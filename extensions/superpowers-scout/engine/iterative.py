"""Bounded recovery research and quality-gated skill selection. No code execution."""
import datetime, re, urllib.error
from .core import keywords, github_json, cached, _repo, inspect_repo, score_repo, optimise, answer_with_model

DESIGN_WORDS={'design','website','clone','cloning','recreate','rebuild','ui','ux','animation','typography','frontend','landing','portfolio','visual','3d'}
RECOVERY={'clone':['website recreation screenshot-to-code visual regression','playwright screenshot comparison pixelmatch','responsive layout CSS typography'],
          'design':['design systems accessibility typography motion','award winning creative frontend webgl gsap','visual regression playwright screenshot'],
          'default':['implementation examples open source','testing debugging integration','agent skill SKILL.md']}

def plan_queries(prompt):
    terms=keywords(prompt); lower=prompt.lower()
    focus=' '.join(terms[:5]) or 'software development'
    category='clone' if any(x in lower for x in ('clone','cloning','recreate','rebuild','replicate')) else ('design' if any(x in lower for x in DESIGN_WORDS) else 'default')
    return category, [focus]+[focus+' '+suffix for suffix in RECOVERY[category]]

def evidence_score(repo,category):
    """Heuristic suitability, not proof of quality or security."""
    text=(repo['name']+' '+repo['description']).lower()
    terms=({'playwright','visual','screenshot','responsive','clone','pixelmatch'} if category=='clone' else
           {'design','typography','animation','accessibility','gsap','webgl','ui','motion'} if category=='design' else
           {'test','skill','agent','integration','example'})
    matches=sorted(t for t in terms if t in text)
    skill_count=len(repo.get('skills',[]))
    readme=repo.get('readme',False)
    score= min(len(matches),4)*12 + min(skill_count,3)*9 + (8 if readme else 0) + min(repo.get('stars',0),1000)/200
    if repo.get('archived'):score-=40
    if repo.get('fork'):score-=5
    if repo.get('license') in (None,'NOASSERTION'):score-=12
    if repo.get('inspection_errors'):score-=8
    return round(score,2),matches

def research_until_helpful(prompt,max_rounds=4,minimum_candidates=2,fetch=github_json,inspector=inspect_repo):
    """Search multiple strategies, inspect and evaluate, stop at evidence threshold or budget.
    Each round searches a distinct query. Never represent a heuristic as a verified solution.
    """
    category,queries=plan_queries(prompt)
    rounds=max(1,min(int(max_rounds),6));found={};trace=[];chosen=[];errors=[]
    for round_no,query in enumerate(queries[:rounds],1):
        try:
            # Custom fetch injection makes retries testable without network.
            if fetch is github_json:
                data,cache_hit=cached('iterative:'+query,lambda:fetch('search/repositories',{'q':query+' in:name,description,readme','per_page':12}),900)
            else:data,cache_hit=fetch('search/repositories',{'q':query+' in:name,description,readme','per_page':12}),False
            candidates=data.get('items',[])[:12]
            for item in candidates:
                if not isinstance(item,dict) or 'full_name' not in item:continue
                found[item['full_name']]=_repo(item)
            search_error=None
        except (urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
            search_error=str(e);errors.append({'round':round_no,'error':search_error});cache_hit=False
        ranked=sorted(found.values(),key=lambda r:-score_repo(r,keywords(prompt)))[:8]
        for r in ranked[:5]:
            if 'skills' not in r:
                try:r.update(inspector(r))
                except Exception as e:r.update({'skills':[],'readme':False,'inspection_errors':[str(e)]})
        for r in ranked:
            r['quality_score'],r['matched_capabilities']=evidence_score(r,category)
        chosen=sorted(ranked,key=lambda r:-r['quality_score'])
        # A good shortlist requires at least two inspected, active candidates with matching evidence.
        viable=[r for r in chosen if r.get('quality_score',0)>=20 and r.get('matched_capabilities') and not r.get('archived') and 'skills' in r]
        trace.append({'round':round_no,'query':query,'new_total':len(found),'viable':len(viable),'cache_hit':cache_hit,'error':search_error})
        if len(viable)>=minimum_candidates:break
    viable=[r for r in chosen if r.get('quality_score',0)>=20 and r.get('matched_capabilities') and not r.get('archived') and 'skills' in r]
    return {'category':category,'rounds':trace,'repositories':chosen[:5], 'viable_candidates':len(viable),
            'quality_gate_passed':len(viable)>=minimum_candidates,'errors':errors,
            'stopping_reason':'evidence_threshold_met' if len(viable)>=minimum_candidates else 'search_budget_exhausted',
            'quality_caveat':'Heuristic discovery only. Test visual fidelity, functionality, accessibility, licences and security in the actual project.',
            'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}

def solve(prompt,generate=True,strict=False,max_rounds=4):
    result=research_until_helpful(prompt,max_rounds=max_rounds)
    result['improved_prompt']=optimise(prompt,result['repositories'])+'\n7. If blocked, diagnose the exact failure, run a new targeted GitHub search, inspect candidate implementation, test against acceptance criteria and repeat within the search budget.\n8. For design, require screenshot comparisons at target viewports, responsive behaviour, accessibility, typography and motion quality. Do not declare success from popularity or a skill file alone.'
    result['answer']=None
    if strict and not result['quality_gate_passed']:result['answer_error']='Quality gate not met: more evidence or manual review required.'
    elif generate:
        try:result['answer']=answer_with_model(result['improved_prompt'])
        except Exception as e:result['answer_error']=str(e)
    return result
