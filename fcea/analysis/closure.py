from fcea.core.canonical import timestamp
from fcea.core.scope import within
from fcea.core.status import PROMOTABLE
from fcea.core.errors import ValidationError


def validate_temporal(db,relations):
    blockers=[]
    for relation in relations:
        a=db.record(relation.from_ref,'EventSpec'); b=db.record(relation.to_ref,'EventSpec')
        a0,a1,b0,b1=map(timestamp,(a.earliest,a.latest,b.earliest,b.latest))
        if relation.relation=='precedes': valid=a1<b0
        elif relation.relation=='overlaps': valid=max(a0,b0)<=min(a1,b1)
        elif relation.relation=='contains': valid=a0<=b0 and b1<=a1
        else: valid=False
        if not valid: blockers.append('temporal_relation:'+relation.id)
    return blockers


def validate_closure(db,spec,scope):
    if len(spec.event_refs)<3 or len(spec.edge_verdict_refs)!=len(spec.event_refs)-1:
        return {'valid':False,'blockers':['closure:path_and_edge_lengths']}
    events=[db.record(ref,'EventSpec') for ref in spec.event_refs]
    blockers=[]
    if events[0].entity!=events[-1].entity:
        blockers.append('closure:endpoint_identity')
    for a,b in zip(events,events[1:]):
        if timestamp(a.latest)>=timestamp(b.earliest):
            blockers.append('closure:time_unrolling')
    for i,ref in enumerate(spec.edge_verdict_refs):
        run=db.get(ref,'RunRecord'); verdict=run['verdict']
        edge_claim=db.record(verdict['claim_ref'],'ClaimSpec')
        if edge_claim.claim_type not in ('CAUSAL_EFFECT','MECHANISM') or verdict['scientific_state'] not in PROMOTABLE or verdict['validity_state']!='VALID':
            blockers.append('closure:uncertified_edge:'+ref)
        certified=db.record(verdict['scope_ref'],'ScopeSpec')
        if within(scope,certified): blockers.append('closure:edge_scope:'+ref)
        bound=run.get('closure_edge_binding')
        if bound!={'from_event':events[i].id,'to_event':events[i+1].id}:
            blockers.append('closure:edge_not_bound_to_events:'+ref)
    return {'valid':not blockers,'blockers':blockers,'closure_type':spec.closure_type,
            'interpretation':'Entity identity may recur only across increasing event times; every causal edge needs its own bound verdict.'}
