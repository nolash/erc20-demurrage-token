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
from erc20_demurrage_token.unittest.base import TestDemurrageDefault

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)

#TAX_LEVEL = 2

class TestBurn(TestDemurrageDefault):

    def setUp(self):
        super(TestBurn, self).setUp()

#
#    def publish(self, tax_level=None):
#        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
#        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
#
#        if tax_level != None:
#            self.publisher.settings.demurrage_level = tax_level * (10 ** 32)
#        self.publisher.settings.sink_address = self.accounts[9]
#        self.publisher.sink_address = self.accounts[9]
#        super(TestBurn, self).publish(c)


    # Burn tokens and immediately check balances and supply
    def test_burn_basic(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1000000)
        r = self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.burn(self.address, self.accounts[1], 600000)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.add_minter(self.address, self.accounts[0], self.accounts[1])
        r = self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.burn(self.address, self.accounts[1], 600000)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        new_supply = c.parse_total_supply(r)
        self.assertEqual(new_supply, 400000)

        o = c.total_burned(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        burned = c.parse_total_burned(r)
        self.assertEqual(burned, 600000)


    # burn tokens and check sink balance and supply after first redistribution period
    def test_burned_redistribution(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], 1000000000)
        r = self.rpc.do(o)

        (tx_hash, o) = c.burn(self.address, self.accounts[0], 500000000)
        self.rpc.do(o)
        
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.sink_address, 500000000)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds)

        o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bal = c.parse_balance(r)
        self.assert_within(bal, 490000000, 1) # 2% == 10000000

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        new_supply = c.parse_total_supply(r)
        self.assertEqual(new_supply, 500000000)

        o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bal = c.parse_balance(r)
        self.assert_within(bal, 500000000, 1)

        self.backend.time_travel(self.start_time + (self.period_seconds * 2))

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        new_supply = c.parse_total_supply(r)
        self.assertEqual(new_supply, 500000000)

        # if we don't burn anything more it should be the same 
        o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bal = c.parse_balance(r)
        self.assert_within_lower(bal, 500000000, 1)


    # burn tokens and check sink and taxed balance and supply after first redistribution period
    def test_burned_other_redistribution(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[0], 1000000000)
        r = self.rpc.do(o)

        (tx_hash, o) = c.burn(self.address, self.accounts[0], 500000000)
        r = self.rpc.do(o)

        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.accounts[1], 500000000)
        r = self.rpc.do(o)

        self.backend.time_travel(self.start_time + self.period_seconds)

        o = c.balance(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bal = c.parse_balance(r)
        #self.assertEqual(bal, 416873881) # 9 periods demurrage
        self.assert_within(bal, 490000000, 1)

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        new_supply = c.parse_total_supply(r)
        self.assertEqual(new_supply, 500000000)

        o = c.balance(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bal = c.parse_balance(r)
        self.assert_within(bal, 490000000, 1)

        o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        sink_bal = c.parse_balance(r)
        self.assert_within_lower(sink_bal, 10000000, 1) # TODO is this ok variance, 1.0 is ppm?

        self.backend.time_travel(self.start_time + (self.period_seconds * 2))

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        new_supply = c.parse_total_supply(r)
        self.assertEqual(new_supply, 500000000)

        o = c.balance(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        next_bal = c.parse_balance(r)
        self.assert_within(next_bal, 480200000, 0.01)

        o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        prev_sink_bal = sink_bal
        bal = prev_sink_bal + (bal - next_bal)
        sink_bal = c.parse_balance(r)
        self.assert_within_lower(sink_bal, bal, 0.09) # TODO is this ok variance, 1.0 is ppm?


    # verify expected results of balance and supply after multiple redistribution periods
    def test_burn_accumulate(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.add_minter(self.address, self.accounts[0], self.sink_address)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.sink_address, self.default_supply)
        r = self.rpc.do(o)

        balance_share = int(self.default_supply / 2)
        nonce_oracle = RPCNonceOracle(self.sink_address, self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.sink_address, self.accounts[1], balance_share)
        r = self.rpc.do(o)

        new_supply = None
        burn_rate = 1000
        sink_bal = None
        bob_bal = None
        bob_refund = None

        o = c.balance(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bob_bal = c.parse_balance(r)
        prev_bob_bal = bob_bal

        o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        logg.info('sink has balance {}'.format(c.parse_balance(r)))

        iterations = 100

        for i in range(1, iterations + 1):
            nonce_oracle = RPCNonceOracle(self.sink_address, self.rpc)
            c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

            if bob_refund != None:
                (tx_hash, o) = c.transfer(self.address, self.sink_address, self.accounts[1], bob_refund)
                r = self.rpc.do(o)
                o = receipt(tx_hash)
                r = self.rpc.do(o)
                self.assertEqual(r['status'], 1)

            (tx_hash, o) = c.burn(self.address, self.sink_address, burn_rate)
            r = self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)

            nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
            c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
            o = c.total_supply(self.address, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            new_supply = c.parse_total_supply(r)

            self.backend.time_travel(self.start_time + (self.period_seconds * i))

            (tx_hash, o) = c.change_period(self.address, self.accounts[0])
            self.rpc.do(o)
            
            o = c.balance(self.address, self.accounts[1], sender_address=self.accounts[0])
            r = self.rpc.do(o)
            bob_bal = c.parse_balance(r)
            bob_refund = prev_bob_bal - bob_bal

            o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            burner_bal = c.parse_balance(r)

            sum_supply = bob_bal + burner_bal
          
            o = c.total_burned(self.address, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            total_burned = c.parse_balance(r)

            o = c.to_base_amount(self.address, total_burned, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            total_burned_base = c.parse_balance(r)

            expected_supply = self.default_supply - (burn_rate * i)
            logg.info('checking burn round {} balance burner {} bob {} supply {} expected {} summed {} burned {} base {}'.format(i, burner_bal, bob_bal, new_supply, expected_supply, sum_supply, total_burned, total_burned_base))
            self.assertEqual(new_supply, expected_supply)

        sum_supply = burner_bal + bob_bal
        logg.debug('balances sink {} bob {} total {} supply real {} original {}'.format(sink_bal, bob_bal, sum_supply, new_supply, self.default_supply))

        self.assert_within_lower(sum_supply, new_supply, 1)
        self.assert_within_lower(burner_bal, balance_share - total_burned + bob_refund, 1)

        bob_delta = self.default_supply * ((2 / 1000000) / 1000)
        self.assert_within_greater(bob_bal, balance_share - bob_delta - bob_refund, 1)
        
        self.assertEqual(total_burned, iterations * burn_rate)


if __name__ == '__main__':
    unittest.main()
