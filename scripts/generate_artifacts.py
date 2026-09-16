"""Regenerate schemas, static examples, API contract and specification/test maps."""
from pathlib import Path
import argparse
import ast
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fcea.core.contracts import CONTRACTS, schema_for
from fcea.examples.builders import NAMES, example


def encoded(value):
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n'


def api_spec():
    schemas = {kind: {'$ref': '../schemas/' + kind + '.schema.json'} for kind in CONTRACTS}
    obj = {'type': 'object'}
    def body(required, optional=None):
        props = {key: {'type': 'string'} for key in required}
        props.update(optional or {})
        return {'type': 'object', 'properties': props, 'required': required, 'additionalProperties': False}
    endpoints = [
        ('get','/healthz',None,None,'Public process liveness only'),
        ('get','/v1/health',None,'reader','Workspace health and counts'),
        ('get','/v1/identity',None,'reader','Authenticated identity and roles'),
        ('get','/v1/adapters',None,'reader','Versioned methods, parameter allowlists and limitations'),
        ('get','/v1/examples',None,'reader','Built-in synthetic example names'),
        ('get','/v1/graphs',None,'reader','Four graph projections with cross-graph references'),
        ('get','/v1/schemas',None,'reader','All runtime-generated JSON schemas'),
        ('get','/v1/audit',None,'reviewer or release','Immutable audit events'),
        ('get','/v1/search',None,'reader','Search immutable objects'),
        ('get','/v1/objects',None,'reader','List objects with limit and offset'),
        ('post','/v1/import',obj,'analyst','Idempotent bundle import; writes are per-object transactional'),
        ('post','/v1/demos',body(['name']),'analyst','Import a synthetic example'),
        ('post','/v1/sources',body(['metadata','content_base64'],{'metadata':obj}),'analyst','Acquire base64 bytes; hash and acquired_at assigned by service'),
        ('post','/v1/evidence',{'$ref':'#/components/schemas/EvidenceItem'},'analyst','Extract evidence; server supplies or verifies value'),
        ('post','/v1/objects',body(['kind','payload'],{'payload':obj}),'analyst','Register typed input; execution-managed records forbidden'),
        ('post','/v1/protocols/{id}/freeze',body([]),'analyst','Freeze exact inputs'),
        ('post','/v1/runs',body(['protocol_ref']),'analyst','Execute frozen protocol; at most two concurrent runs'),
        ('post','/v1/runs/{id}/proof',body([],{'public':{'type':'boolean','default':False}}),'analyst','Create proof packet record'),
        ('get','/v1/proofs/{id}',None,'reader','Download ZIP bytes'),
        ('get','/v1/claims/{id}/proof',None,'reader','Inspect claim runs and packet records'),
        ('post','/v1/reviews/{id}',body(['action','reason'],{'action':{'enum':['APPROVE','DOWNGRADE','REJECT','RERUN_REQUIRED']},'conflict_of_interest':{'type':'boolean','default':False}}),'reviewer','Review exact run or contradiction link'),
        ('post','/v1/releases',body(['run_ref'],{'public':{'type':'boolean','default':False}}),'release','Authenticate release after gates, integrity and independent review'),
        ('post','/v1/verify',body([]),'analyst','Verify database, raw store and audit chain'),
    ]
    for path in ('sources','runs','claims','models','releases','protocols','evidence'):
        endpoints.append(('get','/v1/'+path+'/{id}',None,'reader','Read immutable '+path+' record'))
    for path,kind in [('claims','ClaimSpec'),('models','ModelSpec'),('protocols','ProtocolSpec')]:
        endpoints.append(('post','/v1/'+path,{'$ref':'#/components/schemas/'+kind},'analyst','Register '+kind))
    paths = {}
    for method,path,request,role,summary in endpoints:
        result = {'summary': summary, 'x-required-role': role or 'public',
                  'responses': {'200': {'description': 'Success; scientific state is in the result',
                    'content': {'application/zip' if path=='/v1/proofs/{id}' else 'application/json': {'schema': {'type':'string','format':'binary'} if path=='/v1/proofs/{id}' else {}}}},
                    '401': {'description':'Credentials missing'}, '403':{'description':'Role, token, Host or Origin rejected'},
                    '404': {'description':'Object or route absent'}, '409':{'description':'Immutable conflict or run capacity'},
                    '422': {'description':'Invalid input/integrity failure'}, '500':{'description':'Unexpected error; no success issued'}}}
        if role is None: result['security'] = []
        if '{id}' in path: result['parameters'] = [{'name':'id','in':'path','required':True,'schema':{'type':'string'}}]
        if path=='/v1/objects' and method=='get':
            result['parameters'] = [{'name':'kind','in':'query','schema':{'type':'string'}},
                {'name':'limit','in':'query','schema':{'type':'integer','minimum':1,'maximum':200,'default':100}},
                {'name':'offset','in':'query','schema':{'type':'integer','minimum':0,'default':0}}]
        if path=='/v1/search': result['parameters']=[{'name':'q','in':'query','required':True,'schema':{'type':'string','minLength':1,'maxLength':200}}]
        if request is not None: result['requestBody']={'required':True,'content':{'application/json':{'schema':request}}}
        paths.setdefault(path,{})[method]=result
    return {'openapi':'3.1.0','info':{'title':'FCEA Research Local API','version':'1.0.0',
                'description':'Same-origin, workspace-level bearer RBAC. Read role is inherited by analyst/reviewer/release; admin permits all. Runtime validates semantic references beyond shape schemas.'},
            'servers':[{'url':'http://127.0.0.1:8000'}], 'security':[{'bearer':[]}], 'paths':paths,
            'components':{'securitySchemes':{'bearer':{'type':'http','scheme':'bearer'}},'schemas':schemas}}


