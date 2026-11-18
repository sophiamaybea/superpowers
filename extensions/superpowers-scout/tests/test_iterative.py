import unittest
from unittest.mock import patch
from engine.iterative import research_until_helpful,plan_queries,evidence_score,solve

class IterativeTests(unittest.TestCase):
    def test_recovery_searches(self):
        seen=[]
        def fetch(path,params):seen.append(params['q']);return {'items':[]}
        r=research_until_helpful('Clone a website',fetch=fetch,inspector=lambda r:{})
        self.assertEqual(len(seen),4)
        self.assertEqual(len(set(seen)),4)
        self.assertEqual(r['stopping_reason'],'search_budget_exhausted')
    def test_does_not_stop_on_first_query(self):
        seen=[]
        def fetch(path,params):
            seen.append(params['q'])
            return {'items':[{'full_name':f'x/repo{i}','html_url':f'https://github.com/x/repo{i}',
                 'description':'playwright visual screenshot responsive','stargazers_count':30,
                 'license':{'spdx_id':'MIT'}} for i in range(3)]}
        def inspect(repo):return {'skills':['https://github.com/x/repo/SKILL.md'],'readme':True,
                                   'readme_excerpt':'playwright screenshot CSS','inspection_errors':[]}
        r=research_until_helpful('Clone a website',fetch=fetch,inspector=inspect)
        self.assertTrue(r['evidence_gate_passed'])
        self.assertEqual(len(r['rounds']),2)
        self.assertEqual(len(seen),2)
    def test_failure_drives_three_distinct_queries(self):
        seen=[]
        def fetch(path,params):
            seen.append(params['q'])
            return {'items':[{'full_name':f'x/repo{i}','html_url':f'https://github.com/x/repo{i}',
               'description':'playwright visual screenshot','stargazers_count':200,
               'license':{'spdx_id':'MIT'}} for i in range(3)]}
        def inspector(r):return {'readme':True,'readme_excerpt':'playwright screenshot visual'}
        r=research_until_helpful('Clone a website',failure='mobile screenshot text overflow',fetch=fetch,inspector=inspector)
        self.assertGreaterEqual(len(seen),3)
        self.assertIn('overflow',seen[0])
        self.assertEqual(r['stopping_reason'],'evidence_shortlist_ready')
    def test_design_plan(self):self.assertEqual(plan_queries('Improve typography and design')[0],'design')
    def test_web_design_skill_phrase_classifies_clone(self):
        self.assertEqual(plan_queries('Clone this website with agent skills')[0],'clone')
    def test_archived_penalty(self):
        r={'name':'x/y','description':'design typography','skills':[],'readme':True,'stars':50,
           'archived':True,'fork':False,'license':'MIT'}
        self.assertLess(evidence_score(r,'design')[0],20)
    def test_skill_file_bias_removed(self):
        lib={'name':'microsoft/playwright','description':'browser automation visual regression',
             'readme_excerpt':'screenshot compare responsive page browser testing',
             'skills':[],'readme':True,'stars':2000,'archived':False,'fork':False,'license':'Apache-2.0'}
        obscure={'name':'unknown/screenshot-skills','description':'playwright',
                 'readme_excerpt':'','skills':['skill'+str(i) for i in range(12)],
                 'readme':True,'stars':2,'archived':False,'fork':False,'license':'MIT'}
        self.assertGreater(evidence_score(lib,'clone')[0],evidence_score(obscure,'clone')[0])
    def test_readme_only_first_result_is_inspected(self):
        items=[{'full_name':'author/readme-only','html_url':'https://github.com/author/readme-only',
                'description':'miscellaneous','stargazers_count':2,'license':{'spdx_id':'MIT'}}]
        items += [{'full_name':f'x/visually-related-{i}','html_url':f'https://github.com/x/visually-related-{i}',
                   'description':'screenshot responsive visual playwright', 'stargazers_count':100,
                   'license':{'spdx_id':'MIT'}} for i in range(8)]
        inspected=[]
        def inspector(repo):
            inspected.append(repo['name'])
            return {'readme':True,'readme_excerpt':'playwright visual screenshot browser' if repo['name'].endswith('readme-only') else ''}
        r=research_until_helpful('Clone a website',max_rounds=1,fetch=lambda p,q:{'items':items},inspector=inspector)
        self.assertIn('author/readme-only',inspected)
        self.assertIn('playwright',next(x for x in r['repositories'] if x['name']=='author/readme-only')['matched_capabilities'])
    def test_inspection_budget_replenishes_each_round(self):
        count=[]
        def fetch(path,params):
            n=len(count)
            return {'items':[{'full_name':f'org/repo-{params["q"].split()[0]}-{i}',
              'html_url':f'https://github.com/org/repo-{params["q"].split()[0]}-{i}',
              'description':'playwright screenshot','license':{'spdx_id':'MIT'}} for i in range(8)]}
        def inspector(r):count.append(r['name']);return {'readme':True,'readme_excerpt':'playwright screenshot'}
        r=research_until_helpful('Clone a website',max_rounds=3,minimum_candidates=100,fetch=fetch,inspector=inspector)
        self.assertGreaterEqual(len(count),5)
    @patch('engine.iterative.refine_prompt_with_model')
    @patch('engine.iterative.answer_with_model')
    @patch('engine.iterative.research_until_helpful')
    def test_strict_gate_no_model_calls(self,research,answer,refine):
        research.return_value={'category':'clone','repositories':[], 'evidence_gate_passed':False}
        r=solve('clone a website',strict=True)
        refine.assert_not_called();answer.assert_not_called()
        self.assertIn('Strict evidence gate',r['answer_error'])
    @patch('engine.iterative.refine_prompt_with_model',return_value='Model-based rewrite')
    @patch('engine.iterative.research_until_helpful')
    def test_model_refinement_is_properly_labelled(self,research,refine):
        research.return_value={'category':'design','repositories':[], 'evidence_gate_passed':True}
        r=solve('design a portfolio',generate=False)
        self.assertEqual(r['prompt_optimisation_method'],'model_refined_brief')
        self.assertEqual(r['execution_brief'],'Model-based rewrite')

if __name__=='__main__':unittest.main()
