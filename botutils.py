# utility funcs and classes

import asyncio
import datetime
import json

from tda.client import Client
import httpx


async def gethistory(client, symbol):
    resp = await client.get_price_history(
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