def traceability():
    categories = [
        ('SRC','Immutable source identity','storage/objects.py','test_contracts.py; test_gates.py','Hash reads and deliberate source corruption'),
        ('PROV','Reversible provenance','graphs/provenance.py','test_contracts.py','Extraction replay, forged values, ancestry and backdating'),
        ('CLAIM','Explicit typed claims/dependencies','core/contracts.py; service.py','test_contracts.py; test_gates.py','Nonvacuous routes, mandatory dependencies and alternatives'),
        ('MODEL','Versioned model and implementation','gates/checks.py; adapters/registry.py','test_gates.py; test_numerics.py','Pinned method versions, domain predicates, allowed parameters'),
        ('TIME','Valid time and knowledge cutoff','graphs/provenance.py; gates/checks.py','test_gates.py; test_quantifiers_closure.py','Recursive cutoff, validity interval, market lookahead and causal event order'),
        ('SCOPE','No unjustified scope widening','core/scope.py; gates/checks.py','test_contracts.py; test_gates.py; test_quantifiers_closure.py','Scope partial order, finite coverage, forbidden universal inference'),
        ('GATE','Mandatory failures block promotion','gates/engine.py','test_gates.py; test_proof_review.py','DAG cycle detection, blocked descendants and release rejection'),
        ('CF','Counterfactual and sensitivity route','gates/checks.py','test_gates.py; test_numerics.py','All frozen scenarios, sign changes, threshold tampering and supply disruption'),
        ('CAUSAL','Explicit estimand/identification','adapters/policy.py; gates/checks.py','test_gates.py; test_quantifiers_closure.py','DAG, assumptions, IV exclusion, DiD pretrend and exact causal edge binding'),
        ('FALS','Frozen falsifiers and negative controls','analysis/falsification.py','test_gates.py; test_numerics.py','Negative control invalidation, multiplicity and model/hypothesis distinction'),
        ('REPRO','Run manifest and reproduction route','service.py; proof/packet.py','test_proof_review.py; test_quantifiers_closure.py','Fresh-interpreter rerun, whole packet/closure replay and corruption rejection'),
        ('SEC','Least privilege and immutable audit','api/server.py; security/; operations.py','test_api.py; test_proof_review.py','Local RBAC, immutable audit, private exports, HMAC, backup restore; institutional controls external'),
    ]
    lines=['# Requirements traceability','',
        'Appendix D of the supplied PDF has 48 identifiers: the same 12 normative statements recur four times. Every source identifier is preserved below. Repetition is not counted as independent validation. Mappings refer to executable Research Local controls; REQ-SEC production obligations are only partially satisfied by this deployment profile. See [ARCHITECTURE.md](ARCHITECTURE.md).','',
        '| Source requirement | Statement category | Implementation under `fcea/` | Executable tests under `tests/` | Verification / boundary |',
        '|---|---|---|---|---|']
    for i in range(48):
        code,title,impl,tests,check=categories[i%12]
        lines.append(f'| REQ-{code}-{i+1:03} | {title} | `{impl}` | `{tests}` | {check} |')
    return '\n'.join(lines)+'\n'


