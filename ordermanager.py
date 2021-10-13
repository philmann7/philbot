# tracks and manages positions
# sends orders
# moves stoploss to take profits
# https://tda-api.readthedocs.io/en/latest/client.html#orders
from signaler import Signals
from ema import CloudColor, CloudPriceLocation
from botutils import getStdDevForSymbol, getFlattenedChain

from tda.orders.options import option_buy_to_open_limit, option_sell_to_close_limit, option_sell_to_close_market, option_buy_to_open_market
from tda.utils import Utils

from enum import Enum
from datetime import datetime, timedelta

import httpx
import time


class StopType(Enum):
    EMALong, EMAShort = range(2)

    @classmethod
    def stopTypeToLevel(cls, stoptype, cloud):
        """
        gets a number from the type of stop (ie EMALong etc.)
        """
        match stoptype:
            case cls.EMAShort:
                return cloud.shortEMA
            case cls.EMALong:
                return cloud.longEMA
            case other:
                return other

    @classmethod
    def stopTupleToLevel(cls, stoptuple, cloud):
        """
        returns a level (price) from a stop tuple
        stop tuple expected in the format of
        (StopType, priceoffset: float)
        """
        stoptype, offset = stoptuple
        return cls.stopTypeToLevel(stoptype, cloud) + offset

# possibly turn this into class to store values like multipliers


def levelSet(
    currentprice, standard_deviation, cloud,
):
    """
    calculates risk and reward levels.
    should return a stop loss and take profit levels
    for opening a new position

    returns a stop (in the format (StopType, offset) and a take profit level)
    """
    stop = None
    takeprofit = None
    cloudcolor = cloud.status[0]
    cloudlocation = cloud.status[1]

    stopmod = 1  # number of std devs
    takeprofitmod = 2

    directionmod = 1
    if cloudcolor == CloudColor.RED:
        directionmod = -1

    takeprofitmod = takeprofitmod * directionmod
    stopmod = stopmod * directionmod

    if cloudlocation == CloudPriceLocation.INSIDE:  # ie passing through long ema
        stop = (StopType.EMALong, (standard_deviation * stopmod * -1))

    if (
        cloudlocation == CloudPriceLocation.ABOVE  # ie passing through short ema
        or cloudlocation == CloudPriceLocation.BELOW  # from either cloud
    ):
        stop = (StopType.EMALong, 0)
        # or in case the long EMA is very far away
        if abs(cloud.longEMA - currentprice) > abs(currentprice -
                                                   (cloud.shortEMA - (directionmod * 2 * standard_deviation))):
            stop = (StopType.EMAShort, (directionmod * 2 * standard_deviation))

    riskloss = abs(currentprice - StopType.stopTupleToLevel(stop, cloud))

    takeprofit = cloud.shortEMA + (standard_deviation * takeprofitmod)
    # enforce 3:1 reward:risk if takeprofit is very far away
    if abs(currentprice - takeprofit) > 4 * riskloss:
        takeprofit = currentprice + (directionmod * 3 * riskloss)

    return stop, takeprofit


class LevelSetter:
    """
    holds levelsetter settings
    """

    pass


class OrderManagerConfig:
    def __init__(
        self,
        stdev_period,
        mindte,
        maxdte,
        max_contract_price,
        min_contract_price,
        max_spread,
        max_loss,
        min_risk_reward_ratio,
        strike_count,
        limit_padding,
        time_btwn_positions,  # this and order_timeout_length in seconds
        order_timeout_length,
    ):
        self.stdev_period = (
            stdev_period  # period of calculation of the standard deviation
        )
        self.mindte = mindte  # days to expiration on the options contracts
        self.maxdte = maxdte
        self.max_contract_price = max_contract_price
        self.min_contract_price = min_contract_price
        self.max_spread = max_spread  # bid/ask spread
        # on price of contract so use option pricing convention ie .10 for 10
        # dollars
        self.max_loss = max_loss
        # profit/loss expected_move_to_profit/expected_move_to_stop
        self.min_risk_reward_ratio = min_risk_reward_ratio
        self.strike_count = strike_count  # number of strikes to ask the API for
        self.limit_padding = limit_padding  # if set to 0.01 the limit buy will
        # be set at ask+.01
        self.time_btwn_positions = time_btwn_positions
        self.order_timeout_length = order_timeout_length


