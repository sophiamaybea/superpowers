from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from engine.iterative import solve
from engine.core import investigate
import json,os
HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Superpowers</title><style>body{font-family:system-ui;background:#f5f2ea;color:#171717;max-width:840px;margin:8vh auto;padding:24px}h1{font:clamp(3rem,9vw,6rem) Georgia,serif;letter-spacing:-.06em;margin:0}textarea{width:100%;box-sizing:border-box;min-height:140px;padding:18px;background:#fff;border:1px solid #aaa;border-radius:12px;font:inherit}button{padding:14px 25px;border:0;background:#171717;color:white;border-radius:9px;cursor:pointer;margin-top:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;padding:20px;border-radius:12px}a{color:inherit}small{color:#666}</style><h1>Superpowers.</h1><p>Think better. Find existing tools. Then answer.</p><textarea id="p" placeholder="What do you want to build or solve?"></textarea><button onclick="go()">Research → Improve → Answer</button><p id="status"></p><div id="out"></div><script>async function go(){let p=document.getElementById('p').value,s=document.getElementById('status'),out=document.getElementById('out');s.textContent='Researching GitHub before answering…';out.replaceChildren();try{let r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});let d=await r.json();if(!r.ok)throw Error(d.error);s.textContent=d.quality_gate_passed?'Quality shortlist found':'Search budget exhausted — review evidence';for(let [label,value] of [['Repository candidates',d.repositories.map(x=>x.name+' — '+x.url+' (licence: '+(x.license||'unknown')+')').join('\\n')||'None'],['Research attempts',JSON.stringify(d.rounds,null,2)],['Improved prompt',d.improved_prompt],['Answer',d.answer||'Set OPENAI_API_KEY to enable generated answers.'],['Errors',(d.errors||[]).concat(d.answer_error||[]).join('\\n')]]){if(!value)continue;let h=document.createElement('h2');h.textContent=label;let pre=document.createElement('pre');pre.textContent=value;out.append(h,pre)}}catch(e){s.textContent='Error: '+e.message}}</script></html>'''
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path not in ('/','/health'):self.send_error(404);return
  body=(HTML if self.path=='/' else '{"ok":true}').encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8' if self.path=='/' else 'application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_POST(self):
  if self.path not in ('/api/run','/api/investigate'):self.send_error(404);return
  secret=os.getenv('SUPERPOWERS_API_KEY')
  if secret and self.headers.get('Authorization')!='Bearer '+secret:
   self.send_response(401);self.end_headers();return
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n<=0 or n>20000:raise ValueError('Invalid request size')
   obj=json.loads(self.rfile.read(n));prompt=obj.get('prompt','')
   if not isinstance(prompt,str) or not prompt.strip():raise ValueError('Prompt required')
   body=json.dumps(investigate(prompt[:12000],max_rounds=obj.get('max_rounds',3),include_communities=bool(obj.get('include_communities',True)),use_laya=bool(obj.get('use_laya',False))) if self.path=='/api/investigate' else solve(prompt[:12000],strict=bool(obj.get('strict',False)),max_rounds=obj.get('max_rounds',4))).encode();status=200
  except Exception as e:body=json.dumps({'error':str(e)}).encode();status=400
  self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8000'))),Handler).serve_forever()
