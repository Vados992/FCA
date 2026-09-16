import argparse
import json
import os
from pathlib import Path
import sys

from fcea import __version__
from fcea.core.canonical import canonical,loads
from fcea.core.contracts import CONTRACTS,schema_for
from fcea.core.errors import FCEAError
from fcea.service import Service


def output(value,path=None):
    data=json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if path:
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('x',encoding='utf-8') as f: f.write(data)
    else: print(data,end='')


def parser():
    p=argparse.ArgumentParser(prog='fcea',description='FCEA — evidence-grounded, reproducible research-local analysis')
    p.add_argument('--version',action='version',version=__version__)
    p.add_argument('--data-dir',default=os.environ.get('FCEA_DATA_DIR','var/fcea'))
    p.add_argument('--actor',default='local',help='Local OS-trusted audit identity; API identities come from bearer credentials')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init'); sub.add_parser('verify')
    q=sub.add_parser('import'); q.add_argument('file')
    q=sub.add_parser('register'); q.add_argument('kind',choices=sorted(CONTRACTS)); q.add_argument('file')
    q=sub.add_parser('extract'); q.add_argument('file')
    q=sub.add_parser('source'); q.add_argument('file'); q.add_argument('--metadata',required=True)
    q=sub.add_parser('freeze'); q.add_argument('protocol')
    q=sub.add_parser('run'); q.add_argument('protocol'); q.add_argument('--output')
    q=sub.add_parser('show'); q.add_argument('id')
    q=sub.add_parser('list'); q.add_argument('--kind')
    q=sub.add_parser('search'); q.add_argument('query')
    q=sub.add_parser('demo'); q.add_argument('--name',default='policy-rct'); q.add_argument('--all',action='store_true')
    q=sub.add_parser('example'); q.add_argument('name'); q.add_argument('--output')
    q=sub.add_parser('schemas'); q.add_argument('--output-dir')
    q=sub.add_parser('serve'); q.add_argument('--host',default='127.0.0.1'); q.add_argument('--port',default=8000,type=int)
    q.add_argument('--auth-file'); q.add_argument('--release-key-file'); q.add_argument('--allow-remote',action='store_true')
    q.add_argument('--tls-cert'); q.add_argument('--tls-key')
    q=sub.add_parser('auth'); q.add_argument('operation',choices=['init']); q.add_argument('file')
    q=sub.add_parser('keygen'); q.add_argument('file')
    q=sub.add_parser('review'); q.add_argument('target'); q.add_argument('action',choices=['APPROVE','DOWNGRADE','REJECT','RERUN_REQUIRED'])
    q.add_argument('--reason',required=True); q.add_argument('--conflict-of-interest',action='store_true')
    q=sub.add_parser('release'); q.add_argument('run'); q.add_argument('--key-file',required=True); q.add_argument('--public',action='store_true'); q.add_argument('--output')
    q=sub.add_parser('release-verify'); q.add_argument('file'); q.add_argument('--key-file',required=True)
    q=sub.add_parser('backup'); q.add_argument('target')
    q=sub.add_parser('restore'); q.add_argument('source'); q.add_argument('target')
    q=sub.add_parser('proof'); actions=q.add_subparsers(dest='proof_command',required=True)
    a=actions.add_parser('export'); a.add_argument('run'); a.add_argument('file'); a.add_argument('--public',action='store_true')
    for name in ('verify','reproduce'):
        a=actions.add_parser(name); a.add_argument('file')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        return execute(args)
    except (FCEAError,OSError,KeyError,ValueError) as exc:
        print(json.dumps({'error':str(exc),'type':type(exc).__name__}),file=sys.stderr)
        return 2


