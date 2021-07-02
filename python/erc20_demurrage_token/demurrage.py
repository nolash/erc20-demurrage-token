#
import logging
import datetime
import math

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


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
        logg.debug('adjusted for {} hours {} -> {} delta {}'.format(remainder_minutes, amount, adjusted_amount, adjusted_delta))

        return adjusted_amount
