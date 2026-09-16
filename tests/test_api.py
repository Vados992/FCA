import hashlib
import http.client
import threading
from fcea.api.server import Server
from fcea.core.canonical import canonical,loads
from tests.helpers import Case


class APITests(Case):
    def setUp(self):
        super().setUp()
        self.tokens={'reader':'r'*40,'analyst':'a'*40,'reviewer':'v'*40}
        identities=[{'name':name,'roles':[name],'token_sha256':hashlib.sha256(value.encode()).hexdigest()} for name,value in self.tokens.items()]
        self.server=Server(('127.0.0.1',0),self.service,identities)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)

    def request(self,path,body=None,role='analyst',headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=15)
        h={'Authorization':'Bearer '+self.tokens[role]} if role else {}
        if body is not None: h['Content-Type']='application/json'
        h.update(headers or {})
        connection.request('GET' if body is None else 'POST',path,canonical(body) if body is not None else None,h)
        response=connection.getresponse();data=response.read();status=response.status;rh=dict(response.getheaders());connection.close()
        return status,data,rh

    def test_liveness_without_credentials_has_no_private_data(self):
        status,data,_=self.request('/healthz',role=None)
        self.assertEqual(status,200);self.assertEqual(loads(data),{'status':'ok'})

    def test_api_requires_authentication(self):
        self.assertEqual(self.request('/v1/objects',role=None)[0],401)

    def test_reader_cannot_import_or_run(self):
        self.assertEqual(self.request('/v1/demos',{'name':'science'},'reader')[0],403)
        self.assertEqual(self.request('/v1/runs',{'protocol_ref':'science.protocol'},'reader')[0],403)

    def test_analyst_cannot_forge_review(self):
        self.assertEqual(self.request('/v1/reviews/arbitrary',{'action':'APPROVE','reason':'forged'},'analyst')[0],403)

    def test_analyst_cannot_register_service_managed_verdict(self):
        status,_,_=self.request('/v1/objects',{'kind':'RunRecord','payload':{'id':'forged'}})
        self.assertEqual(status,422)

    def test_cross_origin_request_rejected(self):
        self.assertEqual(self.request('/v1/demos',{'name':'science'},headers={'Origin':'https://hostile.example'})[0],403)

    def test_unrecognized_host_rejected(self):
        self.assertEqual(self.request('/v1/health',headers={'Host':'attacker.example'})[0],403)

    def test_invalid_request_fields_rejected(self):
        self.assertEqual(self.request('/v1/demos',{'name':'science','execute':'evil'})[0],422)

    def test_api_full_lifecycle_and_proof_download(self):
        self.assertEqual(self.request('/v1/demos',{'name':'science'})[0],200)
        self.assertEqual(self.request('/v1/protocols/science.protocol/freeze',{})[0],200)
        status,data,_=self.request('/v1/runs',{'protocol_ref':'science.protocol'});self.assertEqual(status,200)
        run=loads(data);self.assertEqual(run['verdict']['scientific_state'],'SUPPORTED')
        status,data,_=self.request('/v1/runs/'+run['id']+'/proof',{})
        self.assertEqual(status,200);packet=loads(data)
        status,data,headers=self.request('/v1/proofs/'+packet['id'],role='reader')
        self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'application/zip');self.assertTrue(data.startswith(b'PK'))

    def test_frozen_parameters_cannot_be_overridden_at_run_time(self):
        self.assertEqual(self.request('/v1/runs',{'protocol_ref':'x','parameters':{'threshold':0}})[0],422)

    def test_frontend_has_restrictive_content_policy(self):
        status,data,headers=self.request('/',role=None)
        self.assertEqual(status,200);self.assertIn("script-src 'self'",headers['Content-Security-Policy'])
        self.assertNotIn(b'one_time_tokens',data)

    def test_path_traversal_has_no_static_file_route(self):
        self.assertEqual(self.request('/../LICENSE')[0],404)

    def test_request_pagination_validated(self):
        self.assertEqual(self.request('/v1/objects?limit=1000000')[0],422)

    def test_authenticated_identity_cannot_come_from_body(self):
        self.assertEqual(self.request('/v1/demos',{'name':'science','actor':'admin'})[0],422)