class Position:
    """
    Controls and tracks an options position
    """

    def __init__(self, contract, takeprofit, stop, state):
        self.contract = contract  # contract symbol
        self.state = state  # signaler.Signals.OPEN or OPEN_OR_INCREASE
        # if opened on OPEN_OR_INCREASE only allow position size 1

        self.netpos = 0
        self.associated_orders = {}  # id:status

        self.stop = stop  # (StopType, offset)
        self.takeprofit = takeprofit

        self.opened_time = datetime.now()
        self.closed_time = None

    # possibly move these into order manager
    # an initializer. for adding to a position use updatePositionFromQuote

    def open(
        self, client, account_id, limit,
    ):
        """
        For opening a position on the first valid buy signal.

        This method should not be used to add to a position, for
        that use updatePositionFromQuote and increase.
        """
        while True:
            try:
                response = client.place_order(account_id,
                                              option_buy_to_open_limit(
                                                  self.contract, 1, limit)
                                              .build()
                                              )
                response.raise_for_status()
                break
            except Exception as e:
                print(e)
                time.sleep(0.5)
        order_id = Utils(client, account_id).extract_order_id(response)
        # order_id is potentially None
        if not order_id:
            return 0
        self.associated_orders[order_id] = "OPEN"
        print(f"Order sent for {self.contract}")
        return order_id

    def close(self, client, account_id):
        """
        Cancels any orders not already canceled or filled.
        Sells to close any contracts currently held.
        """
        self.state = Signals.EXIT
        self.closed_time = datetime.now()

        print(f"Closing postion {self.contract}")
        # canceling orders
        for order_id in self.associated_orders:
            if self.associated_orders[order_id] not in {
                    'PENDING_CANCEL', 'CANCELED', 'FILLED', 'REPLACED', 'EXPIRED'}:
                try:
                    client.cancel_order(account_id, order_id)
                except Exception as e:
                    print(
                        f"Exception canceling order (id: {order_id}:{self.associated_orders[order_id]}):\n{e}")
        # selling to close out position (important that this is done
        # after canceling so sell orders don't get canceled)
        if self.netpos < 1:
            return 0

        while True:
            try:
                response = client.place_order(account_id,
                                              option_sell_to_close_market(
                                                  self.contract, self.netpos)
                                              .build()
                                              )
                response.raise_for_status()
                break
            except Exception as e:
                print(e)
                time.sleep(0.5)

        order_id = Utils(client, account_id).extract_order_id(response)
        # order_id is potentially None
        if not order_id:
            return 0
        self.associated_orders[order_id] = "SELL_TO_CLOSE"
        return order_id

    def increase(
        self, client, account_id,
    ):
        """
        Adds to the position
        """
        self.state = Signals.OPEN_OR_INCREASE

        # don't increase if there are open orders
        if "OPEN" in self.associated_orders.values():
            return 0

        while True:
            try:
                response = client.place_order(account_id,
                                              option_buy_to_open_market(
                                                  self.contract, 1,)
                                              .build()
                                              )
                response.raise_for_status()
                break
            except Exception as e:
                print(e)
                time.sleep(0.5)

        order_id = Utils(client, account_id).extract_order_id(response)
        # order_id is potentially None
        if not order_id:
            return 0
        self.associated_orders[order_id] = "OPEN"
        print(f"Adding to position {self.contract}")
        return order_id

    def updatePositionFromQuote(
            self, cloud, signal, price, standard_deviation):
        """
        Handles stop loss, take profit and adding to a position.
        Opening a position and closing for other reasons
        are handled elsewhere.
        """
        if self.state == Signals.EXIT:
            return Signals.EXIT

        if signal == Signals.OPEN_OR_INCREASE and self.state == Signals.OPEN:
            return self.increase()

        cloud_color = cloud.status[0]

        stop_level = StopType.stopTupleToLevel(self.stop, cloud)
        if (price < stop_level and cloud_color == CloudColor.GREEN) or (
                price > stop_level and cloud_color == CloudColor.RED):
            return self.close()

        if (price > self.takeprofit + (standard_deviation * 0.25) and cloud_color == CloudColor.GREEN) or (
                price < self.takeprofit - (standard_deviation * 0.25) and cloud_color == CloudColor.RED):
            self.stop = (self.takeprofit, 0)
            self.takeprofit += (standard_deviation *
                                0.75) if cloud_color == CloudColor.GREEN else (standard_deviation * -0.75)

    def updateFromAccountActivity(self, message_type, otherdata):
        """
        Handles order status updates like order fills or UROUT messages.
        otherdata argument should be the output of the XML data parser.
        """
        self.associated_orders[otherdata["OrderKey"]] = message_type
        match message_type:
            case "OrderFill":
                self.netpos += otherdata["OriginalQuantity"] if otherdata["OrderInstructions"] == "Buy" else \
                    -1 * otherdata["OriginalQuantity"]

    def checkTimeouts(self, client, account_id, timeoutlength):
        """
        cancels orders that have been open and unfilled
        for too long.
        """
        now = datetime.now()
        for order_id in self.associated_orders:
            if self.associated_orders[order_id] == "OPEN" and timedelta.total_seconds(
                    now - self.opened_time) < timeoutlength:
                try:
                    client.cancel_order(account_id, order_id)
                except Exception as e:
                    print(
                        f"Exception canceling order (id: {order_id}:{self.associated_orders[order_id]}):\n{e}")


