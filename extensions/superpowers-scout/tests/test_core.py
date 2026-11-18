import unittest
from unittest.mock import patch
from engine.core import keywords,optimise,run,score_repo
class Tests(unittest.TestCase):
 def test_keywords(self):self.assertIn('lip-sync',keywords('Build a lip-sync app'))
 def test_brief(self):self.assertIn('Objective: hello',optimise('hello',[]))
 @patch('engine.core.research')
 def test_research_before_answer(self,m):
  m.return_value={'repositories':[],'errors':[],'queries':[],'verified_live':True}
  d=run('test',generate=False);m.assert_called_once();self.assertIn('improved_prompt',d)
 def test_scoring(self):
  repo={'name':'example/lipsync','description':'lipsync','stars':20,'archived':False,'fork':False,'license':'MIT'}
  self.assertGreater(score_repo(repo,['lipsync']),score_repo({**repo,'archived':True},['lipsync']))
 @patch('engine.core.answer_with_model')
 @patch('engine.core.research')
 def test_strict_gate(self,m,model):
  m.return_value={'repositories':[],'errors':['GitHub unavailable'],'queries':[],'research_complete':False}
  r=run('build an app',strict=True);model.assert_not_called();self.assertIn('Strict research gate',r['answer_error'])
if __name__=='__main__':unittest.main()
