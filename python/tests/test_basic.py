# standard imports
import os
import unittest
import json
import logging
import datetime

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle


# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from tests.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestBasic(TestDemurrageDefault):

    @unittest.skip('foo')
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


#    def test_mint(self):
#        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1024).transact()
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#
#        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
#        self.assertEqual(balance, 1024)
#
#        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 976).transact()
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#
#        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
#        self.assertEqual(balance, 2000)
#
#        self.eth_tester.time_travel(self.start_time + 61)
#        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
#        self.assertEqual(balance, int(2000 * 0.98))
#
#
#    def test_minter_control(self):
#        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
#            tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[2], 1024).transact({'from': self.w3.eth.accounts[1]})
#           
#        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
#            tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[1]})
#
#        tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[0]})
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#
#        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
#            tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[2]).transact({'from': self.w3.eth.accounts[1]})
#
#        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[2], 1024).transact({'from': self.w3.eth.accounts[1]})
#
#        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
#            tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[2]})
#
#        tx_hash = self.contract.functions.removeMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[1]})
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#
#        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
#            tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[2], 1024).transact({'from': self.w3.eth.accounts[1]})
#
#
#    def test_base_amount(self):
#        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1000).transact()
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#
#        self.eth_tester.time_travel(self.start_time + 61)
#
#        self.contract.functions.applyDemurrage().transact()
#        #demurrage_modifier = self.contract.functions.demurrageModifier().call()
#        #demurrage_amount = self.contract.functions.toDemurrageAmount(demurrage_modifier).call()
#        demurrage_amount = self.contract.functions.demurrageAmount().call()
#
#        a = self.contract.functions.toBaseAmount(1000).call();
#        self.assertEqual(a, 1020)
#
#
#    def test_transfer(self):
#        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1024).transact()
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#
#        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[2], 500).transact({'from': self.w3.eth.accounts[1]})
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#        logg.debug('tx {}'.format(r))
#
#        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
#        self.assertEqual(balance_alice, 524)
#
#        balance_bob = self.contract.functions.balanceOf(self.w3.eth.accounts[2]).call()
#        self.assertEqual(balance_bob, 500)
#
#        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[2], 500).transact({'from': self.w3.eth.accounts[1]})
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#        logg.debug('tx {}'.format(r))
#
#
#    def test_transfer_from(self):
#        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1024).transact()
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#
#        tx_hash = self.contract.functions.approve(self.w3.eth.accounts[2], 500).transact({'from': self.w3.eth.accounts[1]})
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#        logg.debug('tx {}'.format(r))
#
#        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
#        self.assertEqual(balance_alice, 1024)
#
#        tx_hash = self.contract.functions.transferFrom(self.w3.eth.accounts[1], self.w3.eth.accounts[3], 500).transact({'from': self.w3.eth.accounts[2]})
#        r = self.w3.eth.getTransactionReceipt(tx_hash)
#        self.assertEqual(r.status, 1)
#        logg.debug('tx {}'.format(r))
#
#        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
#        self.assertEqual(balance_alice, 524)
#
#        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[3]).call()
#        self.assertEqual(balance_alice, 500)


if __name__ == '__main__':
    unittest.main()
