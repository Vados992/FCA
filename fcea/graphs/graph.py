from collections import defaultdict, deque
from fcea.core.errors import ValidationError


def topological_order(dependencies):
    nodes = set(dependencies)
    if any(parent not in nodes for parents in dependencies.values() for parent in parents):
        raise ValidationError('Control graph contains a dangling prerequisite')
    degree = {n: len(set(dependencies[n])) for n in nodes}
    children = defaultdict(set)
    for node, parents in dependencies.items():
        for parent in parents:
            children[parent].add(node)
    queue = deque(sorted(n for n, d in degree.items() if d == 0))
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for child in sorted(children[node]):
            degree[child] -= 1
            if degree[child] == 0:
                queue.append(child)
    if len(result) != len(nodes):
        raise ValidationError('Circular certification is forbidden')
    return result


def reachable(dependencies,start,end,blocked=()):
    children=defaultdict(set)
    for node,parents in dependencies.items():
        for parent in parents: children[parent].add(node)
    visited=set(blocked);queue=deque([start])
    while queue:
        node=queue.popleft()
        if node in visited: continue
        if node==end: return True
        visited.add(node);queue.extend(sorted(children[node]-visited))
    return False


def projections(entries):
    by_id = {e['id']: e for e in entries}
    graphs = {name:{'nodes':[], 'edges':[]} for name in ('evidence','claims','models','temporal')}
    kinds = {'SourceSpec':'evidence','EvidenceItem':'evidence','ClaimSpec':'claims',
             'HypothesisSpec':'claims','ModelSpec':'models','ImplementationSpec':'models',
             'AssumptionSpec':'models','EventSpec':'temporal'}
    for entry in entries:
        kind, p = entry['kind'], entry['payload']
        if kind in kinds:
            graphs[kinds[kind]]['nodes'].append({'id':p['id'],'type':kind,'sha256':entry['sha256']})
        def edge(graph, source, target, relation):
            if source not in by_id or target not in by_id:
                raise ValidationError('Graph projection has a dangling endpoint')
            graphs[graph]['edges'].append({'from':source,'to':target,'relation':relation})
        if kind == 'EvidenceItem':
            edge('evidence', p['id'], p['source_ref'], 'derived_from')
            for parent in p['parent_refs']:
                edge('evidence', p['id'], parent, 'depends_on')
        if kind == 'SourceSpec':
            for parent in p['parent_refs']:
                edge('evidence', p['id'], parent, 'derived_from')
        if kind == 'EvidenceLink':
            edge('evidence', p['evidence_ref'], p['claim_ref'], p['role'])
        if kind == 'ClaimSpec':
            for dep in p['mandatory_dependencies']:
                edge('claims', p['id'], dep, 'requires')
            for index, route in enumerate(p['proof_routes']):
                for dep in route:
                    edge('claims', p['id'], dep, f'route_{index}_requires')
        if kind == 'ModelSpec':
            edge('models', p['implementation_ref'], p['id'], 'implements')
            for assumption in p['assumption_refs']:
                edge('models', p['id'], assumption, 'requires')
        if kind == 'TemporalRelation':
            edge('temporal', p['from_ref'], p['to_ref'], p['relation'])
    for graph in graphs.values():
        graph['nodes'].sort(key=lambda x:x['id'])
        graph['edges'].sort(key=lambda x:(x['from'],x['to'],x['relation']))
        graph['cross_graph_refs'] = sorted({e[k] for e in graph['edges'] for k in ('from','to')} - {n['id'] for n in graph['nodes']})
    return graphs
