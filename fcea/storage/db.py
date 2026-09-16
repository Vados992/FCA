"""A connection is shared only under a reentrant process lock; SQLite serializes writers."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading

from fcea.core.canonical import canonical, digest, loads, now, plain
from fcea.core.contracts import CONTRACTS, decode
from fcea.core.errors import ConflictError, IntegrityError, NotFoundError, ValidationError


def references(payload):
    refs = set()
    for key, value in payload.items():
        if key.endswith('_ref') or key == 'supersedes':
            if value:
                refs.add(value)
        elif key.endswith('_refs') or key in ('mandatory_dependencies', 'optional_dependencies', 'falsification_tests'):
            refs.update(value)
        elif key == 'proof_routes':
            refs.update(x for route in value for x in route)
    return sorted(refs)


class Database:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / 'fcea.sqlite3'
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=FULL')
        self.conn.executescript(Path(__file__).with_name('001.sql').read_text())
        self.conn.execute('INSERT OR IGNORE INTO schema_migrations VALUES(1,?)', (now(),))
        # Read-only relational projections of the typed authoritative JSON records.
        views = {'sources':'SourceSpec', 'source_versions':'SourceSpec', 'evidence_items':'EvidenceItem',
            'claims':'ClaimSpec', 'claim_dependencies':'ClaimSpec', 'evidence_claim_links':'EvidenceLink',
            'models':'ModelSpec', 'model_versions':'ModelSpec', 'implementations':'ImplementationSpec',
            'assumptions':'AssumptionSpec', 'domains':'ScopeSpec', 'scopes':'ScopeSpec', 'events':'EventSpec',
            'temporal_relations':'TemporalRelation', 'counterfactuals':'CounterfactualSpec',
            'causal_estimands':'ModelSpec', 'closure_candidates':'ClosureSpec', 'tests':'TestSpec',
            'gate_runs':'RunRecord', 'contradictions':'EvidenceLink', 'source_dependencies':'SourceSpec',
            'verdicts':'RunRecord', 'proof_packets':'ProofPacketRecord', 'reviews':'ReviewRecord',
            'run_manifests':'RunRecord'}
        for name, kind in views.items():
            self.conn.execute(f"CREATE VIEW IF NOT EXISTS {name} AS SELECT * FROM objects WHERE kind='{kind}'")

    def close(self):
        with self.lock:
            self.conn.close()

    @contextmanager
    def transaction(self):
        with self.lock:
            self.conn.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.conn.execute('COMMIT')
            except BaseException:
                self.conn.execute('ROLLBACK')
                raise

    def _audit(self, actor, action, target, details):
        last = self.conn.execute('SELECT hash FROM audit_events ORDER BY sequence DESC LIMIT 1').fetchone()
        previous = last['hash'] if last else '0' * 64
        item = {'timestamp': now(), 'actor': actor, 'action': action, 'target': target,
                'details': plain(details), 'previous_hash': previous}
        sha = digest(item)
        self.conn.execute('INSERT INTO audit_events(timestamp,actor,action,target,details,previous_hash,hash) VALUES(?,?,?,?,?,?,?)',
            (item['timestamp'], actor, action, target, canonical(details).decode(), previous, sha))
        return sha

    def audit(self, actor, action, target, details=None):
        with self.transaction():
            return self._audit(actor, action, target, details or {})

    def put(self, kind, payload, actor='local', internal=False):
        payload = plain(payload)
        if kind in CONTRACTS:
            payload = plain(decode(kind, payload))
        elif not internal:
            raise ValidationError('This record type is service-managed')
        refs = references(payload) if kind in CONTRACTS else []
        with self.transaction():
            row = self.conn.execute('SELECT sha256 FROM objects WHERE id=?', (payload['id'],)).fetchone()
            if row:
                if row['sha256'] == digest(payload):
                    return payload
                raise ConflictError(f"Immutable ID already exists: {payload['id']}")
            for ref in refs:
                if not self.conn.execute('SELECT 1 FROM objects WHERE id=?', (ref,)).fetchone():
                    raise NotFoundError(f'Missing reference: {ref}')
            self.conn.execute('INSERT INTO objects VALUES(?,?,?,?,?,?,?)',
                (payload['id'], kind, payload.get('version', 1), canonical(payload).decode(), digest(payload), now(), actor))
            self.conn.executemany('INSERT INTO object_refs VALUES(?,?)', [(payload['id'], ref) for ref in refs])
            self._audit(actor, 'register:' + kind, payload['id'], {'sha256': digest(payload)})
        return payload

    def get_entry(self, identifier):
        with self.lock:
            row = self.conn.execute('SELECT * FROM objects WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise NotFoundError(f'Unknown object: {identifier}')
        value = dict(row)
        value['payload'] = loads(value['payload'])
        if digest(value['payload']) != value['sha256']:
            raise IntegrityError(f'Object hash mismatch: {identifier}')
        return value

    def get(self, identifier, kind=None):
        entry = self.get_entry(identifier)
        if kind and entry['kind'] != kind:
            raise ValidationError(f'{identifier}: expected {kind}, got {entry["kind"]}')
        return entry['payload']

    def record(self, identifier, kind):
        return decode(kind, self.get(identifier, kind))

    def list(self, kind=None, limit=None, offset=0):
        with self.lock:
            rows = self.conn.execute('SELECT id FROM objects ' + ('WHERE kind=? ' if kind else '') + 'ORDER BY rowid LIMIT ? OFFSET ?',
                (kind,-1 if limit is None else limit,offset) if kind else (-1 if limit is None else limit,offset)).fetchall()
        return [self.get_entry(r['id']) for r in rows]

    def search(self, query, limit=50):
        if not query.strip() or len(query) > 200:
            raise ValidationError('Search text must contain 1–200 characters')
        escaped = query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        with self.lock:
            rows = self.conn.execute("SELECT id FROM objects WHERE payload LIKE ? ESCAPE '\' ORDER BY rowid DESC LIMIT ?",
                                     ('%' + escaped + '%', limit)).fetchall()
        return [self.get_entry(r['id']) for r in rows]

    def audit_events(self):
        with self.lock:
            rows = self.conn.execute('SELECT * FROM audit_events ORDER BY sequence').fetchall()
        return [dict(r) | {'details': loads(r['details'])} for r in rows]

    def verify(self):
        previous = '0' * 64
        events = self.audit_events()
        for expected, event in enumerate(events, 1):
            content = {k: v for k, v in event.items() if k not in ('sequence','hash')}
            if event['sequence'] != expected or event['previous_hash'] != previous or digest(content) != event['hash']:
                raise IntegrityError(f'Audit chain broken at event {event["sequence"]}')
            previous = event['hash']
        objects = self.list()
        recorded = {(e['target'], e['details'].get('sha256')) for e in events if e['action'].startswith('register:')}
        for entry in objects:
            if (entry['id'], entry['sha256']) not in recorded:
                raise IntegrityError('Object has no corresponding audit event')
        with self.lock:
            result = self.conn.execute('PRAGMA integrity_check').fetchone()[0]
            if result != 'ok' or self.conn.execute('PRAGMA foreign_key_check').fetchall():
                raise IntegrityError('SQLite consistency check failed')
        return {'objects': len(objects), 'audit_events': len(events), 'audit_head': previous, 'status': 'VERIFIED'}

    def backup_database(self, target):
        with self.lock:
            destination = sqlite3.connect(target)
            try:
                self.conn.backup(destination)
            finally:
                destination.close()
