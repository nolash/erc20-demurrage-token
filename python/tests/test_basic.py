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
import eth_tester

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from tests.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestBasic(TestDemurrageDefault):

    def test_hello(self):

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        o = c.actual_period(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        
        self.backend.time_travel(self.start_time + 61)
        o = c.actual_period(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)


    def test_apply_demurrage(self):
        modifier = 10 * (10 ** 37)

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_amount = c.parse_demurrage_amount(r)
        self.assertEqual(modifier, demurrage_amount)

        self.backend.time_travel(self.start_time + 59)
        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_amount = c.parse_demurrage_amount(r)
        self.assertEqual(modifier, demurrage_amount)

        self.backend.time_travel(self.start_time + 61)
        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_amount = c.parse_demurrage_amount(r)
        modifier = int(98 * (10 ** 36))
        self.assertEqual(modifier, demurrage_amount)


    def test_mint(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 1024)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 976)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 2000)


        self.backend.time_travel(self.start_time + 61)
        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, int(2000 * 0.98))


    def test_minter_control(self):

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[1], self.accounts[2], 1024)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)
            
        (tx_hash, o) = c.add_minter(self.address, self.accounts[1], self.accounts[1])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.add_minter(self.address, self.accounts[0], self.accounts[1])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[1], self.accounts[2], 1024)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.add_minter(self.address, self.accounts[1], self.accounts[2])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        (tx_hash, o) = c.remove_minter(self.address, self.accounts[1], self.accounts[1])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[1], self.accounts[2], 1024)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)
            

    def test_base_amount(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
        self.rpc.do(o)

        self.backend.time_travel(self.start_time + 61)
        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        o = c.to_base_amount(self.address, 1000, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        amount = c.parse_to_base_amount(r)
        self.assertEqual(amount, 1020)


    def test_transfer(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], self.accounts[2], 500)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 524)

        o = c.balance_of(self.address, self.accounts[2], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 500)

        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[2], self.accounts[1], 500)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

       

    def test_transfer_from(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.accounts[1], self.accounts[2], 500)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 1024)

        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer_from(self.address, self.accounts[2], self.accounts[1], self.accounts[3], 500)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
 
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 524)

        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 500)


if __name__ == '__main__':
    unittest.main()
