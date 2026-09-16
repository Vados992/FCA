import uuid
from fcea.core.canonical import now,digest
from fcea.core.errors import ValidationError,ConflictError
from fcea.service import software_manifest,RunContext
from fcea.gates.checks import Checks
from fcea.security.signing import sign
from fcea.proof.packet import export_packet


def review(service,target_ref,action,reason,actor,conflict_of_interest=False):
    if action not in ('APPROVE','DOWNGRADE','REJECT','RERUN_REQUIRED') or not reason.strip():
        raise ValidationError('Review needs an allowed disposition and a nonempty rationale')
    entry=service.db.get_entry(target_ref)
    if entry['kind'] not in ('RunRecord','EvidenceLink'):
        raise ValidationError('Review target must be an exact run or contradiction link')
    if entry['kind']=='EvidenceLink' and entry['payload']['role']!='contradicts':
        raise ValidationError('Only contradiction evidence links accept resolution reviews')
    record={'id':'review-'+uuid.uuid4().hex,'target_ref':target_ref,'action':action,'reason':reason,
            'reviewer':actor,'conflict_of_interest':bool(conflict_of_interest),'timestamp':now()}
    return service.db.put('ReviewRecord',record,actor,internal=True)


def release(service,run_id,key,actor='local',public=False):
    run=service.db.get(run_id,'RunRecord'); verdict=run['verdict']
    protocol=service.db.record(run['protocol_ref'],'ProtocolSpec')
    claim=service.db.record(run['claim_ref'],'ClaimSpec')
    if run['error'] or verdict['execution_state']!='COMPLETE' or verdict['validity_state']!='VALID':
        raise ValidationError('Release blocked: execution/validity has not passed')
    allowed_failures={'G12','G15'} if verdict['scientific_state']=='FALSIFIED' else set()
    if any(g['outcome']!='PASS' and g['gate_id'] not in allowed_failures for g in run['gates']):
        raise ValidationError('Release blocked by mandatory gates')
    if not run['reproduction'].get('equivalent'):
        raise ValidationError('Release requires verified reproduction')
    service.verify()
    context=RunContext(service,run['protocol_ref'],run['freeze_ref'])
    if Checks(context).g0().outcome!='PASS': raise ValidationError('Protocol inputs changed; amend and rerun')
    if run['manifest']['software']['code_digest']!=software_manifest()['code_digest']:
        raise ValidationError('Code changed since the run; rerun before release')
    latest={}
    for entry in service.db.list('ReviewRecord'):
        rec=entry['payload']
        if rec['target_ref']==run_id: latest[rec['reviewer']]=rec
    if any(r['action']!='APPROVE' for r in latest.values()):
        raise ValidationError('A reviewer requested downgrade, rejection, or rerun')
    approvers=[r for r in latest.values() if r['action']=='APPROVE' and not r['conflict_of_interest']
               and r['reviewer'] not in (run['created_by'],actor)]
    required=max(protocol.required_reviewers,2 if claim.high_impact else 1)
    if len(approvers)<required:
        raise ValidationError(f'Release needs {required} independent reviewer(s), distinct from analyst and release owner')
    packet=export_packet(service,run_id,public=public,actor=actor)
    content={'id':'release-'+uuid.uuid4().hex,'timestamp':now(),'run_ref':run_id,'packet_ref':packet['id'],
        'packet_sha256':packet['sha256'],'verdict':verdict,'review_refs':[r['id'] for r in approvers],
        'software_digest':run['manifest']['software']['code_digest'],'scope_ref':verdict['scope_ref'],
        'release_owner':actor,'visibility':'public' if public else 'internal',
        'validation_profile':'research-local; external domain validation is not implied'}
    authenticated={'id':content['id'],'content':content,'authentication':sign(content,key)}
    return service.db.put('ReleaseRecord',authenticated,actor,internal=True)
