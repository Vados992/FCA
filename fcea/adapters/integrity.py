from collections import defaultdict,deque
from fcea.core.errors import ValidationError
from .base import Adapter


def analyze(data,method,p,seed):
    allowed={'recorded_payment','recorded_ownership','recorded_contract','documented_access'}
    adjacency=defaultdict(list)
    for row in data:
        if row.get('relation') not in allowed or not all(isinstance(row.get(k),str) for k in ('from','to','id')):
            raise ValidationError('Integrity edge must use an explicit documentary relation')
        adjacency[row['from']].append(row)
    start,end=p.get('start'),p.get('end')
    if not isinstance(start,str) or not isinstance(end,str) or start==end:
        raise ValidationError('Distinct documentary path endpoints required')
    max_hops=p.get('max_hops',6)
    if type(max_hops) is not int or not 1<=max_hops<=12:
        raise ValidationError('max_hops must be 1–12')
    queue=deque([(start,[])]); visited={start}; found=None
    while queue:
        current,path=queue.popleft()
        if current==end:
            found=path; break
        if len(path)<max_hops:
            for edge in sorted(adjacency[current],key=lambda e:e['id']):
                if edge['to'] not in visited:
                    visited.add(edge['to']); queue.append((edge['to'],path+[edge]))
    return {'estimate':float(found is not None),'metric':'documentary_path_present',
            'scientific_state':'SUPPORTED' if found is not None else 'NOT_SUPPORTED',
            'diagnostics':{'path':found or [],'max_hops':max_hops,'edge_semantics':sorted(allowed)},
            'uncertainty_components':{'source_truth':'not established by hashes or path existence'},
            'interpretation':'The registered source contains a documentary path. No inference of guilt, motive, intent, influence or causation.'}


INTEGRITY = Adapter('integrity','integrity',('documentary_path',),('OBSERVATION',),
    frozenset({'start','end','max_hops'}),analyze,{},('documentary_extraction_validity',),
    limitations='Source-backed documentary reachability only; legal, intent and causal labels are prohibited.')
