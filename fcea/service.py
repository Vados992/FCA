"""Application service: immutable registration, protocol freezing and complete gated runs."""
from pathlib import Path
import os
import platform
import subprocess
import sys
import uuid

from fcea import __version__
from fcea.core.canonical import canonical,digest,loads,now,plain,timestamp
from fcea.core.contracts import CONTRACTS,decode,SourceSpec,EvidenceItem
from fcea.core.errors import FCEAError,ValidationError,IntegrityError,ConflictError,NotFoundError
from fcea.core.normalization import extract
from fcea.core.scope import within,evidence_within
from fcea.core.status import PROMOTABLE
from fcea.storage.db import Database,references
from fcea.storage.objects import RawStore
from fcea.adapters.registry import get_adapter
from fcea.graphs.graph import projections,topological_order
from fcea.graphs.provenance import ancestors,verify_evidence
from fcea.gates.engine import evaluate
from fcea.gates.checks import Checks


def software_manifest():
    package=Path(__file__).parent
    files={str(p.relative_to(package)).replace(os.sep,'/'):digest(p.read_bytes())
           for p in sorted(package.rglob('*')) if p.is_file() and p.suffix in ('.py','.sql','.html','.css','.js')}
    return {'core_version':__version__,'files':files,'code_digest':digest(files),
            'dependencies':[],'dependency_lock_hash':digest({'runtime_dependencies':[]})}


def git_commit():
    try:
        result=subprocess.run(['git','rev-parse','HEAD'],cwd=Path(__file__).parent,
            capture_output=True,text=True,timeout=2,check=True)
        return result.stdout.strip()
    except (OSError,subprocess.SubprocessError):
        return None


