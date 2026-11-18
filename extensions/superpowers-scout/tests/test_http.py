import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import server

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join(2)
    def request(self,path,payload=None,headers=None):
        data=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(self.base+path,data=data,method='POST' if data is not None else 'GET',
                      headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req,timeout=4) as response:
                return response.status,json.load(response),dict(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.code,json.load(exc),dict(exc.headers)
    def test_health(self):
        code,data,_=self.request('/health')
        self.assertEqual(code,200);self.assertTrue(data['ok'])
    def test_manifest(self):
        code,data,_=self.request('/api/manifest')
        self.assertEqual(code,200);self.assertEqual(data['project'],'Superpowers Scout')
    def test_validation(self):
        code,data,_=self.request('/api/run',{'prompt':' ','max_rounds':4})
        self.assertEqual(code,400);self.assertIn('Prompt must',data['error'])
    def test_malformed_rounds(self):
        code,data,_=self.request('/api/run',{'prompt':'a','max_rounds':'six'})
        self.assertEqual(code,400)
    def test_authentication(self):
        with patch.dict(os.environ,{'SUPERPOWERS_API_KEY':'correct-key'}):
            code,data,_=self.request('/api/run',{'prompt':'example'})
            self.assertEqual(code,401)
    def test_cross_origin_blocked(self):
        code,data,_=self.request('/api/run',{'prompt':'example'},headers={'Origin':'https://attacker.example'})
        self.assertEqual(code,403)
    @patch.object(server,'solve',return_value={'evidence_gate_passed':True,'repositories':[],'rounds':[]})
    def test_authenticated_local_request(self,solve):
        with patch.dict(os.environ,{'SUPERPOWERS_API_KEY':'abc'}):
            code,data,_=self.request('/api/run',{'prompt':'clone a site','failure':'overflow','strict':True},
                                  headers={'Authorization':'Bearer abc'})
            self.assertEqual(code,200)
            solve.assert_called_once()
            self.assertEqual(solve.call_args.kwargs['failure'],'overflow')
    @patch.object(server,'solve',side_effect=RuntimeError('SECRET_PRIVATE_BACKEND_STRING'))
    def test_internal_errors_are_not_leaked(self,solve):
        code,data,_=self.request('/api/run',{'prompt':'example'})
        self.assertEqual(code,500)
        self.assertNotIn('SECRET_PRIVATE_BACKEND_STRING',str(data))
    def test_quota_returns_429(self):
        with patch.object(server.LIMITER,'allow',return_value=False):
            code,data,headers=self.request('/api/run',{'prompt':'example'})
            self.assertEqual(code,429);self.assertEqual(headers.get('Retry-After'),'60')
    def test_cors_opt_in(self):
        with patch.dict(os.environ,{'SUPERPOWERS_ALLOWED_ORIGINS':'https://trusted.example'}):
            code,data,_=self.request('/api/run',{'prompt':' '},headers={'Origin':'https://trusted.example'})
            self.assertEqual(code,400)

if __name__=='__main__':unittest.main()
