import json
import urllib
from urllib.parse import urlencode

from tornado.testing import AsyncHTTPTestCase

import account


class TestHelloApp(AsyncHTTPTestCase):
    def get_app(self):
        return account.make_app()

    def _make_request(self, params):
        response = self.fetch('/', method="POST", body=urlencode(params))
        answer = response.body.decode()
        answer = json.loads(answer)
        return answer

    def test_operations(self):
        params = {
            'method': 'deposit',
            'account': 'bob',
            'date': '2018-12-09',
            'amount': 2000,
            'ccy': 'EUR'
        }

        response = self._make_request(params)
        self.assertEqual(response['deposit'], 'OK')
        self.assertEqual(response['amount'], '2000')
        self.assertEqual(response['date'], '2018-12-09')

        params = {
            'method': 'withdrawal',
            'account': 'bob',
            'date': '2018-12-09',
            'amount': 1000,
            'ccy': 'EUR'
        }

        response = self._make_request(params)
        self.assertEqual(response['withdrawal'], 'OK')
        self.assertEqual(response['amount'], '1000')
        self.assertEqual(response['date'], '2018-12-09')
        params2 = {
            'method': 'withdrawal',
            'account': 'bob',
            'date': '2018-12-09',
            'amount': 2000,
            'ccy': 'EUR'
        }
        response = self._make_request(params2)
        self.assertEqual(response['withdrawal'], 'Error')
        self.assertEqual(response['amount'], '')
        self.assertEqual(response['date'], '2018-12-09')

        params = {
            'method': 'get_balances',
            'account': 'bob',
            'date': '2018-12-09',
        }
        response = self._make_request(params)
        self.assertEqual(response['get_balances'], 'OK')
        self.assertEqual(response['amount'], '1000')

        params = {
            'method': 'transfer',
            'from_account': 'bob',
            'to_account': 'alice',
            'date': '2018-12-09',
            'amount': 1000,
            'ccy': 'EUR'
        }
        response = self._make_request(params)
        self.assertEqual(response['transfer'], 'OK')
        self.assertEqual(response['amount'], '1000')
        # no money
        params = {
            'method': 'get_balances',
            'account': 'bob',
            'date': '2018-12-09',
        }
        response = self._make_request(params)
        self.assertEqual(response['get_balances'], 'OK')
        self.assertEqual(response['amount'], '0')

        params2 = {
            'method': 'withdrawal',
            'account': 'bob',
            'date': '2018-12-09',
            'amount': 100,
            'ccy': 'EUR'
        }
        response = self._make_request(params2)
        # also no money
        self.assertEqual(response['withdrawal'], 'Error')
        self.assertEqual(response['amount'], '')
        self.assertEqual(response['date'], '2018-12-09')

