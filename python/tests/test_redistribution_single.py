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
        same as hex_same,
        )
from dexif import from_fixed

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from erc20_demurrage_token.unittest import TestDemurrageDefault

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)

class TestRedistribution(TestDemurrageDefault):


    def test_redistribution_periods(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        demurrage = (1 - (self.tax_level / 1000000)) * (10**28)
        supply = self.default_supply

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], supply)
        self.rpc.do(o)

        for i in range(1, 100):
            logg.info('execute time travel to period {}'.format(i))
            self.backend.time_travel(self.start_time + (self.period_seconds * i))
            (tx_hash, o) = c.change_period(self.address, self.accounts[0])
            self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)

            redistribution_value = 0
            for lg in r['logs']:
                if hex_same(lg['topics'][0], '0x9a2a887706623ad3ff7fc85652deeceabe9fe1e00466c597972079ee91ea40d3'):
                    redistribution_value = int(strip_0x(lg['data']), 16)

            o = c.redistributions(self.address, i, sender_address=self.accounts[0])
            redistribution = self.rpc.do(o)

            o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            demurrage = from_fixed(r)

            o = c.redistributions(self.address, i-1, sender_address=self.accounts[0])
            redistribution = self.rpc.do(o)

            o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            demurrage_previous = from_fixed(r)

            o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            balance_sink = c.parse_balance(r)

            o = c.balance_of(self.address, self.accounts[0], sender_address=self.accounts[0])
            r = self.rpc.do(o)
            balance_minter = c.parse_balance(r)

            logg.info('testing redistro {} sink {} mint {} adds up to {} supply {} with demurrage between {} and {}'.format(redistribution_value, balance_sink, balance_minter, balance_sink + balance_minter, supply, demurrage_previous, demurrage))

            self.assert_within(balance_minter + balance_sink, supply, 10)


    def test_redistribution_catchup_periods(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        demurrage = (1 - (self.tax_level / 1000000)) * (10**28)
        supply = self.default_supply

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], supply)
        self.rpc.do(o)

        self.backend.time_travel(self.start_time + (self.period_seconds * 100))

        balance_minter = None
        balance_sink = None
        real_supply = None

        for i in range(1, 101):
            (tx_hash, o) = c.change_period(self.address, self.accounts[0])
            self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)

            o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            balance_sink = c.parse_balance(r)

            o = c.balance_of(self.address, self.accounts[0], sender_address=self.accounts[0])
            r = self.rpc.do(o)
            balance_minter = c.parse_balance(r)
            
            real_supply = balance_sink + balance_minter
            logg.info('period {} testing sink {} mint {} adds up to supply {} of original {} (delta {})'.format(i, balance_sink, balance_minter, real_supply, supply, supply - real_supply))

        i = 100
        o = c.redistributions(self.address, i, sender_address=self.accounts[0])
        redistribution = self.rpc.do(o)

        o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage = c.parse_to_redistribution_item(r)

        o = c.redistributions(self.address, i-1, sender_address=self.accounts[0])
        redistribution = self.rpc.do(o)

        o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage_previous = c.parse_to_redistribution_item(r)

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance_sink = c.parse_balance(r)

        o = c.balance_of(self.address, self.accounts[0], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance_minter = c.parse_balance(r)

        logg.debug('testing sink {} mint {} adds up to supply {} with demurrage between {} and {}'.format(balance_sink, balance_minter, real_supply, demurrage_previous, demurrage))

        self.assert_within_lower(balance_minter + balance_sink, supply, 0.1)


#    def test_redistribution_boundaries(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        demurrage = (1 - (self.tax_level / 1000000)) * (10**28)
#        supply = self.default_supply
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], supply)
#        self.rpc.do(o)
#
#        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance(r)
#        logg.debug('balance before {} supply {}'.format(balance, supply))
#
#        self.backend.time_travel(self.start_time + self.period_seconds)
#        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
#        r = self.rpc.do(o)
#
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        oo = c.to_redistribution_supply(self.address, r, sender_address=self.accounts[0])
#        rr = self.rpc.do(oo)
#        oo = c.to_redistribution_demurrage_modifier(self.address, r, sender_address=self.accounts[0])
#        rr = self.rpc.do(oo)
#
#        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance(r)
#
#        self.backend.time_travel(self.start_time + self.period_seconds * 2 + 1)
#        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
#        r = self.rpc.do(o)
#
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.redistributions(self.address, 2, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        oo = c.to_redistribution_supply(self.address, r, sender_address=self.accounts[0])
#        rr = self.rpc.do(oo)
#        oo = c.to_redistribution_demurrage_modifier(self.address, r, sender_address=self.accounts[0])
#        rr = self.rpc.do(oo)
#
#        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance(r)


if __name__ == '__main__':
    unittest.main()
