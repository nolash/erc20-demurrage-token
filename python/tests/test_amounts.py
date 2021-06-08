# standard imports
import os
import unittest
import json
import logging

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from tests.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)

class TestAmounts(TestDemurrageDefault):

    def test_mints(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1000)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds)

        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        r = self.rpc.do(o)
        
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 817)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1000)
        r = self.rpc.do(o)

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assert_within_lower(balance, 1817, 750)

        self.backend.time_travel(self.start_time + self.period_seconds * 2)

        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        r = self.rpc.do(o)
        
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)

        expected_balance = ((1 - self.tax_level / 1000000) ** 10) * 1000
        expected_balance += ((1 - self.tax_level / 1000000) ** 20) * 1000
        self.assert_within_lower(balance, expected_balance, 500)


    def test_transfers(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 2000)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], self.accounts[2], 500)
        r = self.rpc.do(o)
     
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 817)


if __name__ == '__main__':
    unittest.main()
