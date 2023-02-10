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
from erc20_demurrage_token.unittest import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestGrowth(TestDemurrageDefault):

    def test_decay_by(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        v = 1000000000
        o = c.decay_by(self.address, v, 20000, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        g = c.parse_decay_by(r)
        self.assertEqual(int(g), 990690498)
       
        o = c.decay_by(self.address, v, 43200, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        g = c.parse_decay_by(r)
        self.assertEqual(int(g), 980000000)


    def test_decay_steps(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        v = 1000000000
        o = c.decay_by(self.address, v, 43200, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        gr = c.parse_decay_by(r)

        v = 1000000000
        for i in range(100):
            o = c.decay_by(self.address, v, 432, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            v = c.parse_decay_by(r)

        self.assert_within_lower(int(v), int(gr), 0.1)


if __name__ == '__main__':
    unittest.main()
