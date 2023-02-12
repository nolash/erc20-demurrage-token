# standard imports
import logging
import os
import math

# external imports
from chainlib.eth.unittest.ethtester import EthTesterCase
from chainlib.eth.tx import (
        receipt,
        )
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.constant import ZERO_ADDRESS

# local imports
from erc20_demurrage_token import (
        DemurrageTokenSettings,
        DemurrageToken,
        )
from dexif import *

logg = logging.getLogger()

#BLOCKTIME = 5 # seconds
TAX_LEVEL = int(10000 * 2) # 2%
# calc "1-(0.98)^(1/518400)" <- 518400 = 30 days of blocks
# 0.00000003897127107225
PERIOD = 43200


class TestTokenDeploy:

    """tax level is ppm, 1000000 = 100%"""
    def __init__(self, rpc, token_symbol='FOO', token_name='Foo Token', sink_address=ZERO_ADDRESS, tax_level=TAX_LEVEL, period=PERIOD):
        self.tax_level = tax_level
        self.period_seconds = period * 60

        self.settings = DemurrageTokenSettings()
        self.settings.name = token_name
        self.settings.symbol = token_symbol
        self.settings.decimals = 6
        tax_level_input = to_fixed((1 - (tax_level / 1000000)) ** (1 / period))
        self.settings.demurrage_level = tax_level_input
        self.settings.period_minutes = period
        self.settings.sink_address = sink_address
        self.sink_address = self.settings.sink_address
        logg.debug('using demurrage token settings: {}'.format(self.settings))

        o = block_latest()
        self.start_block = rpc.do(o)
        
        o = block_by_number(self.start_block, include_tx=False)
        r = rpc.do(o)

        try:
            self.start_time = int(r['timestamp'], 16)
        except TypeError:
            self.start_time = int(r['timestamp'])


    def deploy(self, rpc, deployer_address, interface, supply_cap=0):
        tx_hash = None
        o = None
        (tx_hash, o) = interface.constructor(deployer_address, self.settings)

        r = rpc.do(o)
        o = receipt(tx_hash)
        r = rpc.do(o)
        assert r['status'] == 1
        self.start_block = r['block_number']
        self.address = r['contract_address']

        o = block_by_number(r['block_number'])
        r = rpc.do(o)
        self.start_time = r['timestamp']

        (tx_hash, o) = interface.add_writer(self.address, deployer_address, deployer_address)
        r = rpc.do(o)
        o = receipt(tx_hash)
        r = rpc.do(o)
        assert r['status'] == 1

        return self.address


class TestDemurrage(EthTesterCase):

    def setUp(self):
        super(TestDemurrage, self).setUp()
        period = PERIOD
        try:
            period = getattr(self, 'period')
        except AttributeError as e:
            pass
        self.deployer = TestTokenDeploy(self.rpc, period=period, sink_address=self.accounts[9])
        self.default_supply = 0
        self.default_supply_cap = 0
        self.start_block = None
        self.address = None
        self.start_time = None


    def deploy(self, interface):
        self.address = self.deployer.deploy(self.rpc, self.accounts[0], interface, supply_cap=self.default_supply_cap)
        self.start_block = self.deployer.start_block
        self.start_time = self.deployer.start_time
        self.tax_level = self.deployer.tax_level
        self.period_seconds = self.deployer.period_seconds
        self.sink_address = self.deployer.sink_address

        logg.debug('contract address {} start block {} start time {}'.format(self.address, self.start_block, self.start_time))


    def assert_within(self, v, target, tolerance_ppm):
        lower_target = target - (target * (tolerance_ppm / 1000000))
        higher_target = target + (target * (tolerance_ppm / 1000000))
        #self.assertGreaterEqual(v, lower_target)
        #self.assertLessEqual(v, higher_target)
        if v >= lower_target and v <= higher_target:
            logg.debug('asserted within {} <= {} <= {}'.format(lower_target, v, higher_target))
            return
        raise AssertionError('{} not within lower {} and higher {}'.format(v, lower_target, higher_target))


    def assert_within_lower(self, v, target, tolerance_ppm):
        lower_target = target - (target * (tolerance_ppm / 1000000))
        self.assertGreaterEqual(v, lower_target)
        self.assertLessEqual(v, target)
        logg.debug('asserted within lower {} <= {} <= {}'.format(lower_target, v, target))


    def assert_equal_decimals(self, v, target, precision):
        target = int(target * (10 ** precision))
        target = target / (10 ** precision)
        self.assertEqual(v, target)


    def tearDown(self):
        pass


class TestDemurrageDefault(TestDemurrage):

    def setUp(self):
        super(TestDemurrageDefault, self).setUp()
   
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        self.deploy(c)

        self.default_supply = 10**12
        self.default_supply_cap = self.default_supply
