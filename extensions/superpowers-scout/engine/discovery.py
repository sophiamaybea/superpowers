"""Multi-source, read-only evidence gathering. External text is never instructions."""
import json,urllib.request,urllib.parse,datetime,re

def fetch_json(url, timeout=9):
    req=urllib.request.Request(url,headers={'User-Agent':'Superpowers-Research/0.4','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if int(response.headers.get('Content-Length','0'))>2_000_000:raise ValueError('Response too large')
        return json.loads(response.read(2_000_000))

def community_research(prompt, limit=6):
    """Search public HN discussions and Stack Overflow questions. No arbitrary-site scraping."""
    words=re.findall(r'[a-zA-Z][\w-]{2,}',prompt)
    query=' '.join(words[:6]); results=[];errors=[]
    if not query:return {'sources':[], 'errors':[]}
    sources=[('hacker_news','https://hn.algolia.com/api/v1/search?'+urllib.parse.urlencode({'query':query,'tags':'story','hitsPerPage':limit})),('stack_overflow','https://api.stackexchange.com/2.3/search/advanced?'+urllib.parse.urlencode({'q':query,'site':'stackoverflow','pagesize':limit,'sort':'relevance'}))]
    for kind,url in sources:
        try:
            data=fetch_json(url)
            items=data.get('hits',[]) if kind=='hacker_news' else data.get('items',[])
            for item in items:
                title=item.get('title') or ''
                link=(item.get('url') or ('https://news.ycombinator.com/item?id='+str(item.get('objectID','')))) if kind=='hacker_news' else item.get('link')
                if not link or not link.startswith('https://'):continue
                results.append({'source':kind,'title':title,'url':link,'discussion_url':('https://news.ycombinator.com/item?id='+str(item.get('objectID',''))) if kind=='hacker_news' else link,'score':item.get('points',0) if kind=='hacker_news' else item.get('score',0),'answered':item.get('is_answered') if kind=='stack_overflow' else None,'untrusted':True})
        except Exception as exc:errors.append(kind+': '+str(exc))
    return {'sources':results,'errors':errors,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'note':'Community posts are leads, not verified solutions. Respect site terms; do not bypass access controls.'}