def isolated_analysis(request,timeout=45):
    script='import sys; sys.path.insert(0, sys.argv[1]); from fcea.analysis.worker import main; main()'
    safe_env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','PATH') if k in os.environ}
    try:
        run=subprocess.run([sys.executable,'-I','-c',script,str(Path(__file__).parent.parent)],
            input=canonical(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            timeout=timeout,env=safe_env,check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValidationError('Isolated reproduction exceeded the local time budget') from exc
    if run.returncode:
        raise ValidationError('Isolated numerical reproduction failed: '+run.stderr.decode(errors='replace')[-1500:])
    return loads(run.stdout)


class RunContext:
    def __init__(self,service,protocol_ref,freeze_ref):
        self.db,self.raw=service.db,service.raw
        self.contracts=CONTRACTS; self.core_version=__version__
        self.protocol=self.db.record(protocol_ref,'ProtocolSpec')
        self.claim=self.db.record(self.protocol.claim_ref,'ClaimSpec')
        self.scope=self.db.record(self.claim.scope_ref,'ScopeSpec')
        self.hypothesis=self.db.record(self.claim.hypothesis_ref,'HypothesisSpec')
        self.model=self.db.record(self.claim.model_ref,'ModelSpec')
        self.implementation=self.db.record(self.model.implementation_ref,'ImplementationSpec')
        self.adapter=get_adapter(self.implementation.adapter_id)
        self.freeze_ref=freeze_ref; self.freeze=self.db.get(freeze_ref,'ProtocolFreeze')
        self.entries=[self.db.get_entry(ref) for ref in self.freeze['object_hashes']]
        self.evidence={e['id']:e['payload'] for e in self.entries if e['kind']=='EvidenceItem'}
        self.data=self.db.get(self.protocol.dataset_ref,'EvidenceItem')['value']
        self.links=[decode('EvidenceLink',e['payload']) for e in self.entries
                    if e['kind']=='EvidenceLink' and e['payload']['claim_ref']==self.claim.id]
        self.all_supporting=sorted({x.evidence_ref for x in self.links if x.role=='supports'})
        self.contradicting=sorted({x.evidence_ref for x in self.links if x.role=='contradicts'})
        self.assumptions=[self.db.record(r,'AssumptionSpec') for r in self.model.assumption_refs]
        self.counterfactuals=[self.db.record(r,'CounterfactualSpec') for r in self.protocol.counterfactual_refs]
        self.tests=[self.db.record(r,'TestSpec') for r in self.protocol.test_refs]
        self.temporal_relations=[self.db.record(r,'TemporalRelation') for r in self.protocol.temporal_relation_refs]
        self.resolutions=[decode('ResolutionSpec',e['payload']) for e in self.entries if e['kind']=='ResolutionSpec']
        self.analysis=None; self.counterfactual_results=[]; self.falsification=[]
        self.independence={}; self.sensitivity={}; self.reproduction={}; self.closure={}
        self.selected_route=None; self.strength={k:False for k in ('provenance','independence','time','model','reproduction','scope')}
        self.route_checks=self.precheck_routes()
        passing=[r for r in self.route_checks if not r['blockers']]
        self.active_route=(passing or self.route_checks)[0]['route']
        dependencies=set(self.claim.mandatory_dependencies + ((self.claim.proof_routes or [[]])[self.active_route]))
        self.supporting=[]
        for dep in sorted(dependencies):
            entry=self.db.get_entry(dep)
            if entry['kind']=='EvidenceItem' and dep in self.all_supporting:
                self.supporting.append(dep)
            elif entry['kind']=='ClaimSpec' and dep in self.freeze['dependency_runs']:
                run=self.db.get(self.freeze['dependency_runs'][dep],'RunRecord')
                self.supporting+=run['verdict']['supporting_evidence']
        self.supporting=sorted(set(self.supporting))
        needed=set(self.supporting+self.contradicting+[self.protocol.dataset_ref])
        needed.update(r for a in self.assumptions for r in a.evidence_refs)
        needed.update(r for cf in self.counterfactuals for r in cf.evidence_refs)
        needed.update(t.evidence_ref for t in self.tests)
        needed.update(r for e in self.entries if e['kind']=='EventSpec' for r in e['payload']['evidence_refs'])
        needed.update(r for res in self.resolutions for r in res.evidence_refs)
        lineage={}
        for ref in needed: lineage.update(ancestors(self.db,ref))
        self.active_entries=list(lineage.values())
        self.active_evidence={e['id']:e['payload'] for e in self.active_entries if e['kind']=='EvidenceItem'}

    def precheck_routes(self):
        output=[]
        for i,route in enumerate(self.claim.proof_routes or [[]]):
            blockers=[]
            for dep in sorted(set(self.claim.mandatory_dependencies+route)):
                try:
                    entry=self.db.get_entry(dep)
                    if entry['kind']=='EvidenceItem':
                        if dep not in self.all_supporting: blockers.append(dep+':no_support_role')
                        verify_evidence(self.db,self.raw,dep,self.protocol.cutoff)
                        blockers += [dep+':'+b for b in evidence_within(self.scope,self.db.record(entry['payload']['scope_ref'],'ScopeSpec'),entry['payload'])]
                    elif entry['kind']=='ClaimSpec':
                        ref=self.freeze['dependency_runs'].get(dep)
                        if not ref: blockers.append(dep+':missing_run'); continue
                        run=self.db.get(ref,'RunRecord'); v=run['verdict']
                        if v['scientific_state'] not in PROMOTABLE or v['validity_state']!='VALID': blockers.append(dep+':unresolved')
                        blockers += [dep+':'+b for b in within(self.scope,self.db.record(v['scope_ref'],'ScopeSpec'))]
                        if timestamp(run['manifest']['knowledge_cutoff'])>timestamp(self.protocol.cutoff):
                            blockers.append(dep+':future_dependency')
                    else: blockers.append(dep+':invalid_dependency_type')
                except FCEAError as exc:
                    blockers.append(dep+':'+str(exc))
            output.append({'route':i,'blockers':blockers})
        return output

    def analysis_request(self):
        return {'adapter_id':self.adapter.id,'method':self.implementation.method,
                'data':self.data,'parameters':self.protocol.parameters,'seed':self.protocol.seed}

    def reproduce_analysis(self):
        return isolated_analysis(self.analysis_request())


class Service:
    def __init__(self,root='var/fcea'):
        self.root=Path(root)
        self.db=Database(self.root)
        self.raw=RawStore(self.root/'raw')

    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

    def register(self,kind,payload,actor='local'):
        if kind=='SourceSpec': raise ValidationError('Acquire sources through the source-ingestion operation')
        obj=decode(kind,payload)
        if obj.supersedes:
            prior=self.db.get_entry(obj.supersedes)
            if prior['kind']!=kind or obj.version<=prior['version']:
                raise ValidationError('A superseding record must retain its kind and increase its version')
        # Enforce endpoint types before immutable insertion.
        expected={'scope_ref':'ScopeSpec','hypothesis_ref':'HypothesisSpec','model_ref':'ModelSpec',
            'implementation_ref':'ImplementationSpec','dataset_ref':'EvidenceItem','claim_ref':'ClaimSpec',
            'evidence_ref':'EvidenceItem','source_ref':'SourceSpec','closure_ref':'ClosureSpec',
            'coverage_ref':'CoverageSpec','observations_ref':'EvidenceItem','justification_ref':'EvidenceItem',
            'edge_from_ref':'EventSpec','edge_to_ref':'EventSpec'}
        for key,target_kind in expected.items():
            ref=getattr(obj,key,None)
            if ref: self.db.get(ref,target_kind)
        plural={'assumption_refs':'AssumptionSpec','counterfactual_refs':'CounterfactualSpec',
            'test_refs':'TestSpec','falsification_tests':'TestSpec','temporal_relation_refs':'TemporalRelation',
            'event_refs':'EventSpec','edge_verdict_refs':'RunRecord','evidence_refs':'EvidenceItem'}
        for key,target_kind in plural.items():
            for ref in getattr(obj,key,[]): self.db.get(ref,target_kind)
        if kind=='TemporalRelation':
            self.db.get(obj.from_ref,'EventSpec'); self.db.get(obj.to_ref,'EventSpec')
        if kind=='EvidenceItem':
            source=self.db.get(obj.source_ref,'SourceSpec')
            if digest(extract(self.raw.get(source['sha256']),obj.transform,obj.selector))!=digest(obj.value):
                raise IntegrityError('Evidence value does not match the registered extraction')
            for ref in [obj.source_ref]+obj.parent_refs:
                parent=self.db.get(ref)
                if timestamp(obj.known_at)<timestamp(parent['known_at']):
                    raise ValidationError('Derived evidence cannot predate parent knowledge')
        if kind=='ProtocolSpec':
            if 'alpha' in obj.parameters and obj.parameters['alpha']!=obj.alpha:
                raise ValidationError('Estimator alpha must match the frozen protocol alpha')
            if bool(obj.edge_from_ref)!=bool(obj.edge_to_ref):
                raise ValidationError('Causal edge binding requires both event endpoints')
        return self.db.put(kind,plain(obj),actor)

    def acquire(self,metadata,data,actor='local'):
        if 'sha256' in metadata or 'acquired_at' in metadata:
            raise ValidationError('Hash and acquisition time are server-assigned')
        sha=self.raw.put(data)
        try:
            old=self.db.get(metadata.get('id'),'SourceSpec')
        except NotFoundError:
            old=None
        payload=metadata | {'sha256':sha,'acquired_at':old['acquired_at'] if old else now()}
        source=decode('SourceSpec',payload)
        for ref in source.parent_refs:
            parent=self.db.get(ref,'SourceSpec')
            if timestamp(source.known_at)<timestamp(parent['known_at']):
                raise ValidationError('Source derivative cannot predate parent knowledge')
        return self.db.put('SourceSpec',plain(source),actor)

    def extract(self,metadata,actor='local'):
        if 'value' in metadata: raise ValidationError('Extracted values are server-assigned')
        source=self.db.get(metadata['source_ref'],'SourceSpec')
        value=extract(self.raw.get(source['sha256']),metadata['transform'],metadata.get('selector',''))
        return self.register('EvidenceItem',metadata | {'value':value},actor)

    def import_bundle(self,bundle,actor='local'):
        if set(bundle)-{'schema_version','sources','records','protocol_ref','description','expected'} or bundle.get('schema_version')!='1.0':
            raise ValidationError('Unknown bundle version or fields')
        if len(bundle.get('sources',[]))+len(bundle.get('records',[]))>2000:
            raise ValidationError('Bundle exceeds the research-local object budget')
        for source in bundle.get('sources',[]):
            if set(source)!={'metadata','content'}: raise ValidationError('Source requires metadata and content')
            self.acquire(source['metadata'],canonical(source['content']),actor)
        for record in bundle.get('records',[]):
            if set(record)!={'kind','payload'}: raise ValidationError('Invalid bundle record')
            if record['kind']=='EvidenceItem' and 'value' not in record['payload']:
                self.extract(record['payload'],actor)
            else: self.register(record['kind'],record['payload'],actor)
        return {'imported_sources':len(bundle.get('sources',[])),'imported_records':len(bundle.get('records',[])),
                'protocol_ref':bundle.get('protocol_ref')}

    def collect(self,protocol_ref):
        entries={}; links=self.db.list('EvidenceLink'); resolutions=self.db.list('ResolutionSpec')
        def visit(ref):
            if ref in entries: return
            entry=self.db.get_entry(ref); entries[ref]=entry
            if entry['kind'] in CONTRACTS:
                for parent in references(entry['payload']): visit(parent)
            if entry['kind']=='ClaimSpec':
                for link in links:
                    if link['payload']['claim_ref']==ref:
                        visit(link['id'])
                        for res in resolutions:
                            if res['payload']['contradiction_link_ref']==link['id']: visit(res['id'])
        visit(protocol_ref)
        claims={e['id']:e['payload'] for e in entries.values() if e['kind']=='ClaimSpec'}
        graph={identifier:[ref for ref in set(p['mandatory_dependencies']+[d for r in p['proof_routes'] for d in r]) if ref in claims]
               for identifier,p in claims.items()}
        topological_order(graph)
        return entries

    def freeze(self,protocol_ref,actor='local'):
        protocol=self.db.record(protocol_ref,'ProtocolSpec')
        identifier='freeze-'+digest(protocol)[:32]
        try: return self.db.get(identifier,'ProtocolFreeze')
        except NotFoundError: pass
        entries=self.collect(protocol_ref)
        dependency_runs={}
        for run in self.db.list('RunRecord'):
            claim=run['payload']['claim_ref']
            if claim in entries and claim!=protocol.claim_ref:
                dependency_runs[claim]=run['id']
        for ref in dependency_runs.values():
            entries[ref]=self.db.get_entry(ref)
        payload={'id':identifier,'protocol_ref':protocol_ref,'protocol_digest':digest(protocol),
            'frozen_at':now(),'frozen_by':actor,'object_hashes':{ref:e['sha256'] for ref,e in sorted(entries.items())},
            'claim_link_ids':sorted(e['id'] for e in entries.values() if e['kind']=='EvidenceLink' and e['payload']['claim_ref']==protocol.claim_ref),
            'dependency_runs':dependency_runs,'mode':protocol.mode,'registration':protocol.registration}
        return self.db.put('ProtocolFreeze',payload,actor,internal=True)

    def run(self,protocol_ref,actor='local'):
        protocol=self.db.record(protocol_ref,'ProtocolSpec')
        freeze_ref='freeze-'+digest(protocol)[:32]
        self.db.get(freeze_ref,'ProtocolFreeze')  # A run cannot silently freeze a mutable plan.
        identifier='run-'+uuid.uuid4().hex
        started=now(); code=software_manifest(); c=None
        self.db.audit(actor,'run_started',identifier,{'protocol_ref':protocol_ref})
        try:
            c=RunContext(self,protocol_ref,freeze_ref)
            records=evaluate(Checks(c).all(),[digest(c.protocol),digest(c.claim),code['code_digest']])
            verdict=self.make_verdict(c,records)
            if code['code_digest']!=software_manifest()['code_digest']:
                raise IntegrityError('Software changed during execution')
            error=None
        except Exception as exc:
            records=[]
            verdict={'claim_ref':protocol.claim_ref,'scope_ref':self.db.get(protocol.claim_ref)['scope_ref'],
                'execution_state':'ERROR','scientific_state':'UNRESOLVED','validity_state':'MODEL_INVALID',
                'blockers':[type(exc).__name__+':'+str(exc)],'supporting_evidence':[],
                'contradictory_evidence':[],'strength':{k:False for k in ('provenance','independence','time','model','reproduction','scope')},
                'statement':'Run did not complete. No scientific conclusion is available.'}
            error={'type':type(exc).__name__,'message':str(exc)}
        manifest={'run_id':identifier,'timestamp':started,'completed_at':now(),'protocol_version':protocol_ref,
            'knowledge_cutoff':protocol.cutoff,'dataset_release':self.db.get_entry(protocol.dataset_ref)['sha256'],
            'adapter_version':c.adapter.version if c else None,'core_version':__version__,'git_commit':git_commit(),
            'container_digest':os.environ.get('FCEA_CONTAINER_DIGEST'),
            'dependency_lock_hash':code['dependency_lock_hash'],'random_seed':protocol.seed,'parameters':protocol.parameters,
            'hardware':{'machine':platform.machine()},'environment':{'python':platform.python_version(),'platform':platform.system()},
            'input_hashes':self.db.get(freeze_ref)['object_hashes'],'output_hashes':{'analysis':digest(c.analysis) if c else None},
            'gate_results':{r['gate_id']:r['outcome'] for r in records},'software':code}
        payload={'id':identifier,'protocol_ref':protocol_ref,'claim_ref':protocol.claim_ref,'freeze_ref':freeze_ref,
            'created_by':actor,'manifest':manifest,'verdict':verdict,'gates':records,
            'analysis':c.analysis if c else None,'counterfactuals':c.counterfactual_results if c else [],
            'falsification':c.falsification if c else [],'sensitivity':c.sensitivity if c else {},
            'independence':c.independence if c else {},'reproduction':c.reproduction if c else {},
            'closure':c.closure if c else {},'route_checks':c.route_checks if c else [],'error':error}
        if protocol.edge_from_ref and protocol.edge_to_ref:
            payload['closure_edge_binding']={'from_event':protocol.edge_from_ref,'to_event':protocol.edge_to_ref}
        return self.db.put('RunRecord',payload,actor,internal=True)

    def make_verdict(self,c,records):
        gates={r['gate_id']:r for r in records}
        failed=[r for r in records if r['outcome']!='PASS']
        scientific=c.analysis['scientific_state'] if c.analysis and not failed else 'INCONCLUSIVE'
        if scientific=='SUPPORTED' and getattr(c,'coverage_certified',False):
            scientific='CERTIFIED_WITHIN_SCOPE'
        validity='VALID'; execution='COMPLETE'
        for key,state in [('G1','MODEL_INVALID'),('G2','PROVENANCE_FAILURE'),('G3','PROVENANCE_FAILURE'),
                          ('G4','DATA_INSUFFICIENT'),('G5','MODEL_INVALID'),('G6','OUTSIDE_DOMAIN'),
                          ('G7','TEMPORAL_FAILURE'),('G8','IDENTIFICATION_FAILURE')]:
            if gates[key]['outcome'] not in ('PASS','BLOCKED'):
                validity=state; break
        if gates['G0']['outcome']!='PASS': validity='MODEL_INVALID'
        if validity!='VALID': execution='BLOCKED'; scientific='UNRESOLVED'
        elif gates['G12']['outcome']=='FAIL':
            rejected=[r for r in c.falsification if r['critical'] and not r['accepted']]
            if any(r['target']=='model' for r in rejected):
                validity='MODEL_INVALID'; scientific='INCONCLUSIVE'
            elif rejected and all(gates[g]['outcome']=='PASS' for g in ('G2','G3','G5','G6','G7','G8','G13','G14')):
                scientific='FALSIFIED'
        if gates['G14']['outcome']!='PASS': execution='BLOCKED'; scientific='UNRESOLVED'
        allowed={'CAUSAL_EFFECT':'Estimated causal effect conditional on the recorded identification assumptions',
            'ASSOCIATION':'Observed association or historical metric in the frozen dataset',
            'MODEL_COMPATIBILITY':'Compatibility of the declared model with the tested data and tolerances',
            'OBSERVATION':'Observation recorded in the registered source',
            'EXISTENTIAL':'A witness within the explicitly tested domain',
            'UNIVERSAL_NEGATIVE':'Exhaustive absence within the enumerated finite domain'}
        statement=(allowed.get(c.claim.claim_type,'Scoped analysis')+': '+scientific+'.')
        if scientific not in PROMOTABLE:
            c.strength={k:False for k in c.strength}
        return {'claim_ref':c.claim.id,'scope_ref':c.scope.id,'execution_state':execution,
            'scientific_state':scientific,'validity_state':validity,'statement':statement,
            'proposition_for_review':c.claim.proposition,'operational_hypothesis':{'method':c.implementation.method,'parameters':c.protocol.parameters},
            'supporting_evidence':c.supporting,'contradictory_evidence':c.contradicting,
            'alternative_explanations':c.hypothesis.alternatives,'missing_evidence':[b for r in failed for b in r['blockers']],
            'blockers':[b for r in failed for b in r['blockers']],'selected_route':c.selected_route,
            'prohibited_claims':c.claim.prohibited_inferences,'strength':c.strength,
            'review_status':'PENDING_REVIEW','proof_packet_ref':None,
            'scope_note':'Machine state applies to the frozen operational test; natural-language entailment requires human review.'}

    def graph(self): return projections(self.db.list())

    def health(self):
        return {'status':'ok','version':__version__,'profile':'research-local','database':'sqlite',
                'objects':len(self.db.list()),'adapter_count':8}

    def verify(self):
        status=self.db.verify()
        for entry in self.db.list('SourceSpec'): self.raw.get(entry['payload']['sha256'])
        status['raw_sources']=len(self.db.list('SourceSpec'))
        return status