def execute(args):
    cmd=args.command
    if cmd=='example':
        from fcea.examples.builders import example
        output(example(args.name),args.output); return 0
    if cmd=='schemas':
        schemas={k:schema_for(k) for k in CONTRACTS}
        if args.output_dir:
            for k,v in schemas.items(): output(v,Path(args.output_dir)/(k+'.schema.json'))
        else: output(schemas)
        return 0
    if cmd=='auth':
        from fcea.security.auth import initialize_auth
        output({'one_time_tokens':initialize_auth(args.file),'auth_file':args.file}); return 0
    if cmd=='keygen':
        from fcea.security.signing import generate_key
        generate_key(args.file); output({'status':'CREATED','key_file':args.file}); return 0
    if cmd=='release-verify':
        from fcea.security.signing import read_key,verify
        r=loads(Path(args.file).read_bytes()); verify(r['content'],r['authentication'],read_key(args.key_file))
        output({'status':'AUTHENTICATED','release':r['id']}); return 0
    if cmd=='restore':
        from fcea.operations import restore
        output(restore(args.source,args.target)); return 0
    if cmd=='proof' and args.proof_command!='export':
        from fcea.proof.packet import verify_packet,reproduce_packet
        r=(verify_packet if args.proof_command=='verify' else reproduce_packet)(Path(args.file).read_bytes())
        output(r); return 0 if r['status'] in ('VERIFIED','REPRODUCED') else 3
    with Service(args.data_dir) as service:
        actor=args.actor
        if cmd=='init': output(service.health())
        elif cmd=='verify': output(service.verify())
        elif cmd=='import': output(service.import_bundle(loads(Path(args.file).read_bytes()),actor))
        elif cmd=='register': output(service.register(args.kind,loads(Path(args.file).read_bytes()),actor))
        elif cmd=='extract': output(service.extract(loads(Path(args.file).read_bytes()),actor))
        elif cmd=='source': output(service.acquire(loads(Path(args.metadata).read_bytes()),Path(args.file).read_bytes(),actor))
        elif cmd=='freeze': output(service.freeze(args.protocol,actor))
        elif cmd=='run':
            r=service.run(args.protocol,actor); output(r,args.output)
            return 0 if r['verdict']['execution_state']=='COMPLETE' else 3
        elif cmd=='show': output(service.db.get_entry(args.id))
        elif cmd=='list': output([{'id':e['id'],'kind':e['kind'],'sha256':e['sha256']} for e in service.db.list(args.kind)])
        elif cmd=='search': output(service.db.search(args.query))
        elif cmd=='demo':
            from fcea.examples.builders import example,NAMES
            results=[]
            for name in NAMES if args.all else [args.name]:
                ex=example(name); service.import_bundle(ex,actor); service.freeze(ex['protocol_ref'],actor)
                run=service.run(ex['protocol_ref'],actor)
                results.append({'example':name,'run_id':run['id'],'scientific_state':run['verdict']['scientific_state'],
                    'validity_state':run['verdict']['validity_state'],'gates_passed':sum(g['outcome']=='PASS' for g in run['gates']),
                    'estimate':run['analysis']['estimate'] if run['analysis'] else None,'blockers':run['verdict']['blockers']})
            output({'synthetic':True,'results':results})
            return 0 if all(r['gates_passed']==16 and r['scientific_state']=='SUPPORTED' for r in results) else 3
        elif cmd=='serve':
            from fcea.api.server import serve
            from fcea.security.auth import initialize_auth
            auth_file=args.auth_file or str(Path(args.data_dir)/'auth.json')
            if not Path(auth_file).exists() and args.auth_file is None:
                tokens=initialize_auth(auth_file)
                credentials=Path(args.data_dir)/'credentials.local.json'
                output({'one_time_tokens':tokens},credentials); credentials.chmod(0o600)
                print('Local credentials created at '+str(credentials)+'. Paste the analyst token into the dashboard.',flush=True)
            serve(service,args.host,args.port,auth_file,args.release_key_file,args.allow_remote,args.tls_cert,args.tls_key)
        elif cmd=='proof':
            from fcea.proof.packet import export_packet
            output(export_packet(service,args.run,args.file,args.public,actor))
        elif cmd=='review':
            from fcea.review import review
            output(review(service,args.target,args.action,args.reason,actor,args.conflict_of_interest))
        elif cmd=='release':
            from fcea.review import release
            from fcea.security.signing import read_key
            output(release(service,args.run,read_key(args.key_file),actor,args.public),args.output)
        elif cmd=='backup':
            from fcea.operations import backup
            output(backup(service,args.target))
    return 0