class OrderManager:
    def __init__(
        self, config,
    ):
        self.config = config  # class OrderManagerConfig
        self.currentpositions = {}  # symbol:Position

    def updateFromQuote(self, client, account_id, cloud,
                        symbol, signal, newprice):
        """
        update parameter is the output of
        signaler.update so update should be Signals.something
        or 0
        """
        # garbage collection
        if symbol in self.currentpositions and self.currentpositions[symbol].closed_time:
            now = datetime.now()
            if timedelta.total_seconds(
                    now - self.currentpositions[symbol].closed_time) > self.config.time_btwn_positions:
                self.currentpositions.pop(symbol)
            else:
                return 0
        # this will be a cloud color change
        if signal == Signals.CLOSE and symbol in self.currentpositions:
            self.currentpositions[symbol].close(client, account_id)

        elif symbol in self.currentpositions:
            self.currentpositions[symbol].checkTimeouts(
                client, account_id, self.config.order_timeout_length)

            standard_deviation = getStdDevForSymbol(
                client, symbol, self.config.stdev_period)
            self.currentpositions[symbol].updatePositionFromQuote(
                cloud, signal, newprice, standard_deviation)

        elif signal and signal != Signals.CLOSE:
            self.currentpositions[symbol] = self.openPositionFromSignal(
                symbol, signal, client, cloud, newprice,
            )

    def updateFromAccountActivity(self, symbol, message_type, data):
        """
        handles new messages from the account activity stream
        like order fills or cancels
        """
        self.currentpositions[symbol].updateFromAccountActivity(
            message_type, data)

    def getContractFromChain(
        self, client, symbol, take_profit, stop, currentprice, cloudcolor
    ):
        """
        returns an appropriate options contract symbol
        should validate risk/reward with the philrate
        """
        putCall = None
        if cloudcolor == CloudColor.GREEN:
            putCall = "CALL"
        elif cloudcolor == CloudColor.RED:
            putCall = "PUT"

        expected_move_to_profit = abs(take_profit - currentprice)
        expected_move_to_stop = abs(stop - currentprice)
        contracts = getFlattenedChain(
            client, symbol, self.config.strike_count, self.config.maxdte + 1,
        )
        # contract validation
        contracts = [
            contract
            for contract in contracts
            if contract["ask"] - contract["bid"] <= self.config.max_spread
            and contract["putCall"] == putCall
            and contract["daysToExpiration"] >= mindte
            and contract["daysToExpiration"] <= maxdte
            and contract["ask"] > self.config.min_contract_price
            and contract["ask"] < self.config.max_contract_price
        ]

        # risk reward validation
        contracts = [
            contract
            for contract in contracts
            if abs(contract["delta"]) * expected_move_to_stop < self.config.max_loss
            and expected_move_to_profit / expected_move_to_stop > self.config.min_risk_reward_ratio
        ]

        # there can only be one
        highest_delta_contract = sorted(
            contracts, key=lambda contract: abs(contract["delta"])
        )
        return highest_delta_contract

    def openPositionFromSignal(
        self, symbol, signal, client, cloud, price,
    ):
        standard_dev = getStdDevForSymbol(
            client, symbol, self.config.stdev_period)

        stop, takeprofit = levelSet(price, standard_dev, cloud)
        stop_level = StopType.stopTupleToLevel(stop, cloud)

        contract = self.getContractFromChain(
            client, symbol, takeprofit, stop_level, price, cloud.status[0],
        )
        if not contract:
            print("No suitable contracts")
        limit = contract["ask"] + self.config.limit_padding

        self.currentpositions[symbol] = Position(
            contract["symbol"], takeprofit, stop, state_signal
        )
        self.currentpositions[symbol].open(client, account_id, limit)
