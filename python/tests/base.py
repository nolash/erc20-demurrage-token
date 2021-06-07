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

# local imports
from erc20_demurrage_token import (
        DemurrageTokenSettings,
        DemurrageToken,
        )


logg = logging.getLogger()


#BLOCKTIME = 5 # seconds
TAX_LEVEL = int(10000 * 2) # 2%
# calc "1-(0.98)^(1/518400)" <- 518400 = 30 days of blocks
# 0.00000003897127107225
#PERIOD = int(60/BLOCKTIME) * 60 * 24 * 30 # month
PERIOD = 10


class TestDemurrage(EthTesterCase):

    def setUp(self):
        super(TestDemurrage, self).setUp()

        self.tax_level = TAX_LEVEL
        self.period_seconds = PERIOD * 60

        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        self.settings = DemurrageTokenSettings()
        self.settings.name = 'Foo Token'
        self.settings.symbol = 'FOO'
        self.settings.decimals = 6
        self.settings.demurrage_level = TAX_LEVEL * (10 ** 32)
        self.settings.period_minutes = PERIOD
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


    def deploy(self, interface, mode):
        tx_hash = None
        o = None
        if mode == 'MultiNocap':
            (tx_hash, o) = interface.constructor(self.accounts[0], self.settings, redistribute=True, cap=0)
        elif mode == 'SingleNocap':
            (tx_hash, o) = interface.constructor(self.accounts[0], self.settings, redistribute=False, cap=0)
        elif mode == 'MultiCap':
            (tx_hash, o) = interface.constructor(self.accounts[0], self.settings, redistribute=True, cap=self.default_supply_cap)
        elif mode == 'SingleCap':
            (tx_hash, o) = interface.constructor(self.accounts[0], self.settings, redistribute=False, cap=self.default_supply_cap)
        else:
            raise ValueError('Invalid mode "{}", valid are {}'.format(self.mode, DemurrageToken.valid_modes))

        r = self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.start_block = r['block_number']
        self.address = r['contract_address']

        o = block_by_number(r['block_number'])
        r = self.rpc.do(o)
        self.start_time = r['timestamp']

        logg.debug('contract address {} start block {} start time {}'.format(self.address, self.start_block, self.start_time))


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
        super(TestDemurrage, self).setUp()

        self.tax_level = 50
        self.period_seconds = 60

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
