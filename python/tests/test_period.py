# standard imports
import os
import unittest
import json
import logging

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import (
        receipt,
        TxFactory,
        TxFormat,
        )
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        )

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from erc20_demurrage_token.unittest.base import TestDemurrageDefault

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)

class TestPeriod(TestDemurrageDefault):

    def test_period(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        self.backend.time_travel(self.start_time + self.period_seconds)

        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        redistribution = c.parse_redistributions(r)

        o = c.to_redistribution_period(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        period = c.parse_to_redistribution_period(r)
        self.assertEqual(2, period)

        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        redistribution = c.parse_redistributions(r)

        o = c.to_redistribution_period(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        period = c.parse_to_redistribution_period(r)
        self.assertEqual(2, period)

        o = c.actual_period(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        period = c.parse_actual_period(r)
        self.assertEqual(2, period)

        o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        period = c.parse_to_redistribution_item(r)

        # allow test code float rounding error to billionth
        modifier = (1 - (self.tax_level / 1000000)) ** (self.period_seconds / 60)
        modifier *= 10 ** 9 
        modifier = int(modifier) * (10 ** (28 - 9))

        period /= (10 ** (28 - 9))
        period = int(period) * (10 ** (28 - 9))
        self.assertEqual(modifier, period)

        self.backend.time_travel(self.start_time + self.period_seconds * 2)

        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.redistributions(self.address, 2, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        redistribution = c.parse_redistributions(r)

        o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        period = c.parse_to_redistribution_item(r)

        # allow test code float rounding error to billionth
        modifier = (1 - (self.tax_level / 1000000)) ** ((self.period_seconds * 2) / 60)
        modifier *= 10 ** 9 
        modifier = int(modifier) * (10 ** (28 - 9))

        period /= (10 ** (28 - 9))
        period = int(period) * (10 ** (28 - 9))
        self.assertEqual(modifier, period)


    def test_change_sink(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        o = c.balance_of(self.address, ZERO_ADDRESS, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 0)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 102400000000)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        self.backend.time_travel(self.start_time + self.period_seconds + 1)

        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.balance_of(self.address, ZERO_ADDRESS, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertGreater(balance, 0)
        old_sink_balance = balance

        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertEqual(balance, 0)

        nonce_oracle = RPCNonceOracle(self.accounts[5], self.rpc)
        c = TxFactory(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        enc = ABIContractEncoder()
        enc.method('setSinkAddress')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(self.accounts[3])
        data = enc.get()
        o = c.template(self.accounts[5], self.address, use_nonce=True)
        o = c.set_code(o, data)
        (tx_hash, o) = c.finalize(o, TxFormat.JSONRPC)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = TxFactory(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        enc = ABIContractEncoder()
        enc.method('setSinkAddress')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(self.accounts[3])
        data = enc.get()
        o = c.template(self.accounts[0], self.address, use_nonce=True)
        o = c.set_code(o, data)
        (tx_hash, o) = c.finalize(o, TxFormat.JSONRPC)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        self.backend.time_travel(self.start_time + (self.period_seconds * 2) + 1)

        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.balance_of(self.address, ZERO_ADDRESS, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertLess(balance, old_sink_balance)

        o = c.balance_of(self.address, self.accounts[3], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = c.parse_balance_of(r)
        self.assertGreater(balance, 0)


if __name__ == '__main__':
    unittest.main()
