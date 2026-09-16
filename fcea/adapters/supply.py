from collections import defaultdict,deque
from fcea.analysis.statistics import number
from fcea.core.errors import ValidationError
from .base import Adapter


def max_flow(edges,source,sink):
    if source==sink or not source or not sink:
        raise ValidationError('Distinct source/sink required')
    if len(edges)>3000:
        raise ValidationError('Local flow solver is limited to 3000 edges')
    capacity = {}
    residual = defaultdict(dict)
    for edge in edges:
        a,b,c = edge['from'],edge['to'],number(edge['capacity'])
        if not isinstance(a,str) or not isinstance(b,str) or a==b or c<0 or (a,b) in capacity or (b,a) in capacity:
            raise ValidationError('Invalid edge: use distinct nodes, nonnegative capacity, no parallel/antiparallel edges')
        if 0<c<1e-9: raise ValidationError('Rescale flow units: positive capacities must be >=1e-9')
        capacity[a,b]=c
        residual[a][b]=c; residual[b].setdefault(a,0.0)
    if len(residual)>500: raise ValidationError('Local flow solver is limited to 500 nodes')
    total=0.0; iterations=0
    while True:
        iterations+=1
        if iterations>10000: raise ValidationError('Flow augmentation budget exhausted; no certificate issued')
        parent={source:None}; queue=deque([source])
        while queue and sink not in parent:
            a=queue.popleft()
            for b in sorted(residual[a]):
                if residual[a][b]>1e-12 and b not in parent:
                    parent[b]=a; queue.append(b)
        if sink not in parent:
            break
        b=sink; increment=float('inf')
        while parent[b] is not None:
            a=parent[b]; increment=min(increment,residual[a][b]); b=a
        b=sink
        while parent[b] is not None:
            a=parent[b]; residual[a][b]-=increment; residual[b][a]+=increment; b=a
        total+=increment
    flows=[{'from':a,'to':b,'capacity':c,'flow':c-residual[a][b]} for (a,b),c in capacity.items()]
    balance=defaultdict(float)
    for e in flows:
        balance[e['from']]-=e['flow']; balance[e['to']]+=e['flow']
    violations=[n for n,x in balance.items() if n not in (source,sink) and abs(x)>1e-8*max(1,total)]
    if violations:
        raise ValidationError('Flow conservation violated')
    return {'max_flow':total,'edges':flows,'balances':dict(balance),'conservation_pass':True}


def analyze(data,method,p,seed):
    disabled=p.get('disabled_edges',[])
    if not isinstance(disabled,list) or any(not isinstance(x,str) for x in disabled):
        raise ValidationError('disabled_edges must contain edge IDs')
    edges=[row for row in data if row.get('id') not in disabled]
    unknown=set(disabled)-{r.get('id') for r in data}
    if unknown:
        raise ValidationError('Unknown disabled edge')
    result=max_flow(edges,p.get('source','S'),p.get('sink','T'))
    return {'estimate':result['max_flow'],'metric':'maximum_feasible_flow',
            'scientific_state':'SUPPORTED' if result['max_flow']>=number(p.get('required_flow',0)) else 'NOT_SUPPORTED',
            'diagnostics':result,'uncertainty_components':{'capacities':'treated as fixed; change in counterfactual scenarios'}}


SUPPLY = Adapter('supply','supply_chain',('max_flow',),('MODEL_COMPATIBILITY',),
    frozenset({'source','sink','disabled_edges','required_flow'}),analyze,{},('capacity_validity',),
    limitations='Static single-commodity capacitated flow with disruption scenarios; no automatic estimation of inventories, substitution, or dynamic cascades.')
