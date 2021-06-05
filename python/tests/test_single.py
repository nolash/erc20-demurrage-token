import os
import unittest
import json
import logging

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.block import block_latest
from chainlib.eth.address import to_checksum_address
from hexathon import (
        strip_0x,
        add_0x,
        )

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from tests.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestRedistributionSingle(TestDemurrageDefault):

    def test_single_even_if_multiple(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 100000000)
        r = self.rpc.do(o)

        external_address = to_checksum_address('0x' + os.urandom(20).hex())
        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], external_address, 10000000)
        r = self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[3], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[2], external_address, 20000000)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + 61)
        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        self.rpc.do(o)
        o = receipt(tx_hash)
        rcpt = self.rpc.do(o)
        self.assertEqual(rcpt['status'], 1)

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

