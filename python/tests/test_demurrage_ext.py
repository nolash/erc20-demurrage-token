# standard imports
import datetime
import unittest

# local imports
from erc20_demurrage_token.demurrage import DemurrageCalculator

# test imports
from tests.base import TestDemurrage


class TestEmulate(TestDemurrage):

    def test_amount_since(self):

        d = datetime.datetime.utcnow() - datetime.timedelta(seconds=29, hours=5, minutes=3, days=4)
        c = DemurrageCalculator(0.00000050105908373373)
        a = c.amount_since(100, d.timestamp())
        self.assert_within_lower(a, 99.69667, 0.1)


if __name__ == '__main__':
    unittest.main()
