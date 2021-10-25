from tda.auth import easy_client
from tda.client import Client
from tda.streaming import StreamClient

import os
import asyncio
import json

from dotenv import load_dotenv

from msghandler import MessageHandler
from signaler import Signaler
from ordermanager import OrderManager, OrderManagerConfig

load_dotenv()

client = easy_client(
    api_key=os.getenv("client_id"),
    redirect_uri="https://localhost",
    token_path="token.json",
)
stream_client = StreamClient(
    client, account_id=int(
        os.getenv("account_number")))


def message_handling(msg, signaler, msghandler, ordmngr):
    # newdatafor in the form of [(symbol, service),...]
    # or [(content, service),...] in the case of account activity
    try:
        newdatafor = msghandler.handle(msg)
    except KeyError as e:
        print(msg)
        print(e)
        return None

    if newdatafor and newdatafor[0][1] == "ACCT_ACTIVITY":
        return [
            ordmngr.updateFromAccountActivity(symbol, msg_type, msg_data)
            for ((symbol, msg_type, msg_data), service) in newdatafor
        ]

    # the way signaler is currently written it should be only for one symbol
    # so multiple symbols will break this
    updates = [
        (symbol, signaler.update(
            service, msghandler.last_messages[symbol],))
        for (symbol, service) in newdatafor
        # for signaler in signalers if signaler.symbol == symbol
    ]
    ordermngupdate = [
        ordmngr.updateFromQuote(
            client, int(
                os.getenv("account_number")), signaler.cloud, symbol, signal, newprice)
        for (symbol, (signal, newprice)) in updates
    ]
    print(f"Short EMA:{signaler.cloud.shortEMA}\n" +
          f"Long EMA:{signaler.cloud.longEMA}\n")
    print(f"Cloud status: {signaler.cloud.status}")
    [print(pos) for pos in ordmngr.currentpositions.values()]


async def read_stream(msghandler, signaler, ordmngr):
    await stream_client.login()
    # await stream_client.quality_of_service(StreamClient.QOSLevel.EXPRESS)

    # Always add handlers before subscribing because many streams start sending
    # data immediately after success, and messages with no handlers are
    # dropped.
    stream_client.add_chart_equity_handler(
        lambda msg: message_handling(msg, signaler, msghandler, ordmngr)
    )
    await stream_client.chart_equity_subs(["SPY"])

    stream_client.add_level_one_equity_handler(
        lambda msg: message_handling(msg, signaler, msghandler, ordmngr)
    )
    await stream_client.level_one_equity_subs(["SPY"])

    stream_client.add_account_activity_handler(
        lambda msg: message_handling(msg, signaler, msghandler, ordmngr)
    )
    await stream_client.account_activity_sub()

    while True:
        await stream_client.handle_message()


async def main():
    msghandler = MessageHandler()

    shortEMALength = 9
    longEMALength = 21
    signaler = Signaler(client, "SPY", shortEMALength, longEMALength)

    ordermanager_config = OrderManagerConfig(
        stdev_period=50,
        mindte=2,
        maxdte=3,
        max_contract_price=2.2,
        min_contract_price=0.80,
        max_spread=0.06,
        max_loss=.20,
        min_loss=.10,
        min_risk_reward_ratio=2.0,
        strike_count=5,
        limit_padding=.01,
        time_btwn_positions=15,
        order_timeout_length=30,
    )
    ordmngr = OrderManager(ordermanager_config)
    await read_stream(msghandler, signaler, ordmngr)


asyncio.run(main())
