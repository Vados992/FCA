from dataclasses import replace
import sqlite3
from fcea.core.canonical import loads,canonical,timestamp
from fcea.core.contracts import decode,schema_for
from fcea.core.errors import ValidationError,IntegrityError,ConflictError
from fcea.core.normalization import convert,extract,normalize_identity
from fcea.core.scope import within,strength_meet
from fcea.examples.builders import example
from tests.helpers import Case,record


class ContractTests(Case):
    def test_unknown_fields_rejected(self):
        payload=record(example('science'),'ScopeSpec')|{'trust_me':True}
        with self.assertRaises(ValidationError): decode('ScopeSpec',payload)

    def test_bool_cannot_be_version(self):
        payload=record(example('science'),'ScopeSpec')|{'version':True}
        with self.assertRaises(ValidationError): decode('ScopeSpec',payload)

    def test_incompatible_enum_rejected(self):
        payload=record(example('science'),'ClaimSpec')|{'claim_type':'CERTAIN_TRUTH'}
        with self.assertRaises(ValidationError): decode('ClaimSpec',payload)

    def test_empty_proof_route_rejected(self):
        payload=record(example('science'),'ClaimSpec')|{'proof_routes':[[]]}
        with self.assertRaises(ValidationError): decode('ClaimSpec',payload)

    def test_nonfinite_numbers_and_duplicate_keys_rejected(self):
        for text in ('{"x":NaN}','{"x":1e999}','{"x":1,"x":2}'):
            with self.subTest(text=text),self.assertRaises(ValidationError): loads(text)

    def test_aware_datetime_required(self):
        with self.assertRaises(ValidationError): timestamp('2026-01-01T00:00:00')
        self.assertEqual(timestamp('2026-01-01T02:00:00+02:00'),timestamp('2026-01-01T00:00:00Z'))

    def test_reversed_time_interval_rejected(self):
        p=record(example('science'),'ScopeSpec')|{'start':'2030-01-01T00:00:00Z'}
        with self.assertRaises(ValidationError): decode('ScopeSpec',p)

    def test_scope_narrowing_and_widening(self):
        broad=decode('ScopeSpec',record(example('science'),'ScopeSpec')|{'populations':['a','b']})
        narrow=replace(broad,populations=['a'])
        self.assertEqual(within(narrow,broad),[])
        self.assertIn('scope:populations',within(broad,narrow))

    def test_scope_assumptions_have_conditional_direction(self):
        s=decode('ScopeSpec',record(example('science'),'ScopeSpec'))
        stronger=replace(s,assumptions=s.assumptions+['extra_condition'])
        self.assertFalse(within(stronger,s))
        self.assertIn('scope:assumptions_removed',within(s,stronger))

    def test_scope_partial_order_transitivity(self):
        base=decode('ScopeSpec',record(example('science'),'ScopeSpec'))
        a=replace(base,populations=['a']); b=replace(base,populations=['a','b']); c=replace(base,populations=['*'])
        self.assertFalse(within(a,b));self.assertFalse(within(b,c));self.assertFalse(within(a,c))

    def test_dimension_conversion_preserves_raw(self):
        result=convert(23,'degC','K')
        self.assertAlmostEqual(result['value'],296.15)
        self.assertEqual(result['raw_value'],23)
        with self.assertRaises(ValidationError): convert(1,'USD','EUR')
        with self.assertRaises(ValidationError): convert(1,'m','kg')

    def test_extract_nested_json_pointer_and_csv(self):
        self.assertEqual(extract(b'{"a/b":{"~key":[2]}}','json.pointer.v1','/a~1b/~0key/0'),2)
        with self.assertRaises(ValidationError): extract(b'{"a~2b":1}','json.pointer.v1','/a~2b')
        self.assertEqual(extract(b'id,value\nx,1\n','csv.rows.v1'),[{'id':'x','value':'1'}])
        with self.assertRaises(ValidationError): extract(b'a,a\n1,2\n','csv.rows.v1')
        with self.assertRaises(ValidationError): extract(b'a,b\n1\n','csv.rows.v1')

    def test_no_arbitrary_transform_execution(self):
        with self.assertRaises(ValidationError): extract(b'{}','__import__("os").system("anything")')

    def test_normalization_does_not_claim_identity(self):
        self.assertEqual(normalize_identity('  ENTITY  A '),'entity a')

    def test_evidence_strength_meet_is_not_average(self):
        self.assertEqual(strength_meet([{'p':1,'m':0},{'p':0,'m':1}]),{'p':0,'m':0})

    def test_immutable_object_and_audit_triggers(self):
        self.service.import_bundle(example('science'))
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.db.conn.execute("UPDATE objects SET actor='changed'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.db.conn.execute('DELETE FROM audit_events')

    def test_same_id_different_payload_is_rejected(self):
        bundle=example('science'); self.service.import_bundle(bundle)
        scope=record(bundle,'ScopeSpec')|{'populations':['another']}
        with self.assertRaises(ConflictError): self.service.register('ScopeSpec',scope)

    def test_ingest_is_idempotent(self):
        bundle=example('science'); self.service.import_bundle(bundle)
        count=len(self.service.db.list()); self.service.import_bundle(bundle)
        self.assertEqual(len(self.service.db.list()),count)

    def test_superseding_version_must_increase(self):
        b=example('science');self.service.import_bundle(b);p=record(b,'ScopeSpec')
        with self.assertRaises(ValidationError):
            self.service.register('ScopeSpec',p|{'id':'new.scope','supersedes':p['id']})
        self.service.register('ScopeSpec',p|{'id':'new.scope','supersedes':p['id'],'version':2})

    def test_evidence_fabrication_is_rejected(self):
        b=example('science');self.service.import_bundle(b)
        p=self.service.db.get('science.data')|{'id':'fake.data','value':[{'id':'fabricated'}]}
        with self.assertRaises(IntegrityError): self.service.register('EvidenceItem',p)

    def test_schema_has_required_fields_and_no_unknowns(self):
        s=schema_for('ClaimSpec'); self.assertIn('scope_ref',s['required']);self.assertFalse(s['additionalProperties'])
