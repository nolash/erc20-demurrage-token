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
from tests.base import TestDemurrageUnit

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestRedistribution(TestDemurrageUnit):

    # TODO: move to "pure" test file when getdistribution is implemented in all contracts
    def test_distribution(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        demurrage = (1 - (self.tax_level / 1000000)) * (10**38)
        supply = self.default_supply

        o = c.get_distribution(self.address, supply, demurrage, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        distribution = c.parse_get_distribution(r)
        expected_distribution = self.default_supply * (self.tax_level / 1000000)
        self.assertEqual(distribution, expected_distribution)


    def test_distribution_from_redistribution(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        demurrage = (1 - (self.tax_level / 1000000)) * (10**38)
        supply = self.default_supply

        o = c.to_redistribution(self.address, 0, demurrage, supply, 1, sender_address=self.accounts[0])
        redistribution = self.rpc.do(o)

        o = c.get_distribution_from_redistribution(self.address, redistribution, self.accounts[0])
        r = self.rpc.do(o)
        distribution = c.parse_get_distribution(r)
        expected_distribution = self.default_supply * (self.tax_level / 1000000)
        self.assertEqual(distribution, expected_distribution)



#    def test_single_step(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        mint_amount = 100000000
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], mint_amount)
#        self.rpc.do(o)
#
#        self.backend.time_travel(self.start_time + self.period_seconds)
#
#        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
#        self.rpc.do(o)
#
#        expected_balance = int(mint_amount - ((self.tax_level / 1000000) * mint_amount))
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#
#        self.assertEqual(balance, expected_balance)
#
#
#    def test_single_step_multi(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        mint_amount = 100000000
#
#        for i in range(3):
#            (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[i+1], mint_amount)
#            self.rpc.do(o)
#    
#        self.backend.time_travel(self.start_time + self.period_seconds)
#
#        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
#        self.rpc.do(o)
#
#        expected_balance = int(mint_amount - ((self.tax_level / 1000000) * mint_amount))
#
#        for i in range(3):
#            o = c.balance_of(self.address, self.accounts[i+1], sender_address=self.accounts[0])
#            r = self.rpc.do(o)
#            balance = c.parse_balance_of(r)
#            self.assertEqual(balance, expected_balance)
#
#
    def test_single_step_transfer(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        mint_amount = 100000000
        half_mint_amount = int(mint_amount / 2)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], mint_amount)
        self.rpc.do(o)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[2], mint_amount)
        self.rpc.do(o)
    
        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], self.accounts[3], half_mint_amount)
        self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds)

        (tx_hash, o) = c.change_period(self.address, self.accounts[1])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        demurrage_amount = int((self.tax_level / 1000000) * mint_amount)

        expected_balance = mint_amount - demurrage_amount
        o = c.balance_of(self.address, self.accounts[2], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, expected_balance)

        half_demurrage_amount = int((self.tax_level / 1000000) * half_mint_amount)

        expected_balance = half_mint_amount - half_demurrage_amount
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, expected_balance)

        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, expected_balance)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        supply = c.parse_total_supply(r)

        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
        redistribution = self.rpc.do(o)
        o = c.to_redistribution_supply(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        supply = c.parse_to_redistribution_item(r)
        o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        demurrage = c.parse_to_redistribution_item(r)
#        o = c.demurrage_amount(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        demurrage = c.parse_demurrage_amount(r)
        logg.debug('\nrediistribution {}\ndemurrage {}\nsupply {}'.format(redistribution, demurrage, supply))

        expected_balance = int(supply * (self.tax_level / 1000000))
        expected_balance_tolerance = 1

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertGreaterEqual(balance, expected_balance - expected_balance_tolerance)
        self.assertLessEqual(balance, expected_balance)


if __name__ == '__main__':
    unittest.main()
