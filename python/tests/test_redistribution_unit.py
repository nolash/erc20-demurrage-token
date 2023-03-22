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
from dexif import to_fixed

# local imports
from erc20_demurrage_token import DemurrageToken
from erc20_demurrage_token import DemurrageRedistribution

# test imports
from erc20_demurrage_token.unittest import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestRedistribution(TestDemurrageDefault):



    # TODO: move to "pure" test file when getdistribution is implemented in all contracts
    def test_distribution_direct(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        demurrage = (1 - (self.tax_level / 1000000)) * (10**28)
        supply = self.default_supply

        #o = c.get_distribution(self.address, supply, demurrage, sender_address=self.accounts[0])
        o = c.get_distribution(self.address, supply, to_fixed(self.tax_level / 1000000), sender_address=self.accounts[0])
        r = self.rpc.do(o)
        distribution = c.parse_get_distribution(r)
        expected_distribution = self.default_supply * (self.tax_level / 1000000)
        self.assert_within(distribution, expected_distribution, 100)


    def test_distribution_from_redistribution(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        demurrage = (1 - (self.tax_level / 100000)) * (10**28)

        supply = self.default_supply

        o = c.to_redistribution(self.address, 0, to_fixed(self.tax_level / 1000000), supply, 2, sender_address=self.accounts[0])
        redistribution = self.rpc.do(o)

        o = c.get_distribution_from_redistribution(self.address, redistribution, self.accounts[0])
        r = self.rpc.do(o)
        distribution = c.parse_get_distribution(r)
        expected_distribution = (self.default_supply * (self.tax_level / 1000000))
        logg.debug('distribution {} supply {}'.format(distribution, self.default_supply))
        self.assert_within(distribution, expected_distribution, 1000)


    def test_single_step_basic(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        mint_amount = 100000000

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], mint_amount)
        self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds)

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        self.rpc.do(o)

        expected_balance = int(mint_amount - ((self.tax_level / 1000000) * mint_amount))

        o = c.balance_of(self.address, ZERO_ADDRESS, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)

        logg.debug('balance {}'.format(balance))

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)

        self.assertEqual(balance, expected_balance)


    def test_single_step_multi(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        mint_amount = 100000000

        for i in range(3):
            (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[i+1], mint_amount)
            self.rpc.do(o)
    
        self.backend.time_travel(self.start_time + self.period_seconds)

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        self.rpc.do(o)

        expected_balance = int(mint_amount - ((self.tax_level / 1000000) * mint_amount))

        for i in range(3):
            o = c.balance_of(self.address, self.accounts[i+1], sender_address=self.accounts[0])
            r = self.rpc.do(o)
            balance = c.parse_balance(r)
            self.assertEqual(balance, expected_balance)


    def test_single_step_transfer(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        mint_amount = self.default_supply
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

        # check that we have crossed into new period, this will throw if not
        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
        self.rpc.do(o)

        demurrage_amount = int((self.tax_level / 1000000) * mint_amount)

        expected_balance = mint_amount - demurrage_amount
        o = c.balance_of(self.address, self.accounts[2], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assert_within(balance, expected_balance, 10)

        half_demurrage_amount = int((self.tax_level / 1000000) * half_mint_amount)

        expected_balance = half_mint_amount - half_demurrage_amount
        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assertEqual(balance, expected_balance)

        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
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
        #demurrage = c.parse_to_redistribution_item(r)
        #logg.debug('\nrediistribution {}\ndemurrage {}\nsupply {}'.format(redistribution, demurrage, supply))
        redistro_item = DemurrageRedistribution(redistribution)
        logg.debug('redistribution {}'.format(redistro_item))

        expected_balance = int(supply * (self.tax_level / 1000000))
        expected_balance_tolerance = 1

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance(r)
        self.assert_within_lower(balance, expected_balance, 1000)


if __name__ == '__main__':
    unittest.main()
