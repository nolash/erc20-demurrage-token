# standard imports
import os
import unittest
import json
import logging
import datetime

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.block import (
        block_latest,
        block_by_number,
    )

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from tests.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestGrowth(TestDemurrageDefault):

    def test_grow_by(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        growth_factor = (1000000 + self.tax_level) / 1000000
        v = 1000000000
        o = c.grow_by(self.address, v, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        g = c.parse_grow_by(r)
        self.assertEqual(int(v * growth_factor),  g)

        period = 10
        growth_factor = (1 + (self.tax_level) / 1000000) ** period
        o = c.grow_by(self.address, v, period, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        g = c.parse_grow_by(r)
        self.assertEqual(int(v * growth_factor),  g)


    def test_decay_by(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        growth_factor = (1000000 - self.tax_level) / 1000000
        v = 1000000000
        o = c.decay_by(self.address, v, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        g = c.parse_decay_by(r)
        self.assertEqual(int(v * growth_factor),  g)

        period = 10
        growth_factor = (1 - (self.tax_level) / 1000000) ** period
        o = c.decay_by(self.address, v, period, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        g = c.parse_decay_by(r)
        self.assertEqual(int(v * growth_factor),  g)


if __name__ == '__main__':
    unittest.main()
