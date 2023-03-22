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
from erc20_demurrage_token.seal import ContractState
from erc20_demurrage_token.seal import CONTRACT_SEAL_STATE_MAX

# test imports
from erc20_demurrage_token.unittest import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)



class TestSeal(TestDemurrageDefault):

    def test_seal_dup(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.seal(self.address, self.accounts[0], 1)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.seal(self.address, self.accounts[0], 1)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)


    def test_seal_all(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.seal(self.address, self.accounts[0], CONTRACT_SEAL_STATE_MAX)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.is_sealed(self.address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertTrue(c.parse_is_sealed(r))


    def test_seal_minter(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
    
        (tx_hash, o) = c.add_minter(self.address, self.accounts[0], self.accounts[1])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.seal(self.address, self.accounts[0], ContractState.MINTER_STATE)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.add_minter(self.address, self.accounts[0], self.accounts[2])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        o = c.is_sealed(self.address, ContractState.MINTER_STATE, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertTrue(c.parse_is_sealed(r))


    def test_seal_expiry(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
    
        (tx_hash, o) = c.set_expire_period(self.address, self.accounts[0], 10)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.set_expire_period(self.address, self.accounts[0], 20)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.seal(self.address, self.accounts[0], ContractState.EXPIRY_STATE)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.set_expire_period(self.address, self.accounts[0], 21)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        o = c.is_sealed(self.address, ContractState.EXPIRY_STATE, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertTrue(c.parse_is_sealed(r))


    def test_seal_set_sink_address(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
    
        (tx_hash, o) = c.set_sink_address(self.address, self.accounts[0], self.accounts[3])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.set_sink_address(self.address, self.accounts[0], self.accounts[4])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.seal(self.address, self.accounts[0], ContractState.SINK_STATE)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.set_sink_address(self.address, self.accounts[0], self.accounts[5])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        o = c.is_sealed(self.address, ContractState.SINK_STATE, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertTrue(c.parse_is_sealed(r))


    def test_seal_cap(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
    
        (tx_hash, o) = c.set_max_supply(self.address, self.accounts[0], 100)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.set_max_supply(self.address, self.accounts[0], 200)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.seal(self.address, self.accounts[0], ContractState.CAP_STATE)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.set_max_supply(self.address, self.accounts[0], 300)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        o = c.is_sealed(self.address, ContractState.CAP_STATE, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertTrue(c.parse_is_sealed(r))


if __name__ == '__main__':
    unittest.main()


