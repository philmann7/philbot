from tda.auth import easy_client
from tda.client import Client
from tda.streaming import StreamClient

import os
import asyncio
import json

from dotenv import load_dotenv

from msghandler import MessageHandler
from signaler import Signaler
from ordermanager import OrderManager

load_dotenv()

client = easy_client(
    api_key=os.getenv("client_id"),
    redirect_uri="https://localhost",
    token_path="token.json",
)
stream_client = StreamClient(client, account_id=int(os.getenv("account_number")))


async def message_handling(msg, signaler, msghandler, ordmngr):
    # newdatafor in the form of [(symbol, service),...]
    newdatafor = await msghandler.handle(msg)
    # the way signaler is currently written it should be only for one symbol
    # so multiple symbols will break this
    updates = [
        (symbol, signaler.update(service, msghandler.last_messages[service][symbol]))
        for (symbol, service) in newdatafor
        # for signaler in signalers if signaler.symbol == symbol
    ]
    ordermngupdate = [
        ordmngr.update(symbol, signal, newprice)
        for (symbol, (signal, newprice)) in updates
    ]


async def read_stream(msghandler, signaler, ordmngr):
    await stream_client.login()
    # await stream_client.quality_of_service(StreamClient.QOSLevel.EXPRESS)

    # Always add handlers before subscribing because many streams start sending
    # data immediately after success, and messages with no handlers are dropped.
    stream_client.add_chart_equity_handler(
        lambda msg: message_handling(msg, signaler, msghandler)
    )
    await stream_client.chart_equity_subs(["SPY"])

    stream_client.add_level_one_equity_handler(
        lambda msg: message_handling(msg, signaler, msghandler)
    )
    await stream_client.level_one_equity_subs(["AAPL"])

    while True:
        await stream_client.handle_message()


async def main():
    msghandler = MessageHandler()
    signaler = Signaler()
    ordmngr = OrderManager()
    await read_stream(msghandler, signaler, ordmngr)


asyncio.run(main())