def test_catalogue():
    files = sorted((ROOT/'tests').glob('test_*.py'))
    names = []
    for file in files:
        tree=ast.parse(file.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ClassDef):
                for method in node.body:
                    if isinstance(method,ast.FunctionDef) and method.name.startswith('test_'):
                        names.append((file.name,node.name,method.name))
    lines=['# Executable test catalogue','',f'{len(names)} named `unittest` methods. Several contain subcases, including all ten synthetic scenarios. Assertions define expected behavior; PASS means the test observed the intended success or rejection.','',
        'Run `python -m unittest discover -s tests -v` or `python scripts/validate.py`. The latter also replays each of the ten independent proof packets.','',
        '| Module | Test class | Assertion case |','|---|---|---|']
    for file,cls,name in names: lines.append(f'| `{file}` | `{cls}` | `{name}` |')
    lines += ['','## Source Appendix F mapping','',
        'The PDF repeats ten test-purpose templates across TEST-001–TEST-080 while rotating illustrative PASS / FAIL-as-designed / BLOCKED-as-designed labels. Those labels are not mutually consistent execution oracles for the repeated prose. The mapping below preserves all 80 IDs and uses concrete semantic assertions in the modules, rather than fabricating 80 distinct specification cases.','',
        '| Source ID | Suite | Executable coverage |','|---|---|---|']
    categories=[('schema','test_contracts.py'),('provenance','test_contracts.py; test_gates.py'),('scope','test_contracts.py; test_quantifiers_closure.py'),
        ('temporal','test_gates.py; test_quantifiers_closure.py'),('gates','test_gates.py'),('counterfactual','test_gates.py; test_numerics.py'),
        ('causal','test_gates.py; test_numerics.py'),('closure','test_quantifiers_closure.py'),('falsification','test_gates.py; test_numerics.py'),('reproduction','test_proof_review.py')]
    for i in range(80):
        suite,coverage=categories[i%10]
        lines.append(f'| TEST-{i+1:03} | {suite} | `{coverage}` |')
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    outputs={f'schemas/{kind}.schema.json':encoded(schema_for(kind)) for kind in CONTRACTS}
    outputs.update({f'examples/{name}.json':encoded(example(name)) for name in NAMES})
    outputs.update({'docs/openapi.json':encoded(api_spec()),'docs/TRACEABILITY.md':traceability(),
                    'docs/TEST_CATALOGUE.md':test_catalogue()})
    mismatches=[]
    for name,content in outputs.items():
        path=ROOT/name
        if args.check:
            if not path.exists() or path.read_bytes()!=content.encode('utf-8'): mismatches.append(name)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(content.encode('utf-8'))
    if mismatches:
        print('Generated files differ: '+', '.join(mismatches),file=sys.stderr)
        return 1
    print(('Verified' if args.check else 'Generated')+f' {len(outputs)} artifacts.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
