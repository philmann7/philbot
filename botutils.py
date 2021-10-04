# utility funcs and classes

import asyncio
import datetime
import json

from tda.client import Client
import httpx


async def gethistory(client, symbol):
    resp = client.get_price_history(
        symbol,
        period_type=Client.PriceHistory.PeriodType.DAY,
        period=Client.PriceHistory.Period.ONE_DAY,
        frequency_type=Client.PriceHistory.FrequencyType.MINUTE,
        frequency=Client.PriceHistory.Frequency.EVERY_MINUTE,
        end_datetime=datetime.datetime.today() + datetime.timedelta(days=1),
    )

    if resp.status_code != httpx.codes.OK:
        return 0

    history = resp.json()

    return history["candles"]


async def getOptionChain(
    client, symbol, strike_count, dte,
):
    resp = client.get_option_chain(
        symbol,
        strike_count=strike_count,
        from_date=datetime.datetime.today(),
        to_date=datetime.datetime.today() + datetime.timedelta(days=dte),
    )

    if resp.status_code != httpx.codes.OK:
        return 0

    chain = resp.json()

    return chain
