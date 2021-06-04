# standard imports
import logging

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
PERIOD = 1



class TestDemurrage(EthTesterCase):

    def setUp(self):
        super(TestDemurrage, self).setUp()
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        self.settings = DemurrageTokenSettings()
        self.settings.name = 'Foo Token'
        self.settings.symbol = 'FOO'
        self.settings.decimals = 6
        self.settings.demurrage_level = TAX_LEVEL * (10 ** 32)
        self.settings.period_minutes = PERIOD
        self.settings.sink_address = self.accounts[1]

        o = block_latest()
        self.start_block = self.rpc.do(o)
        
        o = block_by_number(self.start_block, include_tx=False)
        r = self.rpc.do(o)
        logg.debug('r {}'.format(r))
        try:
            self.start_time = int(r['timestamp'], 16)
        except TypeError:
            self.start_time = int(r['timestamp'])


    def tearDown(self):
        pass



class TestDemurrageDefault(TestDemurrage):

    def setUp(self):
        super(TestDemurrageDefault, self).setUp()
   
        nonce_oracle = RPCNonceOracle(self.accounts[0], self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], self.settings)
        r = self.rpc.do(o)

        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        self.address = r['contract_address']
