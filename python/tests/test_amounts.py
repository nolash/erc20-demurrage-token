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
from erc20_demurrage_token.unittest import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)

class TestAmounts(TestDemurrageDefault):

    def test_mints(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1000)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        self.backend.time_travel(self.start_time + self.period_seconds)

        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        r = self.rpc.do(o)
        
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assertEqual(balance, 980)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1000)
        r = self.rpc.do(o)

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assert_within_lower(balance, 1980, 750)

        self.backend.time_travel(self.start_time + self.period_seconds * 2)

        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        r = self.rpc.do(o)
        
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)

        expected_balance = ((1 - self.tax_level / 1000000) ** 10) * 1000
        expected_balance += ((1 - self.tax_level / 1000000) ** 20) * 1000
        #self.assert_within_lower(balance, expected_balance, 500)
        self.assertEqual(balance, 1940)

    def test_transfers(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 2000)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds)

        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        r = self.rpc.do(o)
 
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assertEqual(balance, 1960)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], self.accounts[2], 500)
        r = self.rpc.do(o)
     
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assertEqual(balance, 1460)

        o = c.balance_of(self.address, self.accounts[2], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assert_within_lower(balance, 500, 2000)


    def test_dynamic_amount(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 2000)
        r = self.rpc.do(o)

        cases = [
            (60, 1960),
            (120, 1920),
            (180, 1882),
            (240, 1844),
            (300, 1807),
            (360, 1771),
            (420, 1736),
            (480, 1701),
            (540, 1667),
            (600, 1634),
                ]
        for case in cases:
            self.backend.time_travel(self.start_time + int(case[0] * (self.period_seconds / 60)))

            o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
            r = self.rpc.do(o)
            balance = c.parse_balance(r)
            self.assert_within_lower(balance, case[1], 10000)


    def test_sweep(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], 2000)
        r = self.rpc.do(o)

        (tx_hash, o) = c.sweep(self.address, self.accounts[0], self.accounts[1])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.balance_of(self.address, self.accounts[0], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertEqual(c.parse_balance(r), 0)
 
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assert_within(c.parse_balance(r), 2000, 1)
 

if __name__ == '__main__':
    unittest.main()
