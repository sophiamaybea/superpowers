import json
import unittest
import urllib.error
from email.message import Message
from unittest.mock import patch
from engine.core import github_request_budget,github_json,RequestBudgetExceeded,RateLimitError

class DummyResponse:
    def __init__(self,body):self.body=body
    def read(self,limit=None):return self.body
    def __enter__(self):return self
    def __exit__(self,*args):return False

class BudgetTests(unittest.TestCase):
    @patch('engine.core.urllib.request.urlopen')
    def test_budget_stops_requests_before_network(self,urlopen):
        urlopen.return_value=DummyResponse(b'{"items":[]}')
        with github_request_budget(1) as budget:
            github_json('search/repositories',{'q':'test'})
            with self.assertRaises(RequestBudgetExceeded):github_json('search/repositories',{'q':'again'})
        self.assertEqual(budget['used'],1)
        urlopen.assert_called_once()
    @patch('engine.core.urllib.request.urlopen')
    def test_rate_limit_error_is_sanitised(self,urlopen):
        headers=Message();headers['X-RateLimit-Remaining']='0';headers['Retry-After']='30'
        urlopen.side_effect=urllib.error.HTTPError('https://api.github.com/x',403,'Forbidden',headers,None)
        with self.assertRaises(RateLimitError) as err:github_json('search/repositories')
        self.assertEqual(err.exception.retry_after,30)
        self.assertNotIn('https://',str(err.exception))

if __name__=='__main__':unittest.main()
