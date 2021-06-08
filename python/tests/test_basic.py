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


class TestBasic(TestDemurrageDefault):

#    def test_hello(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        o = c.actual_period(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        
#        self.backend.time_travel(self.start_time + self.period_seconds + 1)
#        o = c.actual_period(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#
#
#    def test_balance(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
#        r = self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 1024)


    def test_apply_demurrage(self):
        modifier = (10 ** 38)

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_amount = c.parse_demurrage_amount(r)
        self.assertEqual(modifier, demurrage_amount)

        o = block_latest()
        r = self.rpc.do(o)
        o = block_by_number(r)
        b = self.rpc.do(o)
        logg.debug('block {} start {}'.format(b['timestamp'], self.start_time))

        self.backend.time_travel(self.start_time + 2)
        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_amount = c.parse_demurrage_amount(r)
        self.assertEqual(modifier, demurrage_amount)

        self.backend.time_travel(self.start_time + 61)
        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_amount = c.parse_demurrage_amount(r)
        modifier_base = 1000000 - self.tax_level
        logg.debug('modifier base {}'.format(modifier_base))
        modifier = int(modifier_base * (10 ** 32)) # 38 decimal places minus 6 (1000000)
        self.assertEqual(modifier, demurrage_amount)

        self.backend.time_travel(self.start_time + 601)
        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_amount = c.parse_demurrage_amount(r)
        modifier_base = ((1000000 - self.tax_level) / 1000000) ** 10
        modifier = int(modifier_base * (10 ** 12))

        rounding_tolerance_nano = 4000000 # 0.000004% precision
        demurrage_amount_truncate = int(demurrage_amount / (10 ** 26)) # equals 12 decimal places
        self.assertGreaterEqual(modifier, demurrage_amount_truncate - rounding_tolerance_nano)
        self.assertLessEqual(modifier, demurrage_amount_truncate)


#    def test_mint(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
#        r = self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 1024)
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 976)
#        r = self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 2000)
#
#
#        self.backend.time_travel(self.start_time + 61)
#        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, int(2000 * 0.98))
#
#
#    def test_minter_control(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[1], self.accounts[2], 1024)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 0)
#            
#        (tx_hash, o) = c.add_minter(self.address, self.accounts[1], self.accounts[1])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 0)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.add_minter(self.address, self.accounts[0], self.accounts[1])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[1], self.accounts[2], 1024)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        (tx_hash, o) = c.add_minter(self.address, self.accounts[1], self.accounts[2])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 0)
#
#        (tx_hash, o) = c.remove_minter(self.address, self.accounts[1], self.accounts[1])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[1], self.accounts[2], 1024)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 0)
#            
#
#    def test_base_amount(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
#        self.rpc.do(o)
#
#        self.backend.time_travel(self.start_time + 61)
#        (tx_hash, o) = c.apply_demurrage(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        o = c.to_base_amount(self.address, 1000, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        amount = c.parse_to_base_amount(r)
#        self.assertEqual(amount, 1020)
#
#
#    def test_transfer(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
#        self.rpc.do(o)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[1], self.accounts[2], 500)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 524)
#
#        o = c.balance_of(self.address, self.accounts[2], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 500)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[2], self.accounts[1], 500)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#       
#
#    def test_transfer_from(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
#        self.rpc.do(o)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.approve(self.address, self.accounts[1], self.accounts[2], 500)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#        
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 1024)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer_from(self.address, self.accounts[2], self.accounts[1], self.accounts[3], 500)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
# 
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 524)
#
#        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, 500)


if __name__ == '__main__':
    unittest.main()
