# standard imports
import datetime
import unittest
import logging
import os

# external imports
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt

# local imports
from erc20_demurrage_token import DemurrageToken
from erc20_demurrage_token.demurrage import DemurrageCalculator

# test imports
from erc20_demurrage_token.unittest.base import TestDemurrage

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()


class TestDemurragePeriods(TestDemurrage):

    def setUp(self):
        super(TestDemurragePeriods, self).setUp()
   
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        self.mode = os.environ.get('ERC20_DEMURRAGE_TOKEN_TEST_MODE')
        if self.mode == None:
            self.mode = 'MultiNocap'
        logg.debug('executing test setup default mode {}'.format(self.mode))

        self.deployer.settings.sink_address = self.accounts[9]
        self.deployer.sink_address = self.accounts[9]
        self.deploy(c, self.mode)

        logg.info('deployed with mode {}'.format(self.mode))


    def test_overtime(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], self.default_supply)
        r = self.rpc.do(o)

        o = c.balance(self.address, self.accounts[1], sender_address=self.accounts[0])
        r = self.rpc.do(o)
        bob_bal = c.parse_balance(r)
        prev_bob_bal = bob_bal

        nonce_oracle = RPCNonceOracle(self.sink_address, self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        for i in range(1, 1001):
            self.backend.time_travel(self.start_time + (self.period_seconds * i))

            (tx_hash, o) = c.transfer(self.address, self.sink_address, self.accounts[1], prev_bob_bal - bob_bal)
            r = self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)

            (tx_hash, o) = c.change_period(self.address, self.sink_address)
            self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)

            o = c.balance(self.address, self.accounts[1], sender_address=self.accounts[0])
            r = self.rpc.do(o)
            bob_bal = c.parse_balance(r)

            o = c.balance(self.address, self.sink_address, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            sink_bal = c.parse_balance(r)

            o = c.total_supply(self.address, sender_address=self.accounts[0])
            r = self.rpc.do(o)
            new_supply = c.parse_total_supply(r)

            logg.info('round {} supply {} balance sink {} bob {}'.format(i, new_supply, sink_bal, bob_bal))


if __name__ == '__main__':
    unittest.main()
