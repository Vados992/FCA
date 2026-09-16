from copy import deepcopy
from fcea.examples.builders import example
from fcea.analysis.closure import validate_closure
from fcea.core.contracts import decode
from fcea.proof.packet import build_packet,reproduce_packet
from tests.helpers import Case,record,replace_ids


def finite_bundle():
    bundle=example('science')
    bundle['sources'][0]['content']['data']=[{'id':k,'member':k,'witness':False,'alternate':False} for k in ('a','b','c')]
    record(bundle,'ScopeSpec').update(populations=['a','b','c'],model_families=['science.finite_predicate'])
    record(bundle,'ImplementationSpec')['method']='finite_predicate'
    record(bundle,'ModelSpec')['family']='science.finite_predicate'
    record(bundle,'ProtocolSpec')['parameters']={'key':'member','witness':'witness','quantifier':'none','expected_size':3}
    record(bundle,'CounterfactualSpec')['changes']={'witness':'alternate'}
    record(bundle,'ClaimSpec').update(claim_type='UNIVERSAL_NEGATIVE',coverage_ref='science.coverage')
    coverage={'id':'science.coverage','scope_ref':'science.scope','universe':['a','b','c'],
              'observations_ref':'science.data','key_column':'member','witness_column':'witness','justification_ref':'science.design'}
    i=next(i for i,r in enumerate(bundle['records']) if r['kind']=='ClaimSpec')
    bundle['records'].insert(i,{'kind':'CoverageSpec','payload':coverage})
    return bundle


