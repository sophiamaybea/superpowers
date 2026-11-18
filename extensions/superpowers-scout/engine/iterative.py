"""Evidence-led discovery with adaptive failure queries. No autonomous code execution."""
from __future__ import annotations
from functools import wraps
import datetime
import re
from .core import (keywords,github_json,cached,_repo,inspect_repo,score_repo,
                   matched_terms,optimise,answer_with_model,refine_prompt_with_model,
                   ProviderError,RateLimitError,RequestBudgetExceeded,github_request_budget)

CAPABILITIES={
 'clone':{'playwright','screenshot','visual','regression','responsive','browser','pixelmatch','puppeteer','webgl','css','animation'},
 'design':{'design','typography','animation','accessibility','gsap','webgl','ui','motion','frontend','components','css'},
 'general':set(),
 'skill':{'agent','skill','mcp','workflow'}
}


def category_for(prompt):
    p=prompt.lower()
    if re.search(r'\b(clone|cloning|replicate|recreate|rebuild|screenshot.to.code|pixel.perfect)\b',p):return 'clone'
    if re.search(r'\b(design|typography|animation|frontend|ui|ux|portfolio|landing page)\b',p):return 'design'
    if re.search(r'\b(skill|skills|skill\.md|mcp)\b',p):return 'skill'
    return 'general'


def plan_queries(prompt,failure=''):
    """Distinct strategies; observed failures override generic discovery terms."""
    category=category_for(prompt)
    terms=keywords(prompt)
    base=' '.join(terms[:5]) or 'software implementation'
    if category=='clone':variants=[base+' screenshot comparison',
            'playwright visual regression responsive CSS',
            base+' browser automation test',
            'website reconstruction layout typography screenshot']
    elif category=='design':variants=[base+' design system',
            'accessibility frontend typography components',
            'gsap threejs responsive animation examples',
            base+' visual testing']
    elif category=='skill':variants=[base+' agent skills',
            'SKILL.md workflow implementation',
            base+' mcp integration',
            'agent skills quality evaluation']
    else:variants=[base,base+' implementation documentation',
                    base+' alternative libraries',base+' test examples']
    if failure.strip():
        short=' '.join(keywords(failure)[:5]) or failure.strip()[:80]
        variants=[base+' '+short+' fix',
                  short+' issue debugging workaround',
                  base+' alternative implementation',
                  short+' reproducible test']
    seen=set();out=[]
    for v in variants:
        query=' '.join(v.split())[:180]
        if query not in seen:seen.add(query);out.append(query)
    return category,out


def evidence_score(repo,category,task_terms=None):
    """Capability evidence without a SKILL.md bonus for software libraries.

    README and topics are included. The score is a prioritisation heuristic only.
    """
    capability_matches=matched_terms(repo,CAPABILITIES.get(category,set()))
    task_matches=matched_terms(repo,task_terms or [])
    # A SKILL.md is relevant when the user explicitly asks for agent skills.
    skill_bonus=min(len(repo.get('skills',[])),2)*6 if category=='skill' else 0
    score=len(capability_matches)*12+len(task_matches)*8+skill_bonus
    score+= min(int(repo.get('stars') or 0),5000)/1250
    if repo.get('readme'):score+=2
    if repo.get('license') not in (None,'NOASSERTION'):score+=2
    if repo.get('archived'):score-=60
    if repo.get('fork'):score-=3
    if repo.get('inspection_errors'):score-=3
    matches=sorted(set(capability_matches+task_matches))
    return round(score,2),matches


