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


class TestExpire(TestDemurrageDefault):

    def test_expires(self):
        mint_amount = self.default_supply
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        for i in range(3):
            (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[i+1], mint_amount)
            r = self.rpc.do(o)

        (tx_hash, o) = c.set_expire_period(self.address, self.accounts[0], 2)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.expires(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        expiry_time = c.parse_expires(r)

        self.backend.time_travel(expiry_time + 60)
        o = block_latest()
        r = self.rpc.do(o)
        o = block_by_number(r)
        r = self.rpc.do(o)
        self.assertGreaterEqual(r['timestamp'], expiry_time)
        
        nonce_oracle = RPCNonceOracle(self.sink_address, self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.sink_address, self.accounts[2], 1)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.transfer(self.address, self.sink_address, self.accounts[2], 1)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assert_within(balance, 0.9604 * mint_amount, 1)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        supply = c.parse_balance(r)

        (tx_hash, o) = c.change_period(self.address, self.sink_address)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)

        o = c.decay_by(self.address, supply, int((expiry_time - self.start_time) / 60), sender_address=self.sink_address)
        r = self.rpc.do(o)
        target_balance = c.parse_balance(r)

        self.assert_within_lower(balance, supply - target_balance, 0.0001)


if __name__ == '__main__':
    unittest.main()
