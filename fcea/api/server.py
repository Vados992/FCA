from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,unquote
import base64
import binascii
import socket
import ssl
import threading

from fcea.core.canonical import canonical,loads
from fcea.core.contracts import CONTRACTS,schema_for
from fcea.core.errors import FCEAError,ValidationError,AuthorizationError,NotFoundError,ConflictError,IntegrityError
from fcea.security.auth import authenticate,require,load_identities
from fcea.security.signing import read_key
from fcea.adapters.registry import ADAPTERS
from fcea.examples.builders import example,NAMES
from fcea.proof.packet import export_packet
from fcea.review import review,release


def fields(body,required,optional=()):
    if type(body) is not dict or not set(required)<=set(body) or set(body)-set(required)-set(optional):
        raise ValidationError('Request fields do not match the endpoint contract')


class Server(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True

    def __init__(self,address,service,identities,release_key=None,allowed_hosts=None):
        self.service=service; self.identities=identities; self.release_key=release_key
        self.allowed_hosts=set(allowed_hosts or ['127.0.0.1','localhost','::1'])
        self.capacity=threading.BoundedSemaphore(16)
        self.run_capacity=threading.BoundedSemaphore(2)
        super().__init__(address,Handler)

    def process_request(self,request,address):
        if not self.capacity.acquire(blocking=False):
            try: request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n')
            finally: self.shutdown_request(request)
            return
        try: super().process_request(request,address)
        except BaseException:
            self.capacity.release(); raise

    def process_request_thread(self,request,address):
        try: super().process_request_thread(request,address)
        finally: self.capacity.release()


class Handler(BaseHTTPRequestHandler):
    server_version='FCEA'
    sys_version=''
    protocol_version='HTTP/1.0'
    MAX_BODY=16*1024*1024

    def log_message(self,*args):
        # Never put authorization headers, query strings or evidence content in server logs.
        return

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def reply(self,status,value,content_type='application/json',filename=None):
        data=value if isinstance(value,bytes) else canonical(value)
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename: self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.end_headers()
        if self.command!='HEAD': self.wfile.write(data)

    def read_body(self):
        if self.headers.get('Transfer-Encoding'):
            raise ValidationError('Chunked bodies are not accepted')
        lengths=self.headers.get_all('Content-Length',[])
        if len(lengths)!=1: raise ValidationError('One Content-Length header is required')
        try: length=int(lengths[0])
        except ValueError as exc: raise ValidationError('Invalid Content-Length') from exc
        if not 0<length<=self.MAX_BODY: raise ValidationError('Request body exceeds limits or is empty')
        if self.headers.get_content_type()!='application/json': raise ValidationError('Use application/json')
        data=self.rfile.read(length)
        if len(data)!=length: raise ValidationError('Truncated request body')
        return loads(data)

    def do_GET(self): self.dispatch()
    def do_POST(self): self.dispatch()

    def dispatch(self):
        try:
            url=urlsplit(self.path); path=unquote(url.path)
            host=urlsplit('//'+self.headers.get('Host','')).hostname
            if host not in self.server.allowed_hosts:
                raise AuthorizationError('Unrecognized Host header')
            origin=self.headers.get('Origin')
            if origin:
                allowed_scheme='https' if isinstance(self.connection,ssl.SSLSocket) else 'http'
                expected=f'{allowed_scheme}://{self.headers.get("Host")}'
                if origin!=expected: raise AuthorizationError('Cross-origin requests are not permitted')
            if self.command=='GET' and path in ('/','/app.js','/style.css'):
                names={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),
                       '/style.css':('style.css','text/css; charset=utf-8')}
                name,mime=names[path]
                return self.reply(200,(Path(__file__).parents[1]/'dashboard'/name).read_bytes(),mime)
            if self.command=='GET' and path=='/healthz':
                return self.reply(200,{'status':'ok'})
            identity=authenticate(self.headers.get('Authorization'),self.server.identities)
            if self.command=='GET':
                require(identity,'reader','analyst','reviewer','release')
                result=self.get(path,parse_qs(url.query),identity)
            else:
                body=self.read_body()
                result=self.post(path,body,identity)
            if result is not None:
                self.server.service.db.audit(identity.name,'api:'+self.command,path,{'status':200})
                self.reply(200,result)
        except AuthorizationError as exc:
            self.reply(403 if self.headers.get('Authorization') else 401,{'error':str(exc),'code':'AUTHORIZATION'})
        except NotFoundError as exc: self.reply(404,{'error':str(exc),'code':'NOT_FOUND'})
        except ConflictError as exc: self.reply(409,{'error':str(exc),'code':'CONFLICT'})
        except (ValidationError,IntegrityError) as exc: self.reply(422,{'error':str(exc),'code':type(exc).__name__})
        except (KeyError,TypeError,ValueError,binascii.Error) as exc: self.reply(422,{'error':'Malformed request: '+str(exc),'code':'VALIDATION'})
        except (socket.timeout,TimeoutError): self.reply(408,{'error':'Request timed out'})
        except (BrokenPipeError,ConnectionResetError): return
        except Exception:
            self.reply(500,{'error':'Internal error; no successful result was issued','code':'INTERNAL_ERROR'})

    def get(self,path,query,identity):
        service=self.server.service
        if path=='/v1/health': return service.health()
        if path=='/v1/identity': return {'name':identity.name,'roles':sorted(identity.roles)}
        if path=='/v1/adapters': return [a.manifest() for a in ADAPTERS.values()]
        if path=='/v1/examples': return list(NAMES)
        if path=='/v1/graphs': return service.graph()
        if path=='/v1/schemas': return {k:schema_for(k) for k in CONTRACTS}
        if path=='/v1/audit':
            require(identity,'reviewer','release'); return service.db.audit_events()
        if path=='/v1/search': return service.db.search(query.get('q',[''])[0])
        if path=='/v1/objects':
            limit=int(query.get('limit',['100'])[0]); offset=int(query.get('offset',['0'])[0])
            if not 1<=limit<=200 or offset<0: raise ValidationError('Invalid pagination')
            return service.db.list(query.get('kind',[None])[0],limit,offset)
        parts=path.strip('/').split('/')
        kinds={'sources':'SourceSpec','runs':'RunRecord','claims':'ClaimSpec','models':'ModelSpec',
               'releases':'ReleaseRecord','protocols':'ProtocolSpec','evidence':'EvidenceItem'}
        if len(parts)==3 and parts[0]=='v1' and parts[1] in kinds:
            return service.db.get(parts[2],kinds[parts[1]])
        if len(parts)==4 and parts[:2]==['v1','claims'] and parts[3]=='proof':
            service.db.get(parts[2],'ClaimSpec')
            runs=[e['payload'] for e in service.db.list('RunRecord') if e['payload']['claim_ref']==parts[2]]
            if not runs: return {'claim_ref':parts[2],'runs':[],'blockers':['claim:not_run']}
            return {'claim_ref':parts[2],'runs':runs,'packets':[e['payload'] for e in service.db.list('ProofPacketRecord') if e['payload']['run_ref'] in {r['id'] for r in runs}]}
        if len(parts)==3 and parts[:2]==['v1','proofs']:
            packet=service.db.get(parts[2],'ProofPacketRecord')
            service.db.audit(identity.name,'proof_download',parts[2],{'sha256':packet['sha256']})
            self.reply(200,service.raw.get(packet['sha256']),'application/zip',parts[2]+'.zip')
            return None
        raise NotFoundError('Unknown API endpoint')

    def post(self,path,body,identity):
        service=self.server.service; parts=path.strip('/').split('/')
        if len(parts)==3 and parts[:2]==['v1','reviews']:
            require(identity,'reviewer'); fields(body,['action','reason'],['conflict_of_interest'])
            return review(service,parts[2],body['action'],body['reason'],identity.name,body.get('conflict_of_interest',False))
        if path=='/v1/releases':
            require(identity,'release'); fields(body,['run_ref'],['public'])
            if self.server.release_key is None: raise ValidationError('No release authentication key configured')
            return release(service,body['run_ref'],self.server.release_key,identity.name,body.get('public',False))
        require(identity,'analyst')
        if path=='/v1/import': return service.import_bundle(body,identity.name)
        if path=='/v1/demos':
            fields(body,['name']); data=example(body['name'])
            return service.import_bundle(data,identity.name)
        if path=='/v1/sources':
            fields(body,['metadata','content_base64'])
            return service.acquire(body['metadata'],base64.b64decode(body['content_base64'],validate=True),identity.name)
        if path=='/v1/evidence': return service.extract(body,identity.name)
        mapping={'/v1/claims':'ClaimSpec','/v1/models':'ModelSpec','/v1/protocols':'ProtocolSpec'}
        if path in mapping: return service.register(mapping[path],body,identity.name)
        if path=='/v1/objects':
            fields(body,['kind','payload']); return service.register(body['kind'],body['payload'],identity.name)
        if len(parts)==4 and parts[:2]==['v1','protocols'] and parts[3]=='freeze':
            fields(body,[]); return service.freeze(parts[2],identity.name)
        if path=='/v1/runs':
            fields(body,['protocol_ref'])
            if not self.server.run_capacity.acquire(blocking=False):
                raise ConflictError('Two runs are already active; retry after completion')
            try: return service.run(body['protocol_ref'],identity.name)
            finally: self.server.run_capacity.release()
        if len(parts)==4 and parts[:2]==['v1','runs'] and parts[3]=='proof':
            fields(body,[],['public']); return export_packet(service,parts[2],public=body.get('public',False),actor=identity.name)
        if path=='/v1/verify': fields(body,[]); return service.verify()
        raise NotFoundError('Unknown API endpoint')


def serve(service,host,port,auth_file,release_key_file=None,allow_remote=False,tls_cert=None,tls_key=None):
    if host not in ('127.0.0.1','localhost','::1') and not allow_remote:
        raise ValidationError('Non-loopback bind requires --allow-remote and a reviewed deployment boundary')
    identities=load_identities(auth_file)
    key=read_key(release_key_file) if release_key_file else None
    server=Server((host,port),service,identities,key,allowed_hosts={'127.0.0.1','localhost','::1',host})
    if bool(tls_cert)!=bool(tls_key): raise ValidationError('TLS needs both certificate and key')
    if tls_cert:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(tls_cert,tls_key)
        server.socket=context.wrap_socket(server.socket,server_side=True)
    print(f'FCEA research-local dashboard: {"https" if tls_cert else "http"}://{host}:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
