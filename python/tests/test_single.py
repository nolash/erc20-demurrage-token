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
from dexif import to_fixed

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from erc20_demurrage_token.unittest import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestRedistributionSingle(TestDemurrageDefault):

    def test_single_even_if_multiple(self):
        mint_amount = 100000000

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        for i in range(3):
            (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[i+1], mint_amount)
            r = self.rpc.do(o)

        external_address = to_checksum_address('0x' + os.urandom(20).hex())
        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[2], external_address, int(mint_amount) * 0.1)
        r = self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[3], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[3], external_address, int(mint_amount) * 0.2)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds + 1)
        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[3])
        self.rpc.do(o)
        o = receipt(tx_hash)
        rcpt = self.rpc.do(o)
        self.assertEqual(rcpt['status'], 1)

        (tx_hash, o) = c.change_period(self.address, self.accounts[3])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        tax_modifier = 0.98
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assertEqual(balance, int(mint_amount * tax_modifier))

        o = c.balance_of(self.address, self.accounts[2], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        base_amount = mint_amount - int(mint_amount * 0.1)
        self.assertEqual(balance, int(base_amount * tax_modifier)) #(base_amount - (base_amount * (self.tax_level / 1000000))))

        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        base_amount = mint_amount - int(mint_amount * 0.2)
        self.assertEqual(balance, int(base_amount * tax_modifier)) #(base_amount - (base_amount * (self.tax_level / 1000000))))

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        new_supply = c.parse_total_supply(r)

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        expected_balance = new_supply - (new_supply * tax_modifier)
        self.assert_within_lower(balance, expected_balance, 1)


if __name__ == '__main__':
    unittest.main()
