"""Optional local Laya decision API; never claims model inference without a working endpoint."""
import os,json,urllib.request,urllib.parse

def decide(state, choices, endpoint=None, timeout=5):
    """Optional decision acceleration via an explicitly configured local /v1/systemone server."""
    endpoint=endpoint or os.getenv('LAYA_BASE_URL')
    if not endpoint:return {'enabled':False,'reason':'LAYA_BASE_URL not configured'}
    parsed=urllib.parse.urlparse(endpoint)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1'):
        return {'enabled':False,'reason':'Only local HTTP endpoints are permitted by default'}
    if not choices:return {'enabled':False,'reason':'No decision choices supplied'}
    payload={'state':state[:3000],'questions':[{'type':'choice','name':'next_step','options':choices[:8]}]}
    req=urllib.request.Request(endpoint.rstrip('/')+'/v1/systemone',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return {'enabled':True,'raw':json.load(response),'note':'Unvalidated model output; independently verify decisions'}
    except Exception as exc:return {'enabled':False,'reason':'Laya endpoint error: '+str(exc)}
