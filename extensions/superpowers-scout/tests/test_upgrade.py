import unittest,sys,os
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from engine.core import keywords,optimise,inspect_repo
class UpgradeTests(unittest.TestCase):
 def test_keywords(self):self.assertIn('lip-sync',keywords('Build lip-sync app'))
 def test_prompt_untrusted(self):self.assertIn('untrusted',optimise('Make a site',[]))
 def test_skill_reference(self):self.assertIn('SKILL.md',optimise('Build', [{'name':'x/y','url':'https://github.com/x/y','skills':['https://github.com/x/y/blob/main/SKILL.md']}]))
if __name__=='__main__':unittest.main()