def _limited_research(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        with github_request_budget() as budget:
            result=fn(*args,**kwargs)
            result['github_api_requests']=budget['used']
            result['github_api_budget_remaining']=budget['remaining']
            return result
    return wrapped

@_limited_research
def research_until_helpful(prompt,max_rounds=4,minimum_candidates=2,fetch=github_json,
                           inspector=inspect_repo,failure='',attempted=None):
    """Adaptive *research*, NOT an automated implementation or repair loop.

    Default tries at least two distinct queries. A reported failure encourages
    alternative searches rather than halting at the first two plausible repos.
    """
    category,queries=plan_queries(prompt,failure=failure)
    rounds=max(1,min(int(max_rounds),6))
    if rounds>len(queries):
        queries=queries+[queries[-1]+' alternative '+str(i) for i in range(rounds-len(queries))]
    found={};trace=[];errors=[];cache_hits=0;attempted=attempted or []
    stop='search_budget_exhausted'
    for n,query in enumerate(queries[:rounds],1):
        cache_hit=False;new=0;search_error=None;search_order=[]
        try:
            params={'q':query+' in:name,description,readme','per_page':10}
            if fetch is github_json:
                data,cache_hit=cached('v05:search:'+query,lambda:fetch('search/repositories',params),900)
            else:data=fetch('search/repositories',params)
            cache_hits+=int(cache_hit)
            for item in data.get('items',[])[:10]:
                if not isinstance(item,dict) or not item.get('full_name'):continue
                search_order.append(item['full_name'])
                if item['full_name'] not in found:new+=1
                found[item['full_name']]=_repo(item) if item['full_name'] not in found else found[item['full_name']]
        except (RateLimitError,RequestBudgetExceeded) as exc:
            search_error=str(exc);errors.append({'round':n,'type':'rate_limit_or_budget','error':search_error})
            stop='budget_or_rate_limited'
        except (ProviderError,ValueError,TypeError,KeyError) as exc:
            search_error='GitHub search unavailable';errors.append({'round':n,'type':'provider','error':search_error})
        # Inspect at most 4 new top candidates per round. README evidence is used
        # *after* enrichment to rerank, not omitted from ranking.
        # Preserve the top results of GitHub's README-inclusive ranking so
        # a README-only match is not discarded before we fetch its README.
        metadata_order=[r['name'] for r in sorted(found.values(),key=lambda r:-score_repo(r,keywords(prompt)))[:8]]
        priority=list(dict.fromkeys(search_order[:2]+metadata_order+search_order[2:]))
        inspected_this_round=0
        for name in priority:
            r=found[name]
            if 'readme' in r:continue
            if inspected_this_round>=4:break
            inspected_this_round+=1
            try:
                if inspector is inspect_repo:
                    key='v05:inspect:'+r['name']+':'+str(category=='skill')
                    extra,hit=cached(key,lambda r=r:inspector(r,include_skills=category=='skill'),3600)
                    cache_hits+=int(hit)
                else:extra=inspector(r)
                r.update(extra or {})
            except (RateLimitError,RequestBudgetExceeded) as exc:
                errors.append({'round':n,'type':'rate_limit_or_budget','error':str(exc)})
                stop='budget_or_rate_limited';break
            except Exception:
                r.update({'readme':False,'readme_excerpt':'','inspection_errors':['Inspection failed']})
        ranked=sorted(found.values(),key=lambda r:-evidence_score(r,category,keywords(prompt))[0])
        for repo in ranked:
            repo['evidence_score'],repo['matched_capabilities']=evidence_score(repo,category,keywords(prompt))
        viable=[r for r in ranked if r.get('readme') is not None and r.get('evidence_score',0)>=20
                and r.get('matched_capabilities') and not r.get('archived') and not r.get('inspection_errors')]
        trace.append({'round':n,'query':query,'new_candidates':new,'total_candidates':len(found),
                      'reviewed_candidates':sum('readme' in r for r in found.values()),
                      'viable_candidates':len(viable),'cache_hit':cache_hit,'error':search_error})
        if stop=='budget_or_rate_limited':break
        # We only stop when multiple independent query strategies have been tried.
        # Failure recovery uses at least three when the user provides an error.
        minimum_rounds=min(rounds,3 if failure else 2)
        if n>=minimum_rounds and len(viable)>=minimum_candidates:
            stop='evidence_shortlist_ready';break
    ranked=sorted(found.values(),key=lambda r:-r.get('evidence_score',0))
    viable=[r for r in ranked if r.get('readme') is not None and r.get('evidence_score',0)>=20
            and r.get('matched_capabilities') and not r.get('archived') and not r.get('inspection_errors')]
    passed=bool(len(viable)>=minimum_candidates and stop!='budget_or_rate_limited')
    return {'category':category,'rounds':trace,'repositories':ranked[:8],
            'unique_repository_candidates':len(found),'cache_hits':cache_hits,
            'viable_candidates':len(viable),'evidence_gate_passed':passed,
            'quality_gate_passed':passed, # backwards-compatible *candidate* gate, not product quality
            'errors':errors,'stopping_reason':stop,
            'quality_caveat':'Shortlisted repositories are untested leads. No code, website, licence or accessibility audit has been performed.',
            'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}


def solve(prompt,generate=True,strict=False,max_rounds=4,failure='',refine_prompt=True):
    result=research_until_helpful(prompt,max_rounds=max_rounds,failure=failure)
    brief=optimise(prompt,result['repositories'],category=result['category'],failure=failure)
    method='deterministic_brief'
    if strict and not result['evidence_gate_passed']:
        result['execution_brief']=brief
        result['improved_prompt']=brief
        result['prompt_optimisation_method']=method
        result['answer']=None
        result['answer_error']='Strict evidence gate: no adequate shortlist; answer not generated.'
        return result
    if refine_prompt:
        try:
            model_brief=refine_prompt_with_model(brief)
            if model_brief:brief=model_brief;method='model_refined_brief'
        except ProviderError:
            result.setdefault('warnings',[]).append('Prompt refinement unavailable; deterministic brief used')
    result['execution_brief']=brief
    result['improved_prompt']=brief # compatibility alias, not evidence of AI refinement
    result['prompt_optimisation_method']=method
    result['answer']=None
    if strict and not result['evidence_gate_passed']:
        result['answer_error']='Strict evidence gate: no adequate shortlist; answer not generated.'
    elif generate:
        try:result['answer']=answer_with_model(brief)
        except ProviderError:result['answer_error']='Model generation unavailable'
    return result
