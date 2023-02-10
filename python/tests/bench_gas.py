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
from erc20_demurrage_token.unittest import TestDemurrageDefault

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()

testdir = os.path.dirname(__file__)



class BenchBasic(TestDemurrageDefault):

    def setUp(self):
        super(BenchBasic, self).setUp()
        self.bench = {
    'mint': None,
    'transfer_light': None,
    'transfer_heavy': None,
    'approve': None,
    'transfer_from': None,
    'period_light': None,
    'period_heavy': None,
    'period_catchup': None,
    'demurrage': None,
        }


    def test_bench_min(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[1], 1024)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.bench['mint'] = r['gas_used']
        
        nonce_oracle = RPCNonceOracle(self.accounts[1], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[1], self.accounts[2], 512)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.bench['transfer_light'] = r['gas_used']

        (tx_hash, o) = c.approve(self.address, self.accounts[1], self.accounts[0], 512)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.bench['approve'] = r['gas_used']

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer_from(self.address, self.accounts[0], self.accounts[1], self.accounts[3], 256)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.bench['transfer_from'] = r['gas_used']

        z = 0
        for i in range(100):
            self.backend.time_travel(self.start_time + int(self.period_seconds / 2) + (10 * (i * (i + 1))))
            (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
            r = self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)
            z += r['gas_used']
            logg.info('demurrage round {} gas {}'.format(i, r['gas_used']))
        z /= 100
        self.bench['demurrage'] = int(z)

        z = 0
        for i in range(100):
            self.backend.time_travel(self.start_time + (self.period_seconds * (i + 1)))
            (tx_hash, o) = c.change_period(self.address, self.accounts[0])
            r = self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)
            z += r['gas_used']
            logg.info('period with demurrage round {} gas {}'.format(i, r['gas_used']))

        z /= 100
        self.bench['period_heavy'] = int(z)

        z = 0
        for i in range(100):
            self.backend.time_travel(self.start_time + (self.period_seconds * ((i + 101))))
            (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
            r = self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)

            (tx_hash, o) = c.change_period(self.address, self.accounts[0])
            r = self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)
            z += r['gas_used']
            logg.info('period without demurrage round {} gas {}'.format(i, r['gas_used']))

        z /= 100
        self.bench['period_light'] = int(z)

        z = 0
        self.backend.time_travel(self.start_time + (self.period_seconds * 401))
        for i in range(100):
            (tx_hash, o) = c.change_period(self.address, self.accounts[0])
            r = self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            self.assertEqual(r['status'], 1)
            z += r['gas_used']
            logg.info('period catchup round {} gas {}'.format(i, r['gas_used']))

        z /= 100
        self.bench['period_catchup'] = int(z)

        self.backend.time_travel(self.start_time + (self.period_seconds * 501))
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.accounts[2], 1024)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.backend.time_travel(self.start_time + (self.period_seconds * 502))

        nonce_oracle = RPCNonceOracle(self.accounts[2], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[2], self.accounts[4], 1)
        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.bench['transfer_heavy'] = r['gas_used']

        print(json.dumps(self.bench))





if __name__ == '__main__':
    unittest.main()
