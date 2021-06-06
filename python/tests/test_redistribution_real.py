# standard imports
import os
import unittest
import json
import logging

# external imports
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt

# local imports
from erc20_demurrage_token import DemurrageToken

# test imports
from tests.base import TestDemurrageReal

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)


class TestRedistribution(TestDemurrageReal):

    def test_simple_example(self):
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

        (tx_hash, o) = c.change_period(self.address, self.accounts[1])
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.redistributions(self.address, 1, sender_address=self.accounts[0])
        redistribution = self.rpc.do(o)
        logg.debug('redistribution {}'.format(redistribution))

        o = c.to_redistribution_period(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        period = c.parse_to_redistribution_item(r)
        logg.debug('period {}'.format(period))

        o = c.to_redistribution_participants(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        participants = c.parse_to_redistribution_item(r)
        logg.debug('participants {}'.format(participants))

        o = c.to_redistribution_supply(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        supply = c.parse_to_redistribution_item(r)
        logg.debug('supply {}'.format(supply))

        o = c.to_redistribution_demurrage_modifier(self.address, redistribution, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        modifier = c.parse_to_redistribution_item(r)
        logg.debug('modifier {}'.format(modifier))



if __name__ == '__main__':
    unittest.main()
