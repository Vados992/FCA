from fcea.core.canonical import digest, timestamp
from fcea.core.normalization import extract
from fcea.core.errors import IntegrityError, ValidationError


def ancestors(db, identifier):
    result, active = {}, set()
    def visit(ref):
        if ref in active:
            raise IntegrityError('Cyclic provenance')
        if ref in result:
            return
        active.add(ref)
        entry = db.get_entry(ref)
        p, kind = entry['payload'], entry['kind']
        if kind not in ('SourceSpec','EvidenceItem'):
            raise ValidationError('Provenance parents must be sources or evidence')
        parents = list(p.get('parent_refs', []))
        if kind == 'EvidenceItem':
            parents.append(p['source_ref'])
        for parent in parents:
            visit(parent)
        active.remove(ref)
        result[ref] = entry
    visit(identifier)
    return result


def verify_evidence(db, raw, evidence_ref, cutoff=None):
    lineage = ancestors(db, evidence_ref)
    sources = []
    for ref, entry in lineage.items():
        p = entry['payload']
        if cutoff is not None and timestamp(p['known_at']) > timestamp(cutoff):
            raise IntegrityError(f'TEMPORAL_LEAK:{ref}')
        if entry['kind'] == 'SourceSpec':
            raw.get(p['sha256'])
            sources.append(ref)
        else:
            source = db.get(p['source_ref'], 'SourceSpec')
            derived = extract(raw.get(source['sha256']), p['transform'], p['selector'])
            if digest(derived) != digest(p['value']):
                raise IntegrityError(f'Extraction mismatch: {ref}')
            for parent in [p['source_ref']] + p['parent_refs']:
                if timestamp(p['known_at']) < timestamp(db.get(parent)['known_at']):
                    raise IntegrityError(f'Backdated derived knowledge: {ref}')
    if not sources:
        raise IntegrityError('No raw source in provenance path')
    return sorted(set(sources))
