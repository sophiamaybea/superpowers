import unittest,sys,os
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from engine.iterative import research_until_helpful,plan_queries,evidence_score
class IterativeTests(unittest.TestCase):
 def test_recovery_searches(self):
  seen=[]
  def fetch(path,params):seen.append(params['q']);return {'items':[]}
  r=research_until_helpful('Clone a website',fetch=fetch,inspector=lambda r:{})
  self.assertEqual(len(seen),4)
  self.assertEqual(r['stopping_reason'],'search_budget_exhausted')
 def test_early_stop(self):
  def fetch(path,params):return {'items':[{'full_name':f'x/repo{i}','html_url':f'https://github.com/x/repo{i}','description':'playwright visual screenshot responsive','stargazers_count':30,'license':{'spdx_id':'MIT'}} for i in range(3)]}
  def inspect(repo):return {'skills':['https://github.com/x/repo/SKILL.md'],'readme':True,'inspection_errors':[]}
  r=research_until_helpful('Clone a website',fetch=fetch,inspector=inspect)
  self.assertTrue(r['quality_gate_passed']);self.assertEqual(len(r['rounds']),1)
 def test_design_plan(self):self.assertEqual(plan_queries('Improve typography and design')[0],'design')
 def test_archived_penalty(self):
  r={'name':'x/y','description':'design typography','skills':[],'readme':True,'stars':50,'archived':True,'fork':False,'license':'MIT'}
  self.assertLess(evidence_score(r,'design')[0],20)
if __name__=='__main__':unittest.main()
