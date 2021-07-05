# standard imports
import datetime
import unittest

# external imports
from chainlib.eth.nonce import RPCNonceOracle

# local imports
from erc20_demurrage_token import DemurrageToken
from erc20_demurrage_token.demurrage import DemurrageCalculator

# test imports
from erc20_demurrage_token.unittest.base import TestDemurrage


class TestEmulate(TestDemurrage):

    def test_amount_since(self):
        d = datetime.datetime.utcnow() - datetime.timedelta(seconds=29, hours=5, minutes=3, days=4)
        c = DemurrageCalculator(0.00000050105908373373)
        a = c.amount_since(100, d.timestamp())
        self.assert_within_lower(a, 99.69667, 0.1)


    def test_amount_since_slow(self):
        d = datetime.datetime.utcnow() - datetime.timedelta(seconds=29, hours=5, minutes=3, days=4)
        c = DemurrageCalculator(0.00000050105908373373)
        a = c.amount_since_slow(100, d.timestamp())
        self.assert_within_lower(a, 99.69667, 0.1)


    def test_from_contract(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        self.deploy(c, 'SingleNocap')
        dc = DemurrageCalculator.from_contract(self.rpc, self.chain_spec, self.address, sender_address=self.accounts[0])
        self.assertEqual(dc.r_min, 0.02)


if __name__ == '__main__':
    unittest.main()
