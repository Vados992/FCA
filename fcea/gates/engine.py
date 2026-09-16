from dataclasses import dataclass,field
from fcea.core.canonical import digest
from fcea.core.errors import FCEAError
from fcea.graphs.graph import topological_order


@dataclass
class Check:
    outcome: str = 'PASS'
    blockers: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


NAMES = ['Protocol Freeze','Structural/Schema','Source Integrity','Provenance','Data Quality',
    'Model Validity','Scope Validity','Temporal Consistency','Identification','Counterfactual',
    'Closure / Mechanism','Robustness','Falsification','Contradiction','Reproduction','Claim Escalation']
DEPENDENCIES = {'G0':[],'G1':['G0'],'G2':['G1'],'G3':['G2'],'G4':['G3'],
    'G5':['G4'],'G6':['G3'],'G7':['G3'],'G8':['G5','G7'],'G9':['G5','G7'],
    'G10':['G5','G6','G7'],'G11':['G9'],'G12':['G5','G7'],'G13':['G3','G7'],
    'G14':['G5','G7'],'G15':[f'G{i}' for i in range(15)]}


def evaluate(checks,input_digests,dependencies=None):
    graph=DEPENDENCIES if dependencies is None else dependencies
    order=topological_order(graph)
    records={}
    for gate in order:
        parents=[p for p in graph[gate] if records[p]['outcome']!='PASS']
        if parents:
            check=Check('BLOCKED',[f'upstream:{p}' for p in parents])
        elif gate not in checks:
            check=Check('NOT_IMPLEMENTED',['missing_gate_implementation:'+gate])
        else:
            try:
                check=checks[gate]()
            except FCEAError as exc:
                check=Check('FAIL',[type(exc).__name__+':'+str(exc)])
            # Unexpected programming failures propagate to an ERROR run, never scientific falsification.
        if check.outcome not in ('PASS','FAIL','INCONCLUSIVE','BLOCKED','NOT_IMPLEMENTED'):
            raise ValueError('Illegal gate outcome')
        entry={'gate_id':gate,'name':NAMES[int(gate[1:])] if gate[1:].isdigit() and int(gate[1:])<16 else gate,
            'method_version':'fcea.gates.v1','outcome':check.outcome,'blockers':check.blockers,
            'diagnostics':check.diagnostics,'parents':graph[gate],'input_digests':input_digests}
        entry['record_digest']=digest(entry)
        records[gate]=entry
    return [records[g] for g in order]
