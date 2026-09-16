from fcea.core.canonical import digest,timestamp,plain
from fcea.core.contracts import decode
from fcea.core.errors import ValidationError,IntegrityError
from fcea.core.normalization import UNITS
from fcea.core.scope import within,evidence_within,strength_meet
from fcea.core.status import PROMOTABLE
from fcea.graphs.provenance import verify_evidence,ancestors
from fcea.graphs.independence import clusters
from fcea.graphs.graph import topological_order,reachable
from fcea.analysis.statistics import number,sign_stability,equal_numeric
from fcea.analysis.falsification import execute_tests
from fcea.analysis.closure import validate_temporal,validate_closure
from .engine import Check


class Checks:
    def __init__(self,context):
        self.c=context

    def all(self):
        return {f'G{i}':getattr(self,f'g{i}') for i in range(16)}

    def g0(self):
        c=self.c
        frozen=c.db.get(c.freeze_ref,'ProtocolFreeze')
        if frozen['protocol_digest']!=digest(c.protocol) or frozen['protocol_ref']!=c.protocol.id:
            return Check('FAIL',['protocol:freeze_mismatch'])
        # Frozen sources, hypotheses, claims, tests, links and model records must match exactly.
        for ref,sha in frozen['object_hashes'].items():
            if c.db.get_entry(ref)['sha256']!=sha:
                return Check('FAIL',['protocol:input_changed:'+ref])
        live_links=sorted(e['id'] for e in c.db.list('EvidenceLink') if e['payload']['claim_ref']==c.claim.id)
        if live_links!=sorted(frozen['claim_link_ids']):
            return Check('FAIL',['protocol:evidence_links_changed_after_freeze'])
        if c.protocol.registration=='prospective' and timestamp(frozen['frozen_at'])>=timestamp(c.protocol.cutoff):
            return Check('FAIL',['protocol:prospective_freeze_after_cutoff'])
        return Check(diagnostics={'registration':c.protocol.registration,'mode':c.protocol.mode,
                                 'frozen_at':frozen['frozen_at'],'protocol_digest':frozen['protocol_digest']})

    def g1(self):
        c=self.c
        for entry in c.entries:
            if entry['kind'] in c.contracts: decode(entry['kind'],entry['payload'])
        if c.claim.claim_type not in c.adapter.claim_types:
            return Check('FAIL',['adapter:claim_type_not_supported'])
        if c.implementation.adapter_version!=c.adapter.version or c.implementation.core_version!=c.core_version:
            return Check('FAIL',['adapter:implementation_version_mismatch'])
        if c.model.family not in c.scope.model_families and c.scope.model_families!=['*']:
            return Check('FAIL',['model:family_not_in_scope'])
        if c.adapter.domain not in c.scope.domains:
            return Check('FAIL',['adapter:domain_not_in_scope'])
        if c.implementation.method=='finite_predicate':
            expected='UNIVERSAL_NEGATIVE' if c.protocol.parameters.get('quantifier','none')=='none' else 'EXISTENTIAL'
            if c.claim.claim_type!=expected: return Check('FAIL',['finite:claim_quantifier_mismatch'])
        elif c.adapter.id=='science' and c.claim.claim_type!='MODEL_COMPATIBILITY':
            return Check('FAIL',['science:method_does_not_certify_quantifier'])
        return Check(diagnostics={'validated_objects':len(c.entries),'adapter':c.adapter.id})

    def g2(self):
        c=self.c
        sources=[e['payload'] for e in c.active_entries if e['kind']=='SourceSpec']
        if not sources: return Check('FAIL',['source:none'])
        for source in sources:
            c.raw.get(source['sha256'])
            if not source['legal_basis'].strip(): return Check('FAIL',['source:legal_basis_missing'])
        return Check(diagnostics={'verified_sources':len(sources)})

    def g3(self):
        c=self.c
        for ref in c.active_evidence:
            verify_evidence(c.db,c.raw,ref)
        return Check(diagnostics={'traceability_coverage':1.0,'evidence_items':len(c.evidence)})

    def g4(self):
        c=self.c
        if any(e['units'] not in UNITS for e in c.active_evidence.values()):
            return Check('FAIL',['data:unregistered_units'])
        if not isinstance(c.data,list) or not c.data: return Check('FAIL',['data:empty_or_non_tabular'])
        if any(not isinstance(row,dict) for row in c.data): return Check('FAIL',['data:invalid_row'])
        ids=[row.get('id') for row in c.data]
        if any(x is None for x in ids) or any(not isinstance(x,str) for x in ids) or len(ids)!=len(set(ids)):
            return Check('FAIL',['data:missing_or_duplicate_row_id'])
        c.independence=clusters(c.db,c.supporting)
        if c.independence['independent_clusters']<c.protocol.minimum_independent_clusters:
            return Check('FAIL',['evidence:insufficient_independent_clusters'],c.independence)
        return Check(diagnostics=c.independence)

    def assumptions(self,keys):
        by_key={a.key:a for a in self.c.assumptions}
        blockers=[]
        for key in keys:
            a=by_key.get(key)
            if a is None: blockers.append('assumption:missing:'+key)
            elif a.status!='SUPPORTED': blockers.append('assumption:'+a.status.lower()+':'+key)
            elif not a.evidence_refs or not a.rationale.strip(): blockers.append('assumption:unsupported_declaration:'+key)
        return blockers

    def g5(self):
        c=self.c
        if len({a.key for a in c.assumptions})!=len(c.assumptions):
            return Check('FAIL',['model:duplicate_assumption_keys'])
        blockers=self.assumptions(c.adapter.validity_assumptions)
        blockers += self.assumptions([a.key for a in c.assumptions if not a.causal_only])
        if blockers: return Check('FAIL',blockers)
        for pred in c.model.validity_predicates:
            if set(pred)!={'column','operator','value'}: raise ValidationError('Invalid validity predicate')
            op=pred['operator']; bound=number(pred['value'])
            operators={'gte':lambda x:x>=bound,'lte':lambda x:x<=bound,'gt':lambda x:x>bound,'lt':lambda x:x<bound}
            if op not in operators: raise ValidationError('Predicate operator is not allowlisted')
            if any(not operators[op](number(row.get(pred['column']))) for row in c.data):
                return Check('FAIL',['model:validity_predicate_failed'])
        c.analysis=c.adapter.analyze(c.data,c.implementation.method,c.protocol.parameters,c.protocol.seed)
        if c.analysis.get('diagnostics',{}).get('model_valid') is False:
            return Check('FAIL',['model:numerical_validity_failed'],c.analysis['diagnostics'])
        return Check(diagnostics={'model_ref':c.model.id,'estimate_computed':True})

    def g6(self):
        c=self.c
        blockers=within(c.scope,c.db.record(c.model.scope_ref,'ScopeSpec'))
        for ref in c.supporting:
            blockers.extend(f'{ref}:{reason}' for reason in evidence_within(c.scope,c.db.record(c.evidence[ref]['scope_ref'],'ScopeSpec'),c.evidence[ref]))
        return Check('FAIL' if blockers else 'PASS',sorted(set(blockers)))

    def g7(self):
        c=self.c
        for ref in c.active_evidence: verify_evidence(c.db,c.raw,ref,c.protocol.cutoff)
        blockers=[]
        for e in c.entries:
            if e['kind']=='EventSpec' and timestamp(e['payload']['known_at'])>timestamp(c.protocol.cutoff):
                blockers.append('event:post_cutoff:'+e['id'])
        blockers+=validate_temporal(c.db,c.temporal_relations)
        # Market features have a per-decision cutoff, separate from the dataset's final cutoff.
        if c.adapter.id=='market':
            previous_end=None
            for row in c.data:
                if timestamp(row['signal_known_at'])>timestamp(row['decision_at']):
                    blockers.append('market:look_ahead:'+row['id'])
                if timestamp(row['return_end'])>timestamp(c.protocol.cutoff):
                    blockers.append('market:return_after_cutoff:'+row['id'])
                if timestamp(row['return_end'])<=timestamp(row['decision_at']) or (previous_end and timestamp(row['decision_at'])<previous_end):
                    blockers.append('market:invalid_return_interval:'+row['id'])
                previous_end=timestamp(row['return_end'])
            if c.analysis and c.analysis['diagnostics']['temporal_leak_rows']:
                blockers.append('market:invalid_return_intervals')
        if c.protocol.edge_from_ref:
            a=c.db.record(c.protocol.edge_from_ref,'EventSpec'); b=c.db.record(c.protocol.edge_to_ref,'EventSpec')
            if timestamp(a.latest)>=timestamp(b.earliest): blockers.append('causal_edge:time_order')
        return Check('FAIL' if blockers else 'PASS',blockers)

    def g8(self):
        c=self.c
        if c.claim.claim_type not in ('CAUSAL_EFFECT','MECHANISM'):
            return Check(diagnostics={'applicability':'not_required_for_claim_type'})
        required=c.adapter.identification.get(c.implementation.method)
        if not required or not c.model.estimand:
            return Check('NOT_IMPLEMENTED',['causal:no_identification_route'])
        blockers=self.assumptions(list(required)+[a.key for a in c.assumptions if a.causal_only])
        graph=c.model.causal_graph
        exposure=c.protocol.parameters.get('exposure','x') if c.implementation.method=='iv' else c.protocol.parameters.get('treatment','treatment')
        outcome=c.protocol.parameters.get('outcome','y')
        if not graph:
            blockers.append('causal:explicit_dag_missing')
        else:
            topological_order(graph)
            if exposure not in graph or outcome not in graph or not reachable(graph,exposure,outcome):
                blockers.append('causal:estimand_not_bound_to_dag')
            if c.implementation.method=='rct' and graph.get(exposure):
                blockers.append('causal:rct_treatment_has_declared_parents')
            if c.implementation.method=='iv':
                instrument=c.protocol.parameters.get('instrument','z')
                if instrument not in graph or not reachable(graph,instrument,exposure):
                    blockers.append('causal:instrument_path_missing')
                elif reachable(graph,instrument,outcome,blocked={exposure}):
                    blockers.append('causal:declared_exclusion_violation')
        if c.analysis.get('estimand')!=c.model.estimand:
            blockers.append('causal:estimand_mismatch')
        diagnostic=c.analysis['diagnostics']
        if c.protocol.edge_from_ref:
            from_event=c.db.record(c.protocol.edge_from_ref,'EventSpec')
            to_event=c.db.record(c.protocol.edge_to_ref,'EventSpec')
            exposure=c.protocol.parameters.get('exposure','x') if c.implementation.method=='iv' else c.protocol.parameters.get('treatment','treatment')
            outcome=c.protocol.parameters.get('outcome','y')
            if from_event.entity!=exposure or to_event.entity!=outcome:
                blockers.append('causal:edge_endpoints_do_not_match_estimand_variables')
            if not from_event.evidence_refs or not to_event.evidence_refs:
                blockers.append('causal:edge_events_lack_evidence')
        for key in ('pretrend_pass','first_stage_pass'):
            if diagnostic.get(key) is False: blockers.append('causal:'+key)
        return Check('INCONCLUSIVE' if blockers else 'PASS',blockers,
            {'assumptions':list(required),'causal_graph':graph,'interpretation':'Conditional identification; declarative assumptions are evidence-bearing and reviewable, not automatically proven.'})

    def g9(self):
        c=self.c
        if not c.counterfactuals:
            return Check('INCONCLUSIVE',['counterfactual:none_declared'])
        results=[]
        for cf in c.counterfactuals:
            if not cf.evidence_refs: return Check('FAIL',['counterfactual:no_basis:'+cf.id])
            params=c.protocol.parameters | cf.changes
            if params==c.protocol.parameters: return Check('FAIL',['counterfactual:unchanged_baseline:'+cf.id])
            if {'alpha','bootstrap_samples','direction','effect_threshold'} & set(cf.changes):
                return Check('FAIL',['counterfactual:inference_threshold_change'])
            result=c.adapter.analyze(c.data,c.implementation.method,params,c.protocol.seed)
            if result.get('diagnostics',{}).get('model_valid') is False:
                return Check('FAIL',['counterfactual:outside_model_domain:'+cf.id])
            results.append({'counterfactual_ref':cf.id,'changes':cf.changes,'result':result})
        c.counterfactual_results=results
        return Check(diagnostics={'counterfactual_count':len(results)})

    def g10(self):
        c=self.c
        if c.claim.closure_ref:
            result=validate_closure(c.db,c.db.record(c.claim.closure_ref,'ClosureSpec'),c.scope)
            c.closure=result
            return Check('PASS' if result['valid'] else 'FAIL',result['blockers'],result)
        if c.claim.claim_type=='MECHANISM': return Check('INCONCLUSIVE',['closure:mechanism_certificate_missing'])
        return Check(diagnostics={'applicability':'no_causal_closure_claim'})

    def g11(self):
        c=self.c
        estimates=[c.analysis['estimate']]+[x['result']['estimate'] for x in c.counterfactual_results]
        stable=sign_stability(estimates,c.analysis['estimate'])
        c.sensitivity={'estimates':estimates,'range':[min(estimates),max(estimates)],'sign_stability':stable,
                       'interpretation':'Descriptive sign stability, not a probability of causal truth.'}
        if c.protocol.robustness_sign_required and stable!=1:
            return Check('INCONCLUSIVE',['robustness:sign_changes'],c.sensitivity)
        if c.claim.claim_type in ('CAUSAL_EFFECT','MECHANISM','UNIVERSAL_NEGATIVE','EXISTENTIAL') and any(x['result']['scientific_state']!=c.analysis['scientific_state'] for x in c.counterfactual_results):
            return Check('INCONCLUSIVE',['robustness:causal_conclusion_changes'],c.sensitivity)
        return Check(diagnostics=c.sensitivity)

    def g12(self):
        c=self.c
        required=set(c.hypothesis.falsification_tests)
        if not required or not required<=set(c.protocol.test_refs):
            return Check('INCONCLUSIVE',['falsification:required_test_missing'])
        if not any(t.kind in ('negative_control','placebo') for t in c.tests):
            return Check('INCONCLUSIVE',['falsification:negative_control_missing'])
        c.falsification=execute_tests(c.tests,c.evidence,c.protocol.multiplicity,c.protocol.alpha)
        failed=[r for r in c.falsification if r['critical'] and not r['accepted']]
        return Check('FAIL' if failed else 'PASS',[f"falsification:{r['target']}:{r['test_id']}" for r in failed],
                     {'tests':c.falsification,'multiplicity':c.protocol.multiplicity})

    def g13(self):
        c=self.c
        unresolved=[]
        for link in c.links:
            if link.role=='contradicts' and link.material:
                valid=False
                for resolution in c.resolutions:
                    if resolution.contradiction_link_ref!=link.id: continue
                    review=c.db.get(resolution.review_ref,'ReviewRecord')
                    if review.get('target_ref')==link.id and review.get('action')=='APPROVE' and resolution.evidence_refs:
                        valid=True
                if not valid: unresolved.append(link.evidence_ref)
        return Check('INCONCLUSIVE' if unresolved else 'PASS',
                     ['contradiction:unresolved:'+r for r in unresolved],{'all_contradictory_evidence':c.contradicting})

    def g14(self):
        c=self.c
        fresh=c.reproduce_analysis()
        equivalent=equal_numeric(fresh,c.analysis,c.protocol.reproduction_atol,c.protocol.reproduction_rtol)
        c.reproduction={'equivalent':equivalent,'method':'isolated_fresh_interpreter',
            'reference_digest':digest(c.analysis),'reproduced_digest':digest(fresh),
            'atol':c.protocol.reproduction_atol,'rtol':c.protocol.reproduction_rtol,
            'independent_external_replication':False}
        return Check('PASS' if equivalent else 'FAIL',[] if equivalent else ['reproduction:mismatch'],c.reproduction)

    def g15(self):
        c=self.c
        if c.claim.claim_type in ('INTENT','LEGAL_GUILT'):
            return Check('FAIL',['firewall:prohibited_inference'])
        routes=c.claim.proof_routes or [[]]
        failures=[]; valid_routes=[]; route_strengths=[]
        for i,route in enumerate(routes):
            dependencies=sorted(set(c.claim.mandatory_dependencies+route))
            failed=list(c.route_checks[i]['blockers']); vectors=[]
            for dep in dependencies:
                entry=c.db.get_entry(dep)
                if entry['kind']=='EvidenceItem':
                    if dep not in c.supporting: failed.append(dep+':no_support_role')
                    vectors.append({k:True for k in ('provenance','independence','time','model','reproduction','scope')})
                elif entry['kind']=='ClaimSpec':
                    # Dependency certificate must be pinned at protocol freeze; no mutable latest lookup.
                    ref=c.freeze['dependency_runs'].get(dep)
                    if not ref: failed.append(dep+':missing_run'); continue
                    run=c.db.get(ref,'RunRecord'); v=run['verdict']
                    if v['scientific_state'] not in PROMOTABLE or v['validity_state']!='VALID': failed.append(dep+':unresolved')
                    if within(c.scope,c.db.record(v['scope_ref'],'ScopeSpec')): failed.append(dep+':scope')
                    vectors.append(v['strength'])
                else: failed.append(dep+':invalid_dependency_type')
            if not dependencies: failed.append('empty_route')
            failures.append({'route':i,'blockers':failed})
            if not failed: valid_routes.append(i); route_strengths.append(strength_meet(vectors))
        if not valid_routes: return Check('INCONCLUSIVE',['claim:no_complete_proof_route'],{'routes':failures})
        c.selected_route=valid_routes[0]; c.strength=route_strengths[0]
        if c.claim.claim_type=='UNIVERSAL_NEGATIVE':
            if c.implementation.method!='finite_predicate' or not c.claim.coverage_ref:
                return Check('INCONCLUSIVE',['firewall:exhaustive_finite_coverage_required'])
            coverage=c.db.record(c.claim.coverage_ref,'CoverageSpec')
            certified=c.db.record(coverage.scope_ref,'ScopeSpec')
            observed=c.db.get(coverage.observations_ref,'EvidenceItem')['value']
            universe=set(coverage.universe)
            keys=[row.get(coverage.key_column) for row in observed]
            blockers=[]
            if not universe or len(universe)!=len(coverage.universe) or '*' in universe:
                blockers.append('coverage:invalid_finite_universe')
            if set(keys)!=universe or len(keys)!=len(universe): blockers.append('coverage:not_exhaustive')
            if set(c.scope.populations)!=universe or within(c.scope,certified): blockers.append('coverage:scope_mismatch')
            if coverage.observations_ref!=c.protocol.dataset_ref or coverage.key_column!=c.protocol.parameters.get('key','member') or coverage.witness_column!=c.protocol.parameters.get('witness','witness'):
                blockers.append('coverage:predicate_binding')
            if c.protocol.parameters.get('expected_size')!=len(universe): blockers.append('coverage:expected_size_mismatch')
            if blockers: return Check('FAIL',blockers)
            c.coverage_certified=True
        if c.claim.claim_type=='EXISTENTIAL' and c.analysis['scientific_state']!='SUPPORTED':
            return Check('INCONCLUSIVE',['firewall:no_valid_existential_witness'])
        if c.protocol.mode!='confirmatory': return Check('INCONCLUSIVE',['firewall:exploratory_output'])
        return Check(diagnostics={'selected_route':c.selected_route,'strength':c.strength,
            'operational_hypothesis_only':True,'prohibited_claims':c.claim.prohibited_inferences})
