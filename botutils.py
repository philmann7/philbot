# utility funcs and classes

from statistics import stdev
import asyncio
import datetime
import json
import re
import time

from tda.client import Client
import httpx


def gethistory(client, symbol):
    """
    returns today's minute-by-minute OHCLV history
    """
    while True:
        try:
            resp = client.get_price_history(
                symbol,
                period_type=Client.PriceHistory.PeriodType.DAY,
                period=Client.PriceHistory.Period.ONE_DAY,
                frequency_type=Client.PriceHistory.FrequencyType.MINUTE,
                frequency=Client.PriceHistory.Frequency.EVERY_MINUTE,
                end_datetime=datetime.datetime.today() + datetime.timedelta(days=1),
            )
            resp.raise_for_status()
            break
        except Exception as e:
            print(e)
            time.sleep(0.5)

    return history["candles"]


def getStdDev(candles, period, values="close"):
    """
    takes input of gethistory.
    uses close vals by default
    returns standard deviation of the period
    """
    return stdev([candle[values] for candle in candles[-period:]])


def getStdDevForSymbol(client, symbol, period):
    """
    convenience func to combin getStdDev and gethistory
    """
    history = gethistory(client, symbol)
    standard_deviation = getStdDev(history, period)
    return standard_deviation


def getOptionChain(
    client,
    symbol,
    strike_count,
    dte,
):
    """
    returns the option chain of the requested symbol.
    returned as-is it's nested in a way that can
    be inconvenient. see flatten()
    """
    while True:
        try:
            resp = client.get_option_chain(
                symbol,
                strike_count=strike_count,
                from_date=datetime.datetime.today(),
                to_date=datetime.datetime.today() + datetime.timedelta(days=dte),
            )
            resp.raise_for_status()
            break
        except Exception as e:
            print(e)
            time.sleep(0.5)

    chain = resp.json()

    return chain


def flatten(chain):
    """
    take input from getOptionChain()
    and flatten so that each contract is on its own.
    can then be sorted easily with comprehensions for example

    would like to turn this into a comprehension rather than nested loops
    """

    flattened = []
    for key in ["callExpDateMap", "putExpDateMap"]:
        for date in chain[key]:
            for strike in chain[key][date]:
                for contract in chain[key][date][strike]:
                    flattened.append(contract)

    return flattened


def getFlattenedChain(
    client,
    symbol,
    strike_count,
    dte,
):
    """
    combines the flatten and getOptionChain functions
    """
    chain = getOptionChain(
        client,
        symbol,
        strike_count,
        dte,
    )
    flattened = flatten(chain)
    return flattened


class AccountActivityXMLParse:
    """
    for parsing the xml data returned by the account activity stream.
    gets data associated with the init parameter tags
    """

    def __init__(self, tags=None):
        """
        tags = None for a default list of tags. the default list should
        be pretty exhaustive of relevant ones.
        ignore any tags the message is missing.
        """
        self.tags = tags or [
            "OrderKey",
            "ActivityTimestamp",
            "Symbol",
            "SecurityType",
            "Limit",
            "Bid",
            "Ask",
            "OrderType",
            "OrderEnteredDateTime",
            "OrderInstructions",
            "OriginalQuantity",
            "LastUpdated",
        ]

    def parse(self, xmlstring):
        """
        take a string of the xml returned from an account
        activity stream message and return a dictionary
        of data relevant to the tags in self.tags.
        return format {tag:data} both str

        naively parses the xml by splitting on < and >
        then associating any found tags with the data
        that follows it in the xml string.
        """
        relevant_account_data = {}  # tag:data
        splitxml = re.split("[<>]", xmlstring)
        for index, word in enumerate(splitxml):
            if word in self.tags:
                relevant_account_data[word] = splitxml[index + 1]
        return relevant_account_data
