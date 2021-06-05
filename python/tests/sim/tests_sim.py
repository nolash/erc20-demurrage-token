# standard imports
import unittest
import logging

# external imports
from chainlib.chain import ChainSpec

# local imports
from erc20_demurrage_token import DemurrageTokenSettings
from erc20_demurrage_token.sim import DemurrageTokenSimulation

logg = logging.getLogger()


class TestSim(unittest.TestCase):

    def setUp(self):
        self.chain_spec = ChainSpec('evm', 'foochain', 42)
        self.cap = 1000000000
        settings = DemurrageTokenSettings()
        settings.name = 'Simulated Demurrage Token'
        settings.symbol = 'SIM'
        settings.decimals = 6
        settings.demurrage_level = 50
        settings.period_minutes = 10800
        self.sim = DemurrageTokenSimulation(self.chain_spec, settings, redistribute=True, cap=self.cap)


    def test_hello(self):
        pass

if __name__ == '__main__':
    unittest.main()
