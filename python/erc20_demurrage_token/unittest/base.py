# standard imports
import logging
import os

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

logg = logging.getLogger(__name__)

#BLOCKTIME = 5 # seconds
TAX_LEVEL = int(10000 * 2) # 2%
# calc "1-(0.98)^(1/518400)" <- 518400 = 30 days of blocks
# 0.00000003897127107225
#PERIOD = int(60/BLOCKTIME) * 60 * 24 * 30 # month
PERIOD = 10


class TestTokenDeploy:

    def __init__(self, rpc, token_symbol='FOO', token_name='Foo Token', sink_address=ZERO_ADDRESS, supply=10**12, tax_level=TAX_LEVEL, period=PERIOD):
        self.tax_level = tax_level
        self.period_seconds = period * 60

        self.settings = DemurrageTokenSettings()
        self.settings.name = token_name
        self.settings.symbol = token_symbol
        self.settings.decimals = 6
        self.settings.demurrage_level = tax_level * (10 ** 32)
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

        self.default_supply = supply
        self.default_supply_cap = int(self.default_supply * 10)


    def deploy(self, rpc, deployer_address, interface, mode, supply_cap=10**12):
        tx_hash = None
        o = None
        logg.debug('mode {} {}'.format(mode, self.settings))
        self.mode = mode
        if mode == 'MultiNocap':
            (tx_hash, o) = interface.constructor(deployer_address, self.settings, redistribute=True, cap=0)
        elif mode == 'SingleNocap':
            (tx_hash, o) = interface.constructor(deployer_address, self.settings, redistribute=False, cap=0)
        elif mode == 'MultiCap':
            (tx_hash, o) = interface.constructor(deployer_address, self.settings, redistribute=True, cap=supply_cap)
        elif mode == 'SingleCap':
            (tx_hash, o) = interface.constructor(deployer_address, self.settings, redistribute=False, cap=supply_cap)
        else:
            raise ValueError('Invalid mode "{}", valid are {}'.format(mode, DemurrageToken.valid_modes))

        r = rpc.do(o)
        o = receipt(tx_hash)
        r = rpc.do(o)
        assert r['status'] == 1
        self.start_block = r['block_number']
        self.address = r['contract_address']

        o = block_by_number(r['block_number'])
        r = rpc.do(o)
        self.start_time = r['timestamp']

        return self.address


class TestDemurrage(EthTesterCase):

    def setUp(self):
        super(TestDemurrage, self).setUp()
#        token_deploy = TestTokenDeploy()
#        self.settings = token_deploy.settings
#        self.sink_address = token_deploy.sink_address
#        self.start_block = token_deploy.start_block
#        self.start_time = token_deploy.start_time
#        self.default_supply = self.default_supply
#        self.default_supply_cap = self.default_supply_cap
        period = PERIOD
        try:
            period = getattr(self, 'period')
        except AttributeError as e:
            pass
        self.deployer = TestTokenDeploy(self.rpc, period=period)
        self.default_supply = self.deployer.default_supply
        self.default_supply_cap = self.deployer.default_supply_cap
        self.start_block = None
        self.address = None
        self.start_time = None


    def deploy(self, interface, mode):
        self.address = self.deployer.deploy(self.rpc, self.accounts[0], interface, mode, supply_cap=self.default_supply_cap)
        self.start_block = self.deployer.start_block
        self.start_time = self.deployer.start_time
        self.tax_level = self.deployer.tax_level
        self.period_seconds = self.deployer.period_seconds
        self.sink_address = self.deployer.sink_address

        logg.debug('contract address {} start block {} start time {}'.format(self.address, self.start_block, self.start_time))


    def assert_within_lower(self, v, target, tolerance_ppm):
        lower_target = target - (target * (tolerance_ppm / 1000000))
        self.assertGreaterEqual(v, lower_target)
        self.assertLessEqual(v, target)
        logg.debug('asserted within lower {} <= {} <= {}'.format(lower_target, v, target))


    def tearDown(self):
        pass


class TestDemurrageDefault(TestDemurrage):

    def setUp(self):
        super(TestDemurrageDefault, self).setUp()
   
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        self.mode = os.environ.get('ERC20_DEMURRAGE_TOKEN_TEST_MODE')
        if self.mode == None:
            self.mode = 'MultiNocap'
        logg.debug('executing test setup default mode {}'.format(self.mode))

        self.deploy(c, self.mode)

        logg.info('deployed with mode {}'.format(self.mode))


class TestDemurrageSingle(TestDemurrage):

    def setUp(self):
        super(TestDemurrageSingle, self).setUp()
   
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        self.mode = os.environ.get('ERC20_DEMURRAGE_TOKEN_TEST_MODE')
        single_valid_modes = [
                    'SingleNocap',
                    'SingleCap',
                    ]
        if self.mode != None:
            if self.mode not in single_valid_modes:
                raise ValueError('Invalid mode "{}" for "single" contract tests, valid are {}'.format(self.mode, single_valid_modes))
        else:
            self.mode = 'SingleNocap'
        logg.debug('executing test setup demurragesingle mode {}'.format(self.mode))

        self.deploy(c, self.mode)

        logg.info('deployed with mode {}'.format(self.mode))


class TestDemurrageCap(TestDemurrage):

    def setUp(self):
        super(TestDemurrageCap, self).setUp()
   
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        self.mode = os.environ.get('ERC20_DEMURRAGE_TOKEN_TEST_MODE')
        cap_valid_modes = [
                    'MultiCap',
                    'SingleCap',
                    ]
        if self.mode != None:
            if self.mode not in cap_valid_modes:
                raise ValueError('Invalid mode "{}" for "cap" contract tests, valid are {}'.format(self.mode, cap_valid_modes))
        else:
            self.mode = 'MultiCap'
        logg.debug('executing test setup demurragecap mode {}'.format(self.mode))

        self.deploy(c, self.mode)

        logg.info('deployed with mode {}'.format(self.mode))



class TestDemurrageUnit(TestDemurrage):

    def setUp(self):
        self.period = 1
        self.period_seconds = self.period * 60
        self.tax_level = TAX_LEVEL

        super(TestDemurrageUnit, self).setUp()

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        self.settings = DemurrageTokenSettings()
        self.settings.name = 'Foo Token'
        self.settings.symbol = 'FOO'
        self.settings.decimals = 6
        self.settings.demurrage_level = self.tax_level * (10 ** 32)
        self.settings.period_minutes = int(self.period_seconds/60)
        self.settings.sink_address = self.accounts[9]
        self.sink_address = self.settings.sink_address

        o = block_latest()
        self.start_block = self.rpc.do(o)
        
        o = block_by_number(self.start_block, include_tx=False)
        r = self.rpc.do(o)

        try:
            self.start_time = int(r['timestamp'], 16)
        except TypeError:
            self.start_time = int(r['timestamp'])

        self.default_supply = 1000000000000
        self.default_supply_cap = int(self.default_supply * 10)

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)

        self.mode = os.environ.get('ERC20_DEMURRAGE_TOKEN_TEST_MODE')
        unit_valid_modes = [
                    'SingleNocap',
                    'SingleCap',
                    ]
        if self.mode != None:
            if self.mode not in unit_valid_modes:
                raise ValueError('Invalid mode "{}" for "unit" contract tests, valid are {}'.format(self.mode, unit_valid_modes))
        else:
            self.mode = 'SingleNocap'
        logg.debug('executing test setup unit mode {}'.format(self.mode))

        self.deploy(c, self.mode)

        logg.info('deployed with mode {}'.format(self.mode))
