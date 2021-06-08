# standard imports
import logging

# local imports
from erc20_demurrage_token import DemurrageTokenSettings
from erc20_demurrage_token.sim import DemurrageTokenSimulation

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()

decay_per_minute = 0.00000050105908373373 # equals approx 2% per month

# parameters for simulation object
settings = DemurrageTokenSettings()
settings.name = 'Simulated Demurrage Token'
settings.symbol = 'SIM'
settings.decimals = 6
settings.demurrage_level = int(decay_per_minute*(10**38))
#settings.period_minutes = 1 # 1 week in minutes
settings.period_minutes = 60*24*7
chain = 'evm:foochain:42'
cap = (10 ** 6) * (10 ** 12)

# instantiate simulation
sim = DemurrageTokenSimulation(chain, settings, redistribute=False, cap=cap, actors=10)

# name the usual suspects
alice = sim.actors[0]
bob = sim.actors[1]
carol = sim.actors[2]

# mint and transfer (every single action advances one block, and one second in time)
sim.mint(alice, sim.from_units(100)) # 10000000 tokens
sim.mint(bob, sim.from_units(100))
sim.transfer(alice, carol, sim.from_units(50))

# check that balances have been updated
assert sim.balance(alice) == sim.from_units(50)
assert sim.balance(bob) == sim.from_units(100)
assert sim.balance(carol) == sim.from_units(50)

# advance to next redistribution period
sim.next()

# inspect balances
print('alice balance: demurraged {:>9d} base {:>9d}'.format(sim.balance(alice), sim.balance(alice, base=True)))
print('bob balance:   demurraged {:>9d} base {:>9d}'.format(sim.balance(bob), sim.balance(bob, base=True)))
print('carol balance: demurraged {:>9d} base {:>9d}'.format(sim.balance(carol), sim.balance(carol, base=True)))
print('sink balance:  demurraged {:>9d} base {:>9d}'.format(sim.balance(sim.sink_address), sim.balance(sim.sink_address, base=True)))

# get times
minutes = sim.get_minutes()
timestamp = sim.get_now()
start = sim.get_start()
period = sim.get_period()
print('start {} now {} period {} minutes passed {}'.format(start, timestamp, period, minutes))


contract_demurrage = 1 - sim.get_demurrage()    # demurrage in percent (float)
frontend_demurrage = 1.0 - ((1 - decay_per_minute) ** minutes)   # corresponding demurrage modifier (float)
demurrage_delta = contract_demurrage - frontend_demurrage      # difference between demurrage in contract and demurrage calculated in frontend

alice_checksum = 50000000 - (50000000 * frontend_demurrage) + (200000000 * frontend_demurrage) # alice's balance calculated with frontend demurrage
print("""alice frontend balance {}
alice contract balance {}
frontend demurrage {:.38f}
contract demurrage {:.38f}
demurrage delta {:.38f}""".format(
    alice_checksum,
    sim.balance(alice),
    frontend_demurrage,
    contract_demurrage,
    demurrage_delta),
)

balance_sum = sim.balance(alice) + sim.balance(bob) + sim.balance(carol) + sim.balance(sim.sink_address)
supply = sim.get_supply()
print('sum of contract demurraged balances {}'.format(balance_sum))
print('total token supply {}'.format(supply))
