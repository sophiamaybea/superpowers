import unittest
from unittest.mock import patch
from engine.discovery import community_research
from engine.laya import decide
from engine.core import investigate

class DiscoveryTests(unittest.TestCase):
    @patch('engine.discovery.fetch_json')
    def test_public_communities(self,mock_fetch):
        mock_fetch.side_effect=[{'hits':[{'title':'Approach','url':'https://example.org','objectID':'12'}]},
                                {'items':[{'title':'Answer','link':'https://stackoverflow.com/q/1','is_answered':True}]}]
        r=community_research('fix browser rendering')
        self.assertEqual(len(r['sources']),2)
        self.assertTrue(all(s['untrusted'] for s in r['sources']))
    def test_laya_not_falsely_enabled(self):
        self.assertFalse(decide('task',['a','b'],endpoint='https://remote.example')['enabled'])
    @patch('engine.iterative.research_until_helpful')
    def test_iterative_research(self,research):
        research.return_value={'rounds':[{'round':1},{'round':2}], 'repositories':[{'name':'owner/repo'}],
           'errors':[], 'unique_repository_candidates':1}
        r=investigate('problem',max_rounds=2,include_communities=False)
        self.assertEqual(len(r['rounds']),2)
        self.assertEqual(r['unique_repository_candidates'],1)
        research.assert_called_once()
if __name__=='__main__':unittest.main()
