# standard imports
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

#BLOCKTIME = 5 # seconds
TAX_LEVEL = 10000 * 2 # 2%
#PERIOD = int(60/BLOCKTIME) * 60 * 24 * 30 # month
PERIOD = 1


class TestRedistribution(TestDemurrageDefault):

    @unittest.skip('foo')
    def test_debug_periods(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        o = c.actual_period(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        pactual = c.parse_actual_period(r)

        o = c.period_start(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        pstart = c.parse_actual_period(r)

        o = c.period_duration(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        pduration = c.parse_actual_period(r)

        o = block_latest()
        blocknumber = self.rpc.do(o)

        logg.debug('actual {} start {} duration {} blocknumber {}'.format(pactual, pstart, pduration, blocknumber))


    # TODO: check receipt log outputs
    @unittest.skip('foo')
    def test_redistribution_storage(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertEqual(strip_0x(r), '000000000000000000000000f424000000000000000000000000000000000001')

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1000000)
        r = self.rpc.do(o)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[2], 1000000)
        r = self.rpc.do(o)

        external_address = to_checksum_address('0x' + os.urandom(20).hex())

        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[2], external_address, 1000000)
        r = self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], external_address, 999999)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + 61)

        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertEqual(strip_0x(r), '000000000000000000000000f42400000000010000000000001e848000000001')

        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertEqual(strip_0x(r), '000000000000000000000000f42400000000010000000000001e848000000001')


        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], 1000000)
        r = self.rpc.do(o)

        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertEqual(strip_0x(r), '000000000000000000000000ef4200000000000000000000002dc6c000000002')


    @unittest.skip('foo')
    def test_redistribution_balance_on_zero_participants(self):
        supply = 1000000000000

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], supply)
        r = self.rpc.do(o)


        self.backend.time_travel(self.start_time + 61)
        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        self.rpc.do(o)
        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        self.rpc.do(o)

        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        redistributions = c.parse_redistributions(r)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        supply = c.parse_total_supply(r)

        sink_increment = int(supply * (TAX_LEVEL / 1000000))
#        for l in r['logs']:
#            if l.topics[0].hex() == '0xa0717e54e02bd9829db5e6e998aec0ae9de796b8d150a3cc46a92ab869697755': # event Decayed(uint256,uint256,uint256,uint256)
#                period = int.from_bytes(l.topics[1], 'big')
#                self.assertEqual(period, 2)
#                b = bytes.fromhex(l.data[2:])
#                remainder = int.from_bytes(b, 'big')
#                self.assertEqual(remainder, int((1000000 - TAX_LEVEL) * (10 ** 32)))
#                logg.debug('period {} remainder {}'.format(period, remainder))
#
#        sink_balance = self.contract.functions.balanceOf(self.sink_address).call()
#        logg.debug('{} {}'.format(sink_increment, sink_balance))
#        self.assertEqual(sink_balance, int(sink_increment * 0.98))
#        self.assertEqual(sink_balance, int(sink_increment * (1000000 - TAX_LEVEL) / 1000000))
#
#        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
#        self.assertEqual(balance, supply - sink_increment)
#

    def test_redistribution_two_of_ten(self):
        mint_amount = 100000000
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        z = 0
        for i in range(10):
            (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[i], mint_amount)
            self.rpc.do(o)
            z += mint_amount

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        initial_balance = c.parse_balance_of(r)

        spend_amount = 1000000
        external_address = to_checksum_address('0x' + os.urandom(20).hex())

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], external_address, spend_amount)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[2], external_address, spend_amount)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        # No cheating!
        nonce_oracle = RPCNonceOracle(self.accounts[3], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[3], self.accounts[3], spend_amount)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        # No cheapskating!
        nonce_oracle = RPCNonceOracle(self.accounts[4], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[4], external_address, spend_amount-1)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)


        self.backend.time_travel(self.start_time + 61)

        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[4])
        self.rpc.do(o)

        (tx_hash, o) = c.change_period(self.address, self.accounts[4])
        self.rpc.do(o)

        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bummer_balance = c.parse_balance_of(r)

        self.assertEqual(bummer_balance, mint_amount - (mint_amount * (TAX_LEVEL / 1000000)))
        logg.debug('bal {} '.format(bummer_balance))

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bummer_balance = c.parse_balance_of(r)
        spender_balance = mint_amount - spend_amount
        spender_decayed_balance = int(spender_balance - (spender_balance * (TAX_LEVEL / 1000000)))
        self.assertEqual(bummer_balance, spender_decayed_balance)
        logg.debug('bal {} '.format(bummer_balance))

        (tx_hash, o) = c.apply_redistribution_on_account(self.address, self.accounts[4], self.accounts[1])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

#        logg.debug('log {}'.format(r.logs))
        (tx_hash, o) = c.apply_redistribution_on_account(self.address, self.accounts[4], self.accounts[2])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        redistribution_data = c.parse_redistributions(r)
        logg.debug('redist data {}'.format(redistribution_data))

        o = c.account_period(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        account_period_data = c.parse_account_period(r)
        logg.debug('account period {}'.format(account_period_data))

        o = c.actual_period(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        actual_period = c.parse_actual_period(r)
        logg.debug('period {}'.format(actual_period))

        redistribution = int((z / 2) * (TAX_LEVEL / 1000000))
        spender_new_base_balance = ((mint_amount - spend_amount) + redistribution)
        spender_new_decayed_balance = int(spender_new_base_balance - (spender_new_base_balance * (TAX_LEVEL / 1000000)))

        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        spender_actual_balance = c.parse_balance_of(r)
        logg.debug('rrr {} {}'.format(redistribution, spender_new_decayed_balance))

        self.assertEqual(spender_actual_balance, spender_new_decayed_balance)


if __name__ == '__main__':
    unittest.main()

 
