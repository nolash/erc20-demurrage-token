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

        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('toRedistributionDemurrageModifier')
        enc.typ(ABIContractType.BYTES32)
        enc.bytes32(redistribution)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o




    def test_whole_is_parts(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 100000000)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[2], 100000000)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        
        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], self.accounts[3], 50000000)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        self.backend.time_travel(self.start_time + self.period_seconds + 1)
        
        o = block_latest()
        r = self.rpc.do(o)
        o = block_by_number(r)
        r = self.rpc.do(o)
        self.assertEqual(r['timestamp'], self.start_time + self.period_seconds)

        (tx_hash, o) = c.change_period(self.address, self.accounts[1])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.apply_redistribution_on_account(self.address, self.accounts[1], self.accounts[1])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        balance = 0
        for i in range(3):
            o = c.balance_of(self.address, self.accounts[i+1], sender_address=self.accounts[0])
            r = self.rpc.do(o)
            balance_item = c.parse_balance_of(r)
            balance += balance_item
            logg.debug('balance {} {} total {}'.format(i, balance_item, balance))

        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance_item = c.parse_balance_of(r)
        balance += balance_item

        self.assertEqual(balance, 200000000)
    

#    def test_debug_periods(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        o = c.actual_period(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        pactual = c.parse_actual_period(r)
#
#        o = c.period_start(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        pstart = c.parse_actual_period(r)
#
#        o = c.period_duration(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        pduration = c.parse_actual_period(r)
#
#        o = block_latest()
#        blocknumber = self.rpc.do(o)
#
#        logg.debug('actual {} start {} duration {} blocknumber {}'.format(pactual, pstart, pduration, blocknumber))
#
#
#    # TODO: check receipt log outputs
#    def test_redistribution_storage(self):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        self.assertEqual(strip_0x(r), '000000000000000000000000f424000000000000000000000000000000000001')
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1000000)
#        r = self.rpc.do(o)
#
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[2], 1000000)
#        r = self.rpc.do(o)
#
#        external_address = to_checksum_address('0x' + os.urandom(20).hex())
#
#        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[2], external_address, 1000000)
#        r = self.rpc.do(o)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[1], external_address, 999999)
#        r = self.rpc.do(o)
#
#        self.backend.time_travel(self.start_time + self.period_seconds + 1)
#
#        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        self.assertEqual(strip_0x(r), '000000000000000000000000f42400000000010000000000001e848000000001')
#
#        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        self.assertEqual(strip_0x(r), '000000000000000000000000f42400000000010000000000001e848000000001')
#
#
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], 1000000)
#        r = self.rpc.do(o)
#
#        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        self.assertEqual(strip_0x(r), '000000000000000000000000ef4200000000000000000000002dc6c000000002')
#
#
#    def test_redistribution_balance_on_zero_participants(self):
#        supply = self.default_supply
#
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], supply)
#        r = self.rpc.do(o)
#
#        self.backend.time_travel(self.start_time + self.period_seconds + 1)
#        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        rcpt = self.rpc.do(o)
#        self.assertEqual(rcpt['status'], 1)
#
#        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.total_supply(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        total_supply = c.parse_total_supply(r)
#        sink_increment = int(total_supply * (self.tax_level / 1000000))
#        self.assertEqual(supply, total_supply)
#
#        for l in rcpt['logs']:
#            if l['topics'][0] == '0xa0717e54e02bd9829db5e6e998aec0ae9de796b8d150a3cc46a92ab869697755': # event Decayed(uint256,uint256,uint256,uint256)
#                period = int.from_bytes(bytes.fromhex(strip_0x(l['topics'][1])), 'big')
#                self.assertEqual(period, 2)
#                b = bytes.fromhex(strip_0x(l['data']))
#                remainder = int.from_bytes(b, 'big')
#                self.assertEqual(remainder, int((1000000 - self.tax_level) * (10 ** 32)))
#
#        o = c.balance_of(self.address, self.sink_address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        sink_balance = c.parse_balance_of(r)
#
#        self.assertEqual(sink_balance, int(sink_increment * 0.98))
#        self.assertEqual(sink_balance, int(sink_increment * (1000000 - self.tax_level) / 1000000))
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        balance = c.parse_balance_of(r)
#        self.assertEqual(balance, supply - sink_increment)
#
#
#    def test_redistribution_two_of_ten(self):
#        mint_amount = 100000000
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        z = 0
#        for i in range(10):
#            (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[i], mint_amount)
#            self.rpc.do(o)
#            z += mint_amount
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        initial_balance = c.parse_balance_of(r)
#
#        spend_amount = 1000000
#        external_address = to_checksum_address('0x' + os.urandom(20).hex())
#
#        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[1], external_address, spend_amount)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[2], external_address, spend_amount)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        # No cheating!
#        nonce_oracle = RPCNonceOracle(self.accounts[3], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[3], self.accounts[3], spend_amount)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        # No cheapskating!
#        nonce_oracle = RPCNonceOracle(self.accounts[4], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#        (tx_hash, o) = c.transfer(self.address, self.accounts[4], external_address, spend_amount-1)
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#
#        self.backend.time_travel(self.start_time + self.period_seconds + 1)
#
#        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[4])
#        self.rpc.do(o)
#
#        (tx_hash, o) = c.change_period(self.address, self.accounts[4])
#        self.rpc.do(o)
#
#        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        bummer_balance = c.parse_balance_of(r)
#
#        self.assertEqual(bummer_balance, mint_amount - (mint_amount * (self.tax_level / 1000000)))
#        logg.debug('bal {} '.format(bummer_balance))
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        bummer_balance = c.parse_balance_of(r)
#        spender_balance = mint_amount - spend_amount
#        spender_decayed_balance = int(spender_balance - (spender_balance * (self.tax_level / 1000000)))
#        self.assertEqual(bummer_balance, spender_decayed_balance)
#        logg.debug('bal {} '.format(bummer_balance))
#
#        (tx_hash, o) = c.apply_redistribution_on_account(self.address, self.accounts[4], self.accounts[1])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        (tx_hash, o) = c.apply_redistribution_on_account(self.address, self.accounts[4], self.accounts[2])
#        self.rpc.do(o)
#        o = receipt(tx_hash)
#        r = self.rpc.do(o)
#        self.assertEqual(r['status'], 1)
#
#        o = c.redistributions(self.address, 0, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        redistribution_data = c.parse_redistributions(r)
#        logg.debug('redist data {}'.format(redistribution_data))
#
#        o = c.account_period(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        account_period_data = c.parse_account_period(r)
#        logg.debug('account period {}'.format(account_period_data))
#
#        o = c.actual_period(self.address, sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        actual_period = c.parse_actual_period(r)
#        logg.debug('period {}'.format(actual_period))
#
#        redistribution = int((z / 2) * (self.tax_level / 1000000))
#        spender_new_base_balance = ((mint_amount - spend_amount) + redistribution)
#        spender_new_decayed_balance = int(spender_new_base_balance - (spender_new_base_balance * (self.tax_level / 1000000)))
#
#        o = c.balance_of(self.address, self.accounts[1], sender_address=self.accounts[0])
#        r = self.rpc.do(o)
#        spender_actual_balance = c.parse_balance_of(r)
#        logg.debug('rrr {} {}'.format(redistribution, spender_new_decayed_balance))
#
#        self.assertEqual(spender_actual_balance, spender_new_decayed_balance)
#

if __name__ == '__main__':
    unittest.main()