class QuantifierClosureTests(Case):
    def test_exhaustive_finite_negative_is_certified_only_in_named_scope(self):
        r=self.execute(finite_bundle())
        self.assertEqual(r['verdict']['scientific_state'],'CERTIFIED_WITHIN_SCOPE')
        self.assertEqual(r['verdict']['scope_ref'],'science.scope')

    def test_incomplete_finite_coverage_cannot_certify_universal(self):
        b=finite_bundle();b['sources'][0]['content']['data'].pop();r=self.execute(b)
        self.assertEqual(self.gate(r,'G15')['outcome'],'FAIL')
        self.assertNotEqual(r['verdict']['scientific_state'],'CERTIFIED_WITHIN_SCOPE')

    def test_single_valid_witness_falsifies_finite_universal_negative(self):
        b=finite_bundle();row=b['sources'][0]['content']['data'][0];row['witness']=True;row['alternate']=True
        r=self.execute(b);self.assertEqual(r['verdict']['scientific_state'],'FALSIFIED')

    def test_universal_claim_requires_coverage_certificate(self):
        b=finite_bundle();record(b,'ClaimSpec').pop('coverage_ref');r=self.execute(b)
        self.assertEqual(self.gate(r,'G15')['outcome'],'INCONCLUSIVE')

    def test_counterfactual_witness_blocks_certification(self):
        b=finite_bundle();b['sources'][0]['content']['data'][0]['alternate']=True;r=self.execute(b)
        self.assertEqual(self.gate(r,'G11')['outcome'],'INCONCLUSIVE')

    def test_empty_search_is_not_a_universal_negative(self):
        b=finite_bundle();b['sources'][0]['content']['data']=[];r=self.execute(b)
        self.assertEqual(self.gate(r,'G4')['outcome'],'FAIL')

    def test_existential_witness_has_no_universal_requirement(self):
        b=finite_bundle();record(b,'ProtocolSpec')['parameters']['quantifier']='exists'
        record(b,'ClaimSpec').update(claim_type='EXISTENTIAL',coverage_ref=None)
        for row in b['sources'][0]['content']['data']:row['witness']=True;row['alternate']=True
        r=self.execute(b);self.assertEqual(r['verdict']['scientific_state'],'SUPPORTED')

    def feedback(self):
        bundles=[]
        for prefix,treatment,outcome in [('edge_ab.','A','B'),('edge_ba.','B','A')]:
            b=replace_ids(example('policy-rct'),'policy_rct.',prefix)
            record(b,'ScopeSpec')['populations']=['feedback-system']
            record(b,'ProtocolSpec')['parameters'].update(treatment=treatment,outcome=outcome)
            record(b,'ModelSpec')['causal_graph']={treatment:[],outcome:[treatment]}
            for row in b['sources'][0]['content']['data']:
                row[treatment]=row.pop('treatment');row[outcome]=row.pop('y')
            self.service.import_bundle(b);bundles.append(b)
        for identifier,entity,day in [('event.a0','A','01'),('event.b1','B','02'),('event.a2','A','03')]:
            self.service.register('EventSpec',{'id':identifier,'entity':entity,'earliest':f'2025-02-{day}T00:00:00Z',
                'latest':f'2025-02-{day}T00:00:00Z','known_at':'2025-12-31T00:00:00Z',
                'evidence_refs':['edge_ab.design','edge_ba.design']})
        edge_runs=[]
        for b,start,end in zip(bundles,['event.a0','event.b1'],['event.b1','event.a2']):
            p=deepcopy(record(b,'ProtocolSpec'));p.update(id=p['id']+'.bound',version=2,supersedes=p['id'],edge_from_ref=start,edge_to_ref=end)
            self.service.register('ProtocolSpec',p);self.service.freeze(p['id']);r=self.service.run(p['id'])
            self.assertEqual(r['verdict']['scientific_state'],'SUPPORTED');edge_runs.append(r)
        b=replace_ids(example('policy-rct'),'policy_rct.','feedback.')
        record(b,'ScopeSpec')['populations']=['feedback-system']
        record(b,'ClaimSpec').update(claim_type='MECHANISM',closure_ref='feedback.closure')
        record(b,'ClaimSpec')['mandatory_dependencies']+=['edge_ab.claim','edge_ba.claim']
        closure={'id':'feedback.closure','closure_type':'time_unrolled_feedback','event_refs':['event.a0','event.b1','event.a2'],
                 'edge_verdict_refs':[r['id'] for r in edge_runs]}
        i=next(i for i,r in enumerate(b['records']) if r['kind']=='ClaimSpec')
        b['records'].insert(i,{'kind':'ClosureSpec','payload':closure})
        return b,closure,edge_runs

    def test_feedback_needs_ordered_bound_causal_edges_and_reproduces(self):
        bundle,_,_=self.feedback();r=self.execute(bundle)
        self.assertEqual(self.gate(r,'G10')['outcome'],'PASS')
        self.assertEqual(r['verdict']['scientific_state'],'SUPPORTED')
        self.assertEqual(reproduce_packet(build_packet(self.service,r['id']))['status'],'REPRODUCED')

    def test_bare_graph_cycle_does_not_certify_feedback(self):
        bundle,closure,_=self.feedback()
        bad=deepcopy(closure);bad['edge_verdict_refs']=[]
        result=validate_closure(self.service.db,decode('ClosureSpec',bad),self.service.db.record('edge_ab.scope','ScopeSpec'))
        self.assertFalse(result['valid'])

    def test_swapping_causal_edge_certificates_breaks_closure(self):
        _,closure,_=self.feedback();bad=deepcopy(closure);bad['edge_verdict_refs'].reverse()
        r=validate_closure(self.service.db,decode('ClosureSpec',bad),self.service.db.record('edge_ab.scope','ScopeSpec'))
        self.assertFalse(r['valid']);self.assertTrue(any('not_bound' in b for b in r['blockers']))

    def test_chronologically_reversed_cycle_is_rejected(self):
        _,closure,_=self.feedback();bad=deepcopy(closure);bad['event_refs'].reverse()
        r=validate_closure(self.service.db,decode('ClosureSpec',bad),self.service.db.record('edge_ab.scope','ScopeSpec'))
        self.assertFalse(r['valid']);self.assertIn('closure:time_unrolling',r['blockers'])
