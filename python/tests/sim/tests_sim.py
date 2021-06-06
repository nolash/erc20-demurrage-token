# standard imports
import unittest
import logging

# local imports
from erc20_demurrage_token import DemurrageTokenSettings
from erc20_demurrage_token.sim import DemurrageTokenSimulation

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()


class TestSim(unittest.TestCase):

    def setUp(self):
        self.cap = 0
        settings = DemurrageTokenSettings()
        settings.name = 'Simulated Demurrage Token'
        settings.symbol = 'SIM'
        settings.decimals = 6
        settings.demurrage_level = 5010590837337300000000000000000000 # equals approx 2% per month
        settings.period_minutes = 10800 # 1 week in minutes
        self.sim = DemurrageTokenSimulation('evm:foochain:42', settings, redistribute=True, cap=self.cap, actors=10)


    def test_mint(self):
        self.sim.mint(self.sim.actors[0], 1024)
        self.sim.next()
        balance = self.sim.balance(self.sim.actors[0])
        self.assertEqual(balance, 1023)


    def test_transfer(self):
        self.sim.mint(self.sim.actors[0], 1024)
        self.sim.transfer(self.sim.actors[0], self.sim.actors[1], 500)
        self.sim.next()
        balance = self.sim.balance(self.sim.actors[0])
        self.assertEqual(balance, 523)

        balance = self.sim.balance(self.sim.actors[1])
        self.assertEqual(balance, 499)


    def test_more_periods(self):
        self.sim.mint(self.sim.actors[0], 1024)
        self.sim.mint(self.sim.actors[1], 1024)
        self.sim.next()

        self.sim.mint(self.sim.actors[0], 1024)
        self.sim.next()

        balance = self.sim.balance(self.sim.actors[0])
        self.assertEqual(balance, 2047)


    def test_demurrage(self):
        self.sim.mint(self.sim.actors[0], self.sim.from_units(100))
        self.sim.mint(self.sim.actors[1], self.sim.from_units(100))
        self.sim.transfer(self.sim.actors[0], self.sim.actors[2], self.sim.from_units(10))
        self.sim.next()

        balance = self.sim.balance(self.sim.actors[0])
        self.assertEqual(balance, 90005520)
        
        balance = self.sim.balance(self.sim.actors[1])
        self.assertEqual(balance, 99995000)

        balance = self.sim.balance(self.sim.actors[1], base=True)
        self.assertEqual(balance, 100000000)


if __name__ == '__main__':
    unittest.main()
