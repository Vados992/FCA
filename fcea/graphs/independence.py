"""Conservative connected components for common raw bytes, roots, and dependency keys."""
from .provenance import ancestors


def clusters(db, evidence_refs):
    refs = sorted(set(evidence_refs))
    parents = {r:r for r in refs}
    def root(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x
    fingerprints = {}
    for ref in refs:
        tokens = set()
        for ancestor, entry in ancestors(db, ref).items():
            p = entry['payload']
            tokens.add('ancestor:' + ancestor)
            if entry['kind'] == 'SourceSpec':
                tokens.add('raw:' + p['sha256'])
                tokens.update('dependency:' + key for key in p['dependency_keys'])
        for token in tokens:
            if token in fingerprints:
                a, b = sorted((root(ref), root(fingerprints[token])))
                parents[b] = a
            else:
                fingerprints[token] = ref
    grouped = {}
    for ref in refs:
        grouped.setdefault(root(ref), []).append(ref)
    return {'nominal':len(refs),'independent_clusters':len(grouped),
            'clusters':sorted(grouped.values()),'method':'shared-lineage-components.v1',
            'limitation':'Undeclared upstream dependence can remain undetected; counts are not truth probabilities.'}
