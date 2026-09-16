from pathlib import Path,PurePosixPath
import io
import stat
import tempfile
import zipfile
import uuid

from fcea.core.canonical import canonical,digest,loads,now
from fcea.core.errors import IntegrityError,ValidationError,FCEAError
from fcea.core.contracts import CONTRACTS
from fcea.core.scope import within
from fcea.storage.db import references
from fcea.graphs.graph import projections
from fcea.service import Service,RunContext,software_manifest
from fcea.analysis.statistics import equal_numeric


def build_packet(service,run_id,public=False):
    run=service.db.get(run_id,'RunRecord')
    if run['error']: raise ValidationError('Cannot create a scientific proof packet for an ERROR run')
    context=RunContext(service,run['protocol_ref'],run['freeze_ref'])
    entries=context.entries
    sources=[e['payload'] for e in entries if e['kind']=='SourceSpec']
    restricted=[s for s in sources if not s['redistributable']]
    if public and restricted:
        raise ValidationError('Public export blocked: source or derived input is restricted; create a separately reviewed redacted dataset')
    def get(kind): return [e['payload'] for e in entries if e['kind']==kind]
    reviews=[e['payload'] for e in service.db.list('ReviewRecord') if e['payload']['target_ref']==run_id]
    files={}
    def add(name,obj): files[name]=canonical(obj)+b'\n'
    add('claim.json',service.db.get(run['claim_ref']))
    add('hypothesis.json',service.db.get(context.claim.hypothesis_ref))
    add('domain.json',{'adapter':context.adapter.manifest(),'scope':service.db.get(context.claim.scope_ref)})
    add('scope.json',service.db.get(context.claim.scope_ref))
    add('timeline.json',{'events':get('EventSpec'),'relations':get('TemporalRelation'),'cutoff':context.protocol.cutoff})
    add('evidence_manifest.json',{'sources':sources,'evidence':get('EvidenceItem'),
        'export_class':'public' if public else 'internal','restricted_raw_omitted':[s['id'] for s in restricted]})
    add('contradictory_evidence.json',{'links':[p for p in get('EvidenceLink') if p['role']=='contradicts'],
        'resolutions':get('ResolutionSpec')})
    add('source_dependency.json',run['independence'])
    add('model_spec.json',get('ModelSpec'))
    add('assumptions.json',get('AssumptionSpec'))
    add('counterfactuals.json',{'specifications':get('CounterfactualSpec'),'results':run['counterfactuals']})
    add('causal_graph.json',{'domain_dags':[{'model_ref':m['id'],'parents':m['causal_graph']} for m in get('ModelSpec')],
                           'linked_graphs':projections(entries)})
    add('closure_results.json',run['closure'])
    add('gate_records.json',run['gates'])
    add('falsification_results.json',run['falsification'])
    add('sensitivity.json',run['sensitivity'])
    add('run_manifest.json',run['manifest'])
    add('software_manifest.json',run['manifest']['software'])
    add('review_record.json',reviews)
    add('verdict.json',run['verdict'])
    add('run.json',run)
    add('analysis_request.json',context.analysis_request())
    add('input_snapshot.json',{'entries':entries,'freeze':service.db.get_entry(run['freeze_ref'])})
    add('packet.json',{'format':'fcea-proof-1','created_at':now(),'run_id':run_id,
        'self_contained':not restricted,'authentication':'integrity hashes only; release authentication is a separate HMAC record',
        'restricted_sources':[s['id'] for s in restricted]})
    for source in sources:
        if source['redistributable']:
            files['raw/'+source['sha256']]=service.raw.get(source['sha256'])
    package=Path(__file__).parents[1]
    for name,sha in run['manifest']['software']['files'].items():
        content=(package/name).read_bytes()
        if digest(content)!=sha: raise IntegrityError('Installed code no longer matches run; reproduce using its exact version')
        files['software/fcea/'+name]=content
    files['reproduction.md']=b'''# Reproduction\n\nWith the matching trusted FCEA checkout and Python >=3.11:\n\n```sh\npython -m fcea proof verify packet.zip\npython -m fcea proof reproduce packet.zip\n```\n\nAll inputs and code hashes are checked before rebuilding the temporary database and rerunning gates.\nThe verifier never executes code supplied by an untrusted ZIP. Its installed code digest must match.\nRaw restricted/licensed sources are omitted; reproduction then requires authorized retrieval.\nHMAC-authenticated release records are verified separately with the shared key.\nReproduction is not independent external scientific replication.\n'''
    add('hashes.json',{name:digest(content) for name,content in sorted(files.items())})
    files['hashes.txt']=''.join(f'{sha}  {name}\n' for name,sha in loads(files['hashes.json']).items()).encode()
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,content in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,content)
    return buffer.getvalue()


def export_packet(service,run_id,target=None,public=False,actor='local'):
    data=build_packet(service,run_id,public)
    sha=service.raw.put(data)
    if target:
        p=Path(target); p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f: f.write(data)
    packet={'id':'packet-'+uuid.uuid4().hex,'run_ref':run_id,'sha256':sha,
            'created_at':now(),'visibility':'public' if public else 'internal','size':len(data)}
    service.db.put('ProofPacketRecord',packet,actor,internal=True)
    return packet


