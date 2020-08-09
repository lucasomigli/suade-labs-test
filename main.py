from datetime import datetime, timedelta
import numpy as np
from functools import reduce
import json
import argparse
from terminaltables import AsciiTable


# Instrument class that assesses data from the FIRE regulated json file and evaluates
# required variables for EAD calculation. Swaps and options are evaluated singularly.


class Instrument:

    def __init__(self, data):
        self.id = data['id']
        self.type = data['type']
        self.asset_class = data['asset_class']
        self.date = datetime.strptime(data['date'], '%Y-%m-%dT%H:%M:%SZ')
        self.start_date = datetime.strptime(data['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        self.end_date = datetime.strptime(data['end_date'], '%Y-%m-%dT%H:%M:%SZ')
        self.trade_date = datetime.strptime(data['trade_date'], '%Y-%m-%dT%H:%M:%SZ')
        self.currency_code = data['currency_code']
        self.value_date = datetime.strptime(data['value_date'], '%Y-%m-%dT%H:%M:%SZ')
        self.mtm_dirty = data['mtm_dirty']
        self.notional_amount = data['notional_amount']
        self.payment_type = data['payment_type']
        self.receive_type = data['receive_type']

        self.floatingRate = .06         # using 6% for the floating rate as an example
        self.fixedRate = .05            # using 5% for the fixed rate as an example
        self.sigma = 0.5                # volatility for interest rate swaps and swaptions is 50%
        self.isCall = 0                 # initialised to zero. Returns 1 if contract is a call and -1 if contract is a put

        self.maturity = (self.end_date - self.start_date).days / 365
        self.timeBucket = self.getBucketSet()
        self.MF = 1
        self.delta = self.getDelta()

    # Returns adjusted notional based on the notional amount, S (contract start date) and E (contract end date)
    def getAdjustedNotional(self):
        S = (self.start_date - self.date).days / 365
        E = (self.end_date - self.date).days / 365
        return self.notional_amount * (np.exp(-0.05 * S) - np.exp(-0.05 * E)) / 0.05

    # Evaluates delta for the security. This is following the formula written in the SC-CCR handbook.
    def getDelta(self):

        payLegRate = 0.0
        receiveLegRate = 0.0

        if self.payment_type == 'floating':
            payLegRate = self.floatingRate
            receiveLegRate = self.fixedRate
        else:
            payLegRate = self.fixedRate
            receiveLegRate = self.floatingRate

        self.isCall = 1.0 if receiveLegRate > payLegRate else -1.0

        if self.type == 'vanilla_swap':
            return self.isCall
        else:
            phi = (1 + np.sqrt(5)) / 2
            contractual_date = self.maturity

            return float(self.isCall * phi * (np.log(payLegRate/receiveLegRate) + 0.5 * self.sigma**2 * contractual_date) / (self.sigma * contractual_date**0.5))

    # Evaluates the type of time bucket for the specific swap based on the maturity
    # (less than one year, between 1 and 5 years, greater than 5)
    def getBucketSet(self):

        if self.maturity < 1:
            return 1
        elif self.maturity < 5:
            return 2
        else:
            return 3

    # Finalising notional amount evaluation using delta and adjusted notional.
    # MF = 1 as there are no margin agreements and no collateral implications.
    def getEffectiveNotional(self):
        return self.delta * self.getAdjustedNotional() * self.MF


# Main calculations class, this is where the core of EAD will be evaluated
# and instruments are divided in currency sets.


class SA_CCR:

    def __init__(self, instruments: list):
        self.instruments = instruments
        self.SF = 0.005
        self.multiplier = 1
        self.hedging_sets = {}
        self.effectiveNotionals = []

    # Initialises set, splitting trades by currency in order to evaluate notionalAmounts separately
    def initialize(self):
        for item in self.instruments:
            if item.currency_code not in self.hedging_sets:
                self.hedging_sets[item.currency_code] = [item]
            else:
                self.hedging_sets[item.currency_code].append(item)

    # Gets Replacement Cost for the basket of securities. This is equal to max(V-S, 0)
    def getReplacementCost(self):
        return max(reduce(lambda x, y: x + y, [float(v.mtm_dirty) for v in self.instruments]), 0.0)

    # Calculating effectiveNotionalAmount for each trade in our basket of derivatives.
    # Calling Instrument.getEffectiveNotional from the Instrument class.
    def getEffectiveNotionalAmount(self):
        for currency in self.hedging_sets:
            _set = [instrument.getEffectiveNotional() for instrument in self.hedging_sets[currency]]
            self.effectiveNotionals.append(self.calcNotionalAmount(_set))

    # Calculating notionalAmount for each set (grouped by currency) in hedging_sets
    def calcNotionalAmount(self, lis):
        a = lis[0]
        b = 0.0 if len(lis) < 2 else lis[1]
        c = 0.0 if len(lis) < 3 else lis[2]
        return (a**2 + b**2 + c**2 + 1.4*a*b + 1.4*a*c + 0.6*b*c)**0.5

    # Summing all the items in effectiveNotionals list by following the AddOn Formula
    def getAddOn(self):
        return reduce((lambda x, y: x + y), list(map(lambda x: x * self.SF, self.effectiveNotionals)))

    # Main method that calculates EAD for the instruments. Initialises sets,
    # sets up the effectiveNotionalAmounts and computes Exposure ad Default.
    def getEAD(self):
        self.initialize()
        self.getEffectiveNotionalAmount()

        self.EAD = 1.4 * (60 + self.multiplier * self.getAddOn())

        return self.EAD


def main():

    # argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default='data', nargs='?',
                        help='Name of the JSON file to load (it will need to be stored in "examples/")')
    args = parser.parse_args()

    # Set up. Opens JSON file (data.json by default) and initializes the process with instruments.
    with open("examples/{}.json".format(args.file), 'r') as f:
        data = json.load(f)
    instruments = [Instrument(item) for item in data['data']]
    process = SA_CCR(instruments)
    process.ead = process.getEAD()

    # Using terminaltables for drwawing tables.
    INSTRUMENTS_TABLE = [['Instrument', 'Type', 'Maturity (years)', 'Notional', 'Pay Leg', 'Receive Leg', 'Market Value', 'Adjusted Notional', 'Delta']]
    INSTRUMENTS_TABLE.extend([[i.id, i.type, i.maturity, i.notional_amount, i.payment_type,
                               i.receive_type, i.mtm_dirty, i.getAdjustedNotional(), i.delta]for i in instruments])

    SA_CCR_TABLE = [['Replacement Cost', 'Effective Notionals', 'AddOn', 'EAD'],
                    [process.getReplacementCost(), "Set1: %f; Set2: %f" % tuple(process.effectiveNotionals), process.getAddOn(), process.ead]]

    print(AsciiTable(INSTRUMENTS_TABLE, 'INSTRUMENTS').table, '\n',
          AsciiTable(SA_CCR_TABLE, 'FINALISED EAD').table)

    return process.EAD


if __name__ == "__main__":
    main()
