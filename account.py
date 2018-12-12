import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, getcontext
from urllib.error import HTTPError

import tornado.escape
import tornado.ioloop
import tornado.locks
import tornado.web
from tornado.options import define, options, parse_command_line

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=True, help="run in debug mode")

getcontext().prec = 2


class CurrencyConverter:
    def __init__(self, amount, date, currency):
        self.currency = currency
        self.amount = Decimal(amount)
        self.date = date

    def get_data(self):
        response = None
        url = 'https://api.exchangeratesapi.io/{}?symbols=1{}'.format(self.date, self.currency)
        req = urllib.request.Request(url)
        try:
            result = urllib.request.urlopen(req).read()
        except HTTPError:
            result = None
        if result:
            content = json.loads(result.decode('utf-8'))
            if content:
                rates = content.get('rates', {})
                curr = rates.get(self.currency)
                if curr:
                    curr = Decimal(curr)
                    response = Decimal(self.amount / curr)
        return response


class UserAccount:
    BASE_CURRENCY = 'EUR'
    MAX_WEEKLY_SUM = 10000

    def __init__(self, username):
        self.username = username
        self.amount = Decimal(0.00)
        self.daily_balance = {}
        self.daily_withdrawal = defaultdict(Decimal)

    def _convert_money(self, amount, date, currency):
        date = self._format_date(date)
        converter = CurrencyConverter(amount, date, currency)
        amount = converter.get_data()
        return amount

    def _update_daily_balance(self, date):
        self.daily_balance[date] = self.amount

    def _update_daily_withdrawal(self, date, amount):
        self.daily_withdrawal[date] += amount

    def _get_weekly_total_amount_withdrawal(self, date):
        five_day_before = date - timedelta(days=5)
        total_sum = sum(amount for day, amount in self.daily_withdrawal.items() if five_day_before <= day <= date)
        return total_sum

    def _format_date(self, date):
        return date.strftime('%Y-%m-%d')

    def deposit(self, amount, date, currency):
        if currency != self.BASE_CURRENCY:
            amount = self._convert_money(amount, date, currency)
        if amount:
            self.amount += amount
            self._update_daily_balance(date)
        return amount

    def withdrawal(self, amount, date, currency):
        if currency != self.BASE_CURRENCY:
            amount = self._convert_money(amount, date, currency)

        weekly_withdrawal_amount = self._get_weekly_total_amount_withdrawal(date)
        if amount and weekly_withdrawal_amount + amount > self.MAX_WEEKLY_SUM:
            print('Limit of withdrawal was exceed')
            return None
        elif amount and self.amount >= amount:
            self.amount -= amount
            self._update_daily_balance(date)
            self._update_daily_withdrawal(date, amount)
            return amount
        else:
            return None

    def get_balances(self, date):
        balance = self.daily_balance.get(date)
        balance = '{0:f}'.format(balance)
        return balance


class UserList:
    def __init__(self, users):
        self.users = users

    def get_user_by_name(self, name):
        if name:
            for user in self.users:
                if user.username == name:
                    return user
        return None

    def transfer(self, to_account, from_account, amount, date, currency):
        withdrawal = from_account.withdrawal(amount, date, currency)
        if withdrawal:
            deposit = to_account.deposit(withdrawal, date, currency)
            if not deposit:
                # if something is wrong we will return money
                from_account.deposit(amount, date, currency)

            return amount
        return None


bank_users = UserList([UserAccount('bob'), UserAccount('alice')])


class MainHandler(tornado.web.RequestHandler):
    async def post(self):
        def is_valid_params(params):
            for param in params.values():
                if param is None:
                    return False
            return True

        method = self.get_argument('method', default=None, strip=False)
        account = self.get_argument('account', default=None, strip=False)
        from_account = self.get_argument('from_account', default=None, strip=False)
        to_account = self.get_argument('to_account', default=None, strip=False)
        date = self.get_argument('date', default=None, strip=False)
        amount = Decimal(self.get_argument('amount', default=0, strip=False))
        currency = self.get_argument('ccy', default=None, strip=False)
        user = bank_users.get_user_by_name(account)
        if date and method:
            date = datetime.strptime(date, "%Y-%m-%d")
            from_account = bank_users.get_user_by_name(from_account)
            to_account = bank_users.get_user_by_name(to_account)

            methods = {
                'deposit': {
                    'func': user.deposit if user else None,
                    'params': {'amount': amount, 'date': date, 'currency': currency},
                    'is_user_required': True
                },
                'withdrawal': {
                    'func': user.withdrawal if user else None,
                    'params': {'amount': amount, 'date': date, 'currency': currency},
                    'is_user_required': True
                },
                'transfer': {
                    'func': bank_users.transfer,
                    'params': {'from_account': from_account, 'to_account': to_account, 'amount': amount, 'date': date, 'currency': currency},
                    'is_user_required': False
                },
                'get_balances': {
                    'func': user.get_balances if user else None,
                    'params': {'date': date},
                    'is_user_required': True
                }
            }
            method_name = method
            method = methods.get(method)
            if method:
                func = method['func']
                params = method['params']
                is_user_required = method['is_user_required']

                is_valid_params = is_valid_params(params)
                if is_valid_params and ((is_user_required and user) or (not is_user_required and not user)):
                    result = func(**params)
                    response = {
                        method_name: 'OK' if result else 'Error',
                        'amount': str(result) if result else '',
                        'date': date.strftime("%Y-%m-%d")
                    }
                else:
                    response = {
                        method_name: 'Error',
                        'error': 'Some params were missed'
                    }
            else:
                response = {
                    'error': "method doesn't found"
                }
        else:
            response = {
                'error': 'date and method are required'
            }
        self.write(json.dumps(response))


def make_app():
    return tornado.web.Application(
        [
            (r"/", MainHandler),
        ],
        debug=options.debug,
    )


def main():
    parse_command_line()
    app = make_app()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