def read_packet(data):
    if len(data)>32*1024*1024: raise ValidationError('Proof archive is too large')
    files={}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos=archive.infolist()
            if len(infos)>2048 or sum(i.file_size for i in infos)>100*1024*1024:
                raise ValidationError('Proof archive exceeds extraction budget')
            for info in infos:
                path=PurePosixPath(info.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in info.filename or info.filename in files or info.is_dir() or stat.S_ISLNK(info.external_attr>>16):
                    raise IntegrityError('Unsafe or duplicate archive member')
                files[info.filename]=archive.read(info)
    except (zipfile.BadZipFile,RuntimeError,OSError) as exc:
        raise IntegrityError('Invalid proof archive') from exc
    if 'hashes.json' not in files or 'packet.json' not in files:
        raise IntegrityError('Missing proof manifests')
    expected=loads(files['hashes.json'])
    if not isinstance(expected,dict) or set(files)!=set(expected)|{'hashes.json','hashes.txt'}:
        raise IntegrityError('Unexpected/missing proof members')
    for name,sha in expected.items():
        if digest(files[name])!=sha: raise IntegrityError('Proof hash mismatch: '+name)
    if files['hashes.txt']!=''.join(f'{sha}  {name}\n' for name,sha in expected.items()).encode():
        raise IntegrityError('Text hash manifest mismatch')
    if loads(files['packet.json']).get('format')!='fcea-proof-1': raise ValidationError('Unsupported proof format')
    run=loads(files['run.json'])
    for filename,key in [('run_manifest.json','manifest'),('verdict.json','verdict'),('gate_records.json','gates')]:
        if loads(files[filename])!=run[key]: raise IntegrityError('Inconsistent proof view: '+filename)
    if loads(files['packet.json'])['run_id']!=run['id']:
        raise IntegrityError('Proof run identity mismatch')
    if loads(files['software_manifest.json'])!=run['manifest']['software']:
        raise IntegrityError('Inconsistent software manifest')
    for name,sha in run['manifest']['software']['files'].items():
        if 'software/fcea/'+name not in files or digest(files['software/fcea/'+name])!=sha:
            raise IntegrityError('Software snapshot does not match the frozen manifest')
    return files


def verify_packet(data):
    files=read_packet(data)
    metadata=loads(files['packet.json'])
    return {'status':'VERIFIED','sha256':digest(data),'files':len(files),
            'self_contained':metadata['self_contained'],'run_id':metadata['run_id'],
            'authentication':'hash consistency only; authenticity requires a trusted external digest or authenticated release'}


def reproduce_packet(data):
    files=read_packet(data); meta=loads(files['packet.json'])
    if not meta['self_contained']:
        return {'status':'BLOCKED','reason':'Authorized retrieval of omitted restricted raw sources is required'}
    reference=loads(files['run.json']); snapshot=loads(files['input_snapshot.json'])
    software=software_manifest()
    if software['code_digest']!=reference['manifest']['software']['code_digest']:
        return {'status':'BLOCKED','reason':'Installed trusted code does not match the frozen run'}
    with tempfile.TemporaryDirectory(prefix='fcea-reproduce-') as directory:
        with Service(directory) as service:
            for name,content in files.items():
                if name.startswith('raw/'):
                    if digest(content)!=name[4:]: raise IntegrityError('Raw proof filename mismatch')
                    service.raw.put(content)
            pending=list(snapshot['entries'])
            while pending:
                progress=False
                for entry in pending[:]:
                    if digest(entry['payload'])!=entry['sha256']: raise IntegrityError('Snapshot object mismatch')
                    refs=references(entry['payload']) if entry['kind'] in CONTRACTS else []
                    try:
                        for ref in refs: service.db.get(ref)
                    except FCEAError: continue
                    service.db.put(entry['kind'],entry['payload'],entry.get('actor','reproduction'),internal=True)
                    pending.remove(entry); progress=True
                if not progress: raise IntegrityError('Proof snapshot has dangling or cyclic references')
            frozen=snapshot['freeze']
            if digest(frozen['payload'])!=frozen['sha256']: raise IntegrityError('Freeze record mismatch')
            service.db.put(frozen['kind'],frozen['payload'],'reproduction',internal=True)
            rebuilt=service.run(reference['protocol_ref'],'reproduction')
            protocol=service.db.get(reference['protocol_ref'])
            numeric=equal_numeric(rebuilt['analysis'],reference['analysis'],protocol['reproduction_atol'],protocol['reproduction_rtol'])
            gates={r['gate_id']:r['outcome'] for r in rebuilt['gates']}=={r['gate_id']:r['outcome'] for r in reference['gates']}
            states=all(rebuilt['verdict'].get(k)==reference['verdict'].get(k) for k in ('scientific_state','validity_state','execution_state','scope_ref','strength'))
            counterfactuals=equal_numeric(rebuilt['counterfactuals'],reference['counterfactuals'],protocol['reproduction_atol'],protocol['reproduction_rtol'])
            tests=equal_numeric(rebuilt['falsification'],reference['falsification'],protocol['reproduction_atol'],protocol['reproduction_rtol'])
            passed=numeric and gates and states and counterfactuals and tests and not rebuilt['error']
            return {'status':'REPRODUCED' if passed else 'MISMATCH','numeric':numeric,'gates':gates,'states':states,
                    'counterfactuals':counterfactuals,'falsification':tests,'reference_run':meta['run_id'],
                    'rebuilt_execution':rebuilt['verdict']['execution_state'],'independent_external_replication':False}
