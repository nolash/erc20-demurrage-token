# standard imports
import unittest
import logging

# external imports
from chainlib.chain import ChainSpec

# local imports
from erc20_demurrage_token import DemurrageTokenSettings
from erc20_demurrage_token.sim import (
        DemurrageTokenSimulation,
        TxLimitException,
        )

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()

class TestLimit(unittest.TestCase):

    def setUp(self):
        self.chain_spec = ChainSpec('evm', 'foochain', 42)
        self.cap = 0
        settings = DemurrageTokenSettings()
        settings.name = 'Simulated Demurrage Token'
        settings.symbol = 'SIM'
        settings.decimals = 6
        settings.demurrage_level = 1
        settings.period_minutes = 1
        self.sim = DemurrageTokenSimulation(self.chain_spec, settings, redistribute=True, cap=self.cap, actors=1)


    def test_limit(self):
        with self.assertRaises(TxLimitException):
            for i in range(60):
                self.sim.mint(self.sim.actors[0], i)
        

if __name__ == '__main__':
    unittest.main()
