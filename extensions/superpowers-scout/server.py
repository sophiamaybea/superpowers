"""Local-first HTTP API. Read-only research; generation is opt-in via OPENAI_API_KEY."""
from __future__ import annotations
from collections import deque
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlparse
from engine.iterative import solve
from engine.core import investigate

HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Superpowers Scout</title><style>body{font-family:system-ui;background:#f5f2ea;color:#171717;max-width:900px;margin:6vh auto;padding:24px;line-height:1.5}h1{font:clamp(3rem,8vw,5rem) Georgia,serif;letter-spacing:-.05em;margin:0}textarea,input{width:100%;box-sizing:border-box;padding:15px;background:#fff;border:1px solid #aaa;border-radius:9px;font:inherit}textarea{min-height:150px}button{padding:14px 25px;border:0;background:#171717;color:white;border-radius:9px;cursor:pointer;margin-top:12px}button:disabled{opacity:.6;cursor:progress}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;padding:20px;border-radius:10px}a{color:inherit}small{color:#555}label{display:block;margin:10px 0}input[type=checkbox]{width:auto}h2{font:1.55rem Georgia,serif}</style><h1>Superpowers Scout.</h1><p>Evidence-led discovery. A shortlist is not a tested solution.</p><label>Problem or build brief<textarea id="p" placeholder="Describe the project or problem"></textarea></label><label>Observed failure (optional)<textarea id="failure" style="min-height:65px" placeholder="Paste the exact error or visual mismatch"></textarea></label><label>API token (only if enabled on server)<input id="key" type="password" autocomplete="off" placeholder="Not stored"></label><label><input type="checkbox" id="strict" checked> Require a viable evidence shortlist before generating an answer</label><button id="go" onclick="go()">Research and build execution brief</button><p role="status" aria-live="polite" id="status"></p><div id="out"></div><script>async function go(){const p=document.getElementById('p').value,failed=document.getElementById('failure').value,key=document.getElementById('key').value,status=document.getElementById('status'),out=document.getElementById('out'),btn=document.getElementById('go');status.textContent='Researching candidate implementations…';btn.disabled=true;out.replaceChildren();try{const headers={'Content-Type':'application/json'};if(key)headers.Authorization='Bearer '+key;const response=await fetch('/api/run',{method:'POST',headers,body:JSON.stringify({prompt:p,failure:failed,strict:document.getElementById('strict').checked})});const d=await response.json();if(!response.ok)throw Error(d.error||'Request failed');status.textContent=d.evidence_gate_passed?'Evidence shortlist ready (not yet tested)':'No confirmed evidence shortlist; inspect errors and try a different query';const format=x=>typeof x==='string'?x:JSON.stringify(x,null,2);for(const [label,value] of [['Candidates',(d.repositories||[]).map(x=>x.name+' — '+x.url+' — '+x.evidence_score+' points (licence: '+(x.license||'unverified')+')').join('\\n')||'None'],['Research rounds',d.rounds],['Prompt refinement method',d.prompt_optimisation_method],['Execution brief',d.execution_brief],['Generated answer',d.answer||d.answer_error||'No model answer available.'],['Errors',d.errors],['Warnings',d.warnings]]){if(value===undefined||value===null||(Array.isArray(value)&&!value.length))continue;const h=document.createElement('h2'),pre=document.createElement('pre');h.textContent=label;pre.textContent=format(value);out.append(h,pre)}}catch(e){status.textContent='Request failed: '+e.message}finally{btn.disabled=false}}</script></html>'''

class SlidingWindowLimiter:
    def __init__(self,limit=12,period=60):
        self.limit=max(1,int(limit));self.period=int(period);self.lock=threading.Lock();self.history={}
    def allow(self,key):
        now=time.monotonic()
        with self.lock:
            history=self.history.setdefault(key,deque())
            while history and now-history[0]>=self.period:history.popleft()
            if len(history)>=self.limit:return False
            history.append(now)
            # opportunistic pruning to avoid unbounded memory growth
            if len(self.history)>500:
                for ip in list(self.history):
                    if not self.history[ip] or now-self.history[ip][-1]>self.period:del self.history[ip]
            return True

LIMITER=SlidingWindowLimiter(int(os.getenv('SUPERPOWERS_REQUESTS_PER_MINUTE','12')))
ACTIVE_REQUESTS=threading.BoundedSemaphore(int(os.getenv('SUPERPOWERS_MAX_CONCURRENT','3')))

class Handler(BaseHTTPRequestHandler):
    server_version='SuperpowersScout/0.5'
    def _headers(self,status,body,content_type='application/json',extra=None):
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        origin=self.headers.get('Origin')
        if origin and self._allowed_origin() and 'Access-Control-Allow-Origin' not in (extra or {}):
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
        for key,value in (extra or {}).items():self.send_header(key,str(value))
        self.end_headers();self.wfile.write(body)
    def _json(self,status,value,extra=None):
        body=json.dumps(value,ensure_ascii=False).encode('utf-8')
        self._headers(status,body,extra=extra)
    def _error(self,status,message):self._json(status,{'error':message})
    def _is_authorised(self):
        secret=os.getenv('SUPERPOWERS_API_KEY')
        if not secret:return True
        return hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+secret)
    def _allowed_origin(self):
        origin=self.headers.get('Origin')
        if not origin:return True
        allowed={x.strip() for x in os.getenv('SUPERPOWERS_ALLOWED_ORIGINS','').split(',') if x.strip()}
        parsed=urlparse(origin)
        if parsed.scheme not in ('http','https'):return False
        # Same-origin is always allowed; there are no wildcard cross-origin grants.
        return parsed.netloc==self.headers.get('Host') or origin in allowed
    def do_OPTIONS(self):
        origin=self.headers.get('Origin')
        if not origin or not self._allowed_origin():self._error(403,'Origin not allowed');return
        self._json(200,{},extra={'Access-Control-Allow-Origin':origin,
            'Access-Control-Allow-Headers':'Authorization, Content-Type',
            'Access-Control-Allow-Methods':'POST, OPTIONS', 'Vary':'Origin'})
    def do_GET(self):
        if self.path=='/':
            self._headers(200,HTML.encode(),'text/html; charset=utf-8');return
        if self.path=='/health':self._json(200,{'ok':True,'service':'superpowers-scout'});return
        if self.path=='/api/manifest':
            manifest=json.loads((Path(__file__).parent/'workflow_spec.json').read_text())
            self._json(200,manifest);return
        self._error(404,'Not found')
    def do_POST(self):
        if self.path not in ('/api/run','/api/investigate'):self._error(404,'Not found');return
        if not self._allowed_origin():self._error(403,'Origin not allowed');return
        if not self._is_authorised():self._error(401,'Unauthorised');return
        remote=self.client_address[0]
        if not LIMITER.allow(remote):
            self._json(429,{'error':'Request quota exceeded'},extra={'Retry-After':'60'});return
        if not ACTIVE_REQUESTS.acquire(blocking=False):self._error(503,'Server busy; retry shortly');return
        try:
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<=0 or size>20000:raise ValueError('Body must be between 1 and 20000 bytes')
                if 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('Content-Type must be application/json')
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict):raise ValueError('Expected a JSON object')
                prompt=payload.get('prompt')
                if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>12000:
                    raise ValueError('Prompt must contain 1 to 12000 characters')
                failure=payload.get('failure','')
                if not isinstance(failure,str) or len(failure)>2000:
                    raise ValueError('Failure must be a string of at most 2000 characters')
                max_rounds=payload.get('max_rounds',4)
                if type(max_rounds) is not int or not 1<=max_rounds<=6:
                    raise ValueError('max_rounds must be an integer from 1 to 6')
                strict=payload.get('strict',False)
                if type(strict) is not bool:raise ValueError('strict must be a boolean')
            except (ValueError,TypeError,UnicodeDecodeError,json.JSONDecodeError) as exc:
                self._error(400,str(exc) if isinstance(exc,ValueError) and not isinstance(exc,json.JSONDecodeError) else 'Malformed JSON request');return
            if self.path=='/api/run':
                result=solve(prompt,strict=strict,max_rounds=max_rounds,failure=failure,
                             refine_prompt=bool(payload.get('refine_prompt',True)))
            else:
                result=investigate(prompt,max_rounds=max_rounds,failure=failure,
                                   include_communities=bool(payload.get('include_communities',True)),
                                   use_laya=bool(payload.get('use_laya',False)))
            self._json(200,result)
        except Exception:
            # Logs are server-side, never return internal tracebacks, env vars, or tokens.
            self.log_error('Internal request failure')
            self._error(500,'Internal server error')
        finally:ACTIVE_REQUESTS.release()


def main():
    host=os.getenv('HOST','127.0.0.1')
    port=int(os.getenv('PORT','8000'))
    if host not in ('localhost','127.0.0.1','::1') and not os.getenv('SUPERPOWERS_API_KEY'):
        raise SystemExit('Refusing to bind a public interface without SUPERPOWERS_API_KEY')
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__=='__main__':main()
