from copy import deepcopy
from fcea.core.errors import ValidationError,NotFoundError
from fcea.graphs.graph import topological_order
from fcea.graphs.independence import clusters
from fcea.gates.engine import evaluate,Check
from fcea.examples.builders import example,NAMES
from tests.helpers import Case,record,replace_ids


class GateTests(Case):
    def test_gate_dag_rejects_circular_certification(self):
        with self.assertRaises(ValidationError): topological_order({'a':['b'],'b':['a']})

    def test_gate_dag_rejects_missing_parent(self):
        with self.assertRaises(ValidationError): topological_order({'a':['missing']})

    def test_failure_propagates_without_running_child(self):
        called=[]
        results=evaluate({'a':lambda:Check('FAIL',['bad']),'b':lambda:called.append(True)},[],{'a':[],'b':['a']})
        self.assertEqual(results[1]['outcome'],'BLOCKED');self.assertFalse(called)

    def test_missing_gate_implementation_is_not_pass(self):
        r=evaluate({},[],{'a':[]});self.assertEqual(r[0]['outcome'],'NOT_IMPLEMENTED')

    def test_all_ten_synthetic_scenarios(self):
        for name in NAMES:
            with self.subTest(name=name):
                r=self.execute(example(name))
                self.assertIsNone(r['error']);self.assertEqual(r['verdict']['scientific_state'],'SUPPORTED')
                self.assertTrue(all(g['outcome']=='PASS' for g in r['gates']))

    def test_unfrozen_protocol_cannot_run(self):
        b=example('policy-rct');self.service.import_bundle(b)
        with self.assertRaises(NotFoundError): self.service.run(b['protocol_ref'])

    def test_missing_identification_cannot_emit_causal_support(self):
        b=example('policy-rct')
        a=next(r['payload'] for r in b['records'] if r['kind']=='AssumptionSpec' and r['payload']['key']=='random_assignment')
        a['status']='UNKNOWN';r=self.execute(b)
        self.assertEqual(self.gate(r,'G8')['outcome'],'INCONCLUSIVE')
        self.assertEqual(r['verdict']['validity_state'],'IDENTIFICATION_FAILURE')
        self.assertNotEqual(r['verdict']['scientific_state'],'SUPPORTED')

    def test_unsupported_association_is_not_intent(self):
        b=example('integrity');record(b,'ClaimSpec')['claim_type']='INTENT';r=self.execute(b)
        self.assertNotEqual(r['verdict']['scientific_state'],'SUPPORTED')
        self.assertEqual(self.gate(r,'G1')['outcome'],'FAIL')

    def test_temporal_leak_blocks_historical_run(self):
        b=example('policy-rct');future='2027-01-01T00:00:00Z'
        b['sources'][0]['metadata']['known_at']=future
        for row in b['records']:
            if row['kind']=='EvidenceItem': row['payload']['known_at']=future
        r=self.execute(b)
        self.assertEqual(self.gate(r,'G7')['outcome'],'FAIL')
        self.assertEqual(r['verdict']['validity_state'],'TEMPORAL_FAILURE')

    def test_backdating_derived_evidence_rejected(self):
        b=example('science');self.service.import_bundle(b)
        meta=self.service.db.get('science.data')|{'id':'bad.derived','known_at':'2020-01-01T00:00:00Z'}
        with self.assertRaises(ValidationError): self.service.register('EvidenceItem',meta)

    def test_market_per_decision_lookahead(self):
        b=example('market');b['sources'][0]['content']['data'][0]['signal_known_at']='2025-06-01T00:00:00Z'
        r=self.execute(b);self.assertEqual(self.gate(r,'G7')['outcome'],'FAIL')

    def test_scope_widening_is_blocked(self):
        b=example('science');base=record(b,'ScopeSpec')
        new=deepcopy(base);new['id']='science.expanded';new['populations']+=['untested_population']
        b['records'].insert(1,{'kind':'ScopeSpec','payload':new})
        record(b,'ClaimSpec')['scope_ref']=new['id']
        r=self.execute(b);self.assertEqual(self.gate(r,'G6')['outcome'],'FAIL')
        self.assertEqual(r['verdict']['validity_state'],'OUTSIDE_DOMAIN')

    def test_evidence_valid_time_restricts_supporting_scope(self):
        b=example('science')
        record(b,'EvidenceItem')['valid_end']='2025-06-01T00:00:00Z'
        r=self.execute(b)
        self.assertEqual(self.gate(r,'G6')['outcome'],'FAIL')
        self.assertNotEqual(r['verdict']['scientific_state'],'SUPPORTED')

    def test_negative_control_failure_invalidates_model(self):
        b=example('policy-rct');b['sources'][0]['content']['negative_control'][0]['zero']=4
        r=self.execute(b);self.assertEqual(self.gate(r,'G12')['outcome'],'FAIL')
        self.assertEqual(r['verdict']['validity_state'],'MODEL_INVALID')

    def test_material_contradiction_blocks_promotion(self):
        b=example('science')
        b['records'].append({'kind':'EvidenceLink','payload':{'id':'science.contradiction','evidence_ref':'science.design',
            'claim_ref':'science.claim','role':'contradicts','material':True}})
        r=self.execute(b);self.assertEqual(self.gate(r,'G13')['outcome'],'INCONCLUSIVE')
        self.assertNotEqual(r['verdict']['scientific_state'],'SUPPORTED')

    def test_new_contradiction_after_freeze_requires_amendment(self):
        b=example('science');self.service.import_bundle(b);self.service.freeze(b['protocol_ref'])
        self.service.register('EvidenceLink',{'id':'new.contradiction','evidence_ref':'science.design','claim_ref':'science.claim','role':'contradicts'})
        r=self.service.run(b['protocol_ref']);self.assertEqual(self.gate(r,'G0')['outcome'],'FAIL')

    def test_source_echo_does_not_count_as_independence(self):
        b=example('science');copy=deepcopy(b['sources'][0]);copy['metadata']['id']='science.copy';b['sources'].append(copy)
        second=deepcopy(next(r for r in b['records'] if r['kind']=='EvidenceItem' and r['payload']['id']=='science.data'))
        second['payload'].update(id='science.echo',source_ref='science.copy')
        claim_index=next(i for i,r in enumerate(b['records']) if r['kind']=='ClaimSpec');b['records'].insert(claim_index,second)
        record(b,'ClaimSpec')['mandatory_dependencies'].append('science.echo')
        b['records'].append({'kind':'EvidenceLink','payload':{'id':'science.echo_link','evidence_ref':'science.echo','claim_ref':'science.claim','role':'supports'}})
        record(b,'ProtocolSpec')['minimum_independent_clusters']=2
        r=self.execute(b);self.assertEqual(self.gate(r,'G4')['outcome'],'FAIL')
        self.assertEqual(r['independence']['nominal'],2);self.assertEqual(r['independence']['independent_clusters'],1)

    def test_source_corruption_is_a_runtime_block_not_falsification(self):
        b=example('science');self.service.import_bundle(b);self.service.freeze(b['protocol_ref'])
        source=self.service.db.get('science.source');p=self.service.raw.path(source['sha256']);p.chmod(0o600);p.write_bytes(b'corrupted')
        r=self.service.run(b['protocol_ref']);self.assertEqual(self.gate(r,'G2')['outcome'],'FAIL')
        self.assertEqual(r['verdict']['scientific_state'],'UNRESOLVED')

    def test_counterfactual_sign_change_blocks_causal_promotion(self):
        b=example('policy-rct');record(b,'CounterfactualSpec')['changes']={'bias_offset':100}
        r=self.execute(b);self.assertEqual(self.gate(r,'G11')['outcome'],'INCONCLUSIVE')

    def test_counterfactual_cannot_change_inference_threshold(self):
        b=example('policy-rct');record(b,'CounterfactualSpec')['changes']={'effect_threshold':0}
        r=self.execute(b);self.assertEqual(self.gate(r,'G9')['outcome'],'FAIL')

    def test_exploratory_protocol_cannot_be_promoted(self):
        b=example('science');record(b,'ProtocolSpec')['mode']='exploratory'
        r=self.execute(b);self.assertEqual(self.gate(r,'G15')['outcome'],'INCONCLUSIVE')

    def test_disjunctive_route_can_survive_other_unresolved_claim(self):
        b=example('science');p=record(b,'ClaimSpec');child=deepcopy(p)
        child.update(id='science.unresolved_child',mandatory_dependencies=['science.data'])
        position=next(i for i,x in enumerate(b['records']) if x['kind']=='ClaimSpec')
        b['records'].insert(position,{'kind':'ClaimSpec','payload':child})
        p['mandatory_dependencies']=[];p['proof_routes']=[['science.unresolved_child'],['science.data']]
        r=self.execute(b);self.assertEqual(r['verdict']['scientific_state'],'SUPPORTED');self.assertEqual(r['verdict']['selected_route'],1)

    def test_missing_mandatory_claim_cannot_be_averaged_away(self):
        b=example('science');p=record(b,'ClaimSpec');child=deepcopy(p);child['id']='science.child'
        position=next(i for i,x in enumerate(b['records']) if x['kind']=='ClaimSpec');b['records'].insert(position,{'kind':'ClaimSpec','payload':child})
        p['mandatory_dependencies'].append(child['id']);r=self.execute(b)
        self.assertNotEqual(r['verdict']['scientific_state'],'SUPPORTED')

    def test_weak_did_pretrend_rejects_identification(self):
        b=example('policy-did')
        for row in b['sources'][0]['content']['data']:
            if row['treatment']==1: row['pre_previous']-=10
        r=self.execute(b);self.assertEqual(self.gate(r,'G8')['outcome'],'INCONCLUSIVE')

    def test_duplicate_sample_identity_rejected(self):
        b=example('science');b['sources'][0]['content']['data'][1]['id']=b['sources'][0]['content']['data'][0]['id']
        r=self.execute(b);self.assertEqual(self.gate(r,'G4')['outcome'],'FAIL')

    def test_causal_dag_required_and_cycles_rejected(self):
        b=example('policy-rct');record(b,'ModelSpec')['causal_graph']={}
        r=self.execute(b);self.assertEqual(self.gate(r,'G8')['outcome'],'INCONCLUSIVE')
        other=replace_ids(example('policy-rct'),'policy_rct.','cycle.')
        record(other,'ModelSpec')['causal_graph']={'treatment':['y'],'y':['treatment']}
        r=self.execute(other);self.assertEqual(self.gate(r,'G8')['outcome'],'FAIL')

    def test_declared_iv_exclusion_violation_cannot_pass(self):
        b=example('policy-iv');record(b,'ModelSpec')['causal_graph']['y'].append('z')
        r=self.execute(b);self.assertEqual(self.gate(r,'G8')['outcome'],'INCONCLUSIVE')
