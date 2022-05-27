# standard imports
import os
import unittest
import json
import logging

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        )
from chainlib.eth.address import to_checksum_address
from hexathon import (
        strip_0x,
        add_0x,
        )

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from erc20_demurrage_token.unittest.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)

class TestRedistribution(TestDemurrageDefault):


    def test_redistribution_boundaries(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        demurrage = (1 - (self.tax_level / 1000000)) * (10**28)
        supply = self.default_supply

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], supply)
        self.rpc.do(o)

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        logg.debug('balance before {} supply {}'.format(balance, supply))

        self.backend.time_travel(self.start_time + self.period_seconds)
        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)

        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        oo = c.to_redistribution_supply(self.address, r, sender_address=self.accounts[0])
        rr = self.rpc.do(oo)
        oo = c.to_redistribution_demurrage_modifier(self.address, r, sender_address=self.accounts[0])
        rr = self.rpc.do(oo)

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)

        self.backend.time_travel(self.start_time + self.period_seconds * 2 + 1)
        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)

        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.redistributions(self.address, 2, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        oo = c.to_redistribution_supply(self.address, r, sender_address=self.accounts[0])
        rr = self.rpc.do(oo)
        oo = c.to_redistribution_demurrage_modifier(self.address, r, sender_address=self.accounts[0])
        rr = self.rpc.do(oo)

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)


if __name__ == '__main__':
    unittest.main()
