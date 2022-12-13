# standard imports
import logging
import datetime
import math

# eternal imports
from chainlib.eth.constant import ZERO_ADDRESS

# local imports
from .token import DemurrageToken

logg = logging.getLogger(__name__)


class DemurrageCalculator:

    def __init__(self, interest_f_minute):

        self.r_min = interest_f_minute
        self.r_hour = 1 - ((1 -self.r_min) ** 60)
        self.r_day = 1 - ((1 -self.r_hour) ** 24)
        #self.r_week = interest_f_day ** 7
        logg.info('demurrage calculator set with min {:.32f} hour {:.32f} day {:.32f}'.format(self.r_min, self.r_hour, self.r_day))


    def amount_since(self, amount, timestamp):
        delta = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(timestamp)
        adjusted_amount = amount * ((1 - self.r_day) ** (delta.days))
        logg.debug('adjusted for {} days {} -> {}'.format(delta.days, amount, adjusted_amount))

        remainder = delta.seconds
        remainder_hours = math.floor(remainder / (60 * 60))
        adjusted_delta = adjusted_amount * ((1 - self.r_hour) ** remainder_hours)
        adjusted_amount -= (adjusted_amount - adjusted_delta)
        logg.debug('adjusted for {} hours {} -> {} delta {}'.format(remainder_hours, amount, adjusted_amount, adjusted_delta))

        remainder -= (remainder_hours * (60 * 60))
        remainder_minutes = math.floor(remainder / 60)
        adjusted_delta = adjusted_amount * ((1 - self.r_min) ** remainder_minutes)
        adjusted_amount -= (adjusted_amount - adjusted_delta)
        logg.debug('adjusted for {} minutes {} -> {} delta {}'.format(remainder_minutes, amount, adjusted_amount, adjusted_delta))

        return adjusted_amount

    
    def amount_since_slow(self, amount, timestamp):
        delta = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(timestamp)
        remainder_minutes = math.floor(delta.total_seconds() / 60)
        adjusted_amount = amount * ((1 - self.r_min) ** remainder_minutes)
        logg.debug('adjusted for {} minutes {} -> {} delta {}'.format(remainder_minutes, amount, adjusted_amount, amount - adjusted_amount))

        return adjusted_amount


    @staticmethod
    def from_contract(rpc, chain_spec, contract_address, sender_address=ZERO_ADDRESS):
        c = DemurrageToken(chain_spec)
        o = c.tax_level(contract_address, sender_address=sender_address)
        r = rpc.do(o)
        taxlevel_i = c.parse_tax_level(r)

        o = c.resolution_factor(contract_address, sender_address=sender_address)
        r = rpc.do(o)
        divider = c.parse_resolution_factor(r)
        logg.debug('taxlevel {} f {}'.format(taxlevel_i, divider))
        taxlevel_f = taxlevel_i / divider
        return DemurrageCalculator(taxlevel_f)
