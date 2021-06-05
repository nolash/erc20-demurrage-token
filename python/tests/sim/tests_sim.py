# standard imports
import unittest
import logging

# external imports
from chainlib.chain import ChainSpec

# local imports
from erc20_demurrage_token import DemurrageTokenSettings
from erc20_demurrage_token.sim import DemurrageTokenSimulation

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class TestSim(unittest.TestCase):

    def setUp(self):
        self.chain_spec = ChainSpec('evm', 'foochain', 42)
        #self.cap = 1000000000
        self.cap = 0
        settings = DemurrageTokenSettings()
        settings.name = 'Simulated Demurrage Token'
        settings.symbol = 'SIM'
        settings.decimals = 6
        settings.demurrage_level = 50
        settings.period_minutes = 10800
        self.sim = DemurrageTokenSimulation(self.chain_spec, settings, redistribute=True, cap=self.cap, actors=10)


    def test_mint(self):
        self.sim.mint(self.sim.actors[0], 1024)
        self.sim.next()
        balance = self.sim.balance(self.sim.actors[0])
        self.assertEqual(balance, 1024)


    def test_transfer(self):
        self.sim.mint(self.sim.actors[0], 1024)
        self.sim.transfer(self.sim.actors[0], self.sim.actors[1], 500)
        self.sim.next()


if __name__ == '__main__':
    unittest.main()
