## Table of Contents

* [Usage](#usage)
* [How It Works](#usage)

## Usage
Download repo and save locally. For loading a JSON file run 

    python main.py 

or

    python main.py data

There are a total of 3 JSON formatted files. Feel free to add or edit them in "examples/".

For tests, either run pytest in the root or use run_tests.sh.

## How It Works
There are a total of two main classes:

    class Instrument:
        getAdjustedNotional()   # Calculates the adjusted notional amount
        getDelta()              # Calculates the delta of the instrument
        getBucketSet()          # Identifies the right time bucket set
        getEffectiveNotional()  # Calculates the effective notional amount
The Instrument Class will load and calculate all the necessary values from each individual trade. This will seve the other class, SA-CCR.

    class SA-CCR(instruments):
        initialize()                    # Initializes the class and loads instruments from the loaded list to split by currency. 
        getReplacementCost()            # Calculates Replacement Cost for the baske of securities: max(V-S, 0)
        getEffectiveNotionalAmount()    # Gets the effective notional amount for each trade set (calling Instrument.getEffectiveNotional()).
        calcNotionalAmount(lis)         # Calculates notional amount for the whole basket of derivatives.
        getAddOn()                      # Uses the AddOn formula  
        getEAD()                        # Finally gets the Exposure at Default for the whole basket.
The SA-CCR class will then take the instantiated Instruments and work on them as a whole. Firstly by dividing them in different currency_sets, weighting values with the right formulas and then getting the individual and interested values.
