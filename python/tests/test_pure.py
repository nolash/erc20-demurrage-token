# standard imports
import os
import unittest
import json
import logging
import math

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.error import JSONRPCException
import eth_tester

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from tests.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class Test(TestDemurrageDefault):

    def test_fractional_state(self):
        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        with self.assertRaises(JSONRPCException):
            o = c.remainder(self.address, 2, 1, sender_address=self.accounts[0])
            self.rpc.do(o)
 
        with self.assertRaises(JSONRPCException):
            o = c.remainder(self.address, 0, 100001, sender_address=self.accounts[0])
            self.rpc.do(o)       

        o = c.remainder(self.address, 1, 2, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        remainder = c.parse_remainder(r)
        self.assertEqual(remainder, 0);

        whole = 5000001
        parts = 20000
        expect = whole - (math.floor(whole/parts) * parts) 
        o = c.remainder(self.address, parts, whole, sender_address=self.accounts[0])
        r = self.rpc.do(o)      
        remainder = c.parse_remainder(r)
        self.assertEqual(remainder, expect)

        parts = 30000
        expect = whole - (math.floor(whole/parts) * parts) 
        o = c.remainder(self.address, parts, whole, sender_address=self.accounts[0])
        r = self.rpc.do(o)      
        remainder = c.parse_remainder(r)
        self.assertEqual(remainder, expect)

        parts = 40001
        expect = whole - (math.floor(whole/parts) * parts) 
        o = c.remainder(self.address, parts, whole, sender_address=self.accounts[0])
        r = self.rpc.do(o)      
        remainder = c.parse_remainder(r)
        self.assertEqual(remainder, expect)


if __name__ == '__main__':
    unittest.main()
