"""Utility functions and classes used in philbot."""

from statistics import stdev
import datetime
import re
import time
from requests import HTTPError

from tda.client import Client


def get_history(client, symbol):
    """Returns today's minute-by-minute OHCLV history for the requested symbol."""
    while True:
        try:
            resp = client.get_price_history(
                symbol,
                period_type=Client.PriceHistory.PeriodType.DAY,
                period=Client.PriceHistory.Period.ONE_DAY,
                frequency_type=Client.PriceHistory.FrequencyType.MINUTE,
                frequency=Client.PriceHistory.Frequency.EVERY_MINUTE,
                # end_datetime defaults to yesterday, necessitating the
                # following
                end_datetime=datetime.datetime.today() + datetime.timedelta(days=1),
            )
            resp.raise_for_status()
            break
        except HTTPError as http_error:
            print(http_error)
            time.sleep(0.5)

    history = resp.json()
    return history["candles"]


def get_std_dev_for_symbol(client, symbol, period, time_period=1):
    """
    Returns standard deviation of given symbol on period.
    Only uses close values of candles.
    time_period: timeframe of the candles in minutes.
    """
    candles = get_history(client, symbol)[time_period-1::time_period]
    return stdev([candle['close'] for candle in candles[-period:]])


def get_option_chain(
    client,
    symbol,
    strike_count,
    dte,
):
    """
    Returns the option chain of the requested symbol.
    Returned as-is. It's nested in a way that can be inconvenient.
    See flatten() for extraction of the contracts.
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
        except HTTPError as http_error:
            print(http_error)
            time.sleep(0.5)

    chain = resp.json()
    return chain


def flatten(chain):
    """
    Take input from get_option_chain()
    and flatten so that each contract is on its own.
    Can then be sorted easily with comprehensions for example.
    """

    flattened = []
    for key in ["callExpDateMap", "putExpDateMap"]:
        for date in chain[key]:
            for strike in chain[key][date]:
                for contract in chain[key][date][strike]:
                    flattened.append(contract)

    return flattened


def get_flattened_chain(
    client,
    symbol,
    strike_count,
    dte,
):
    """Combines the flatten and get_option_chain functions."""
    chain = get_option_chain(
        client,
        symbol,
        strike_count,
        dte,
    )
    flattened = flatten(chain)
    return flattened


class AccountActivityXMLParse:
    """
    For parsing the xml data returned by the account activity stream.
    Gets data associated with the init parameter tags.
    """

    def __init__(self, tags=None):
        """
        tags = None for a default list of tags. The default list should
        be pretty exhaustive of relevant ones.
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

    def update_tags(self, new_tags):
        """Update self.tags by appending new tags."""
        self.tags.extend(new_tags)

    def parse(self, xmlstring):
        """
        Take a string of the xml returned from an account activity stream message
        and return a dictionary of data relevant to the tags in self.tags.
        return format: {tag:data} both strings.

        Naively parses the xml by splitting on < and >
        then associating any found tags with the data that follows said tag in the xml string.
        """
        relevant_account_data = {}  # tag:data
        splitxml = re.split("[<>]", xmlstring)
        for index, word in enumerate(splitxml):
            if word in self.tags:
                relevant_account_data[word] = splitxml[index + 1]
        return relevant_account_data
