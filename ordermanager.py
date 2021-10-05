# tracks and manages positions
# sends orders
# moves stoploss to take profits
# https://tda-api.readthedocs.io/en/latest/client.html#orders
from signaler import Signals
from ema import CloudColor, CloudPriceLocation
from botutils import getStdDevForSymbol, getFlattenedChain

from enum import Enum


class PositionState(Enum):
    OPEN, TRAIL_STOP = range(2)


# possibly turn this into class to store values like multipliers
def levelSet(
    currentprice, standard_deviation, cloud,
):
    """
    calculates risk and reward levels.
    should return a stop loss and take profit levels
    for opening a new position
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

    if cloudlocation == CloudPriceLocation.INSIDE:
        stop = cloud.longEMA - (standard_deviation * stopmod)

    if (
        cloudlocation == CloudPriceLocation.ABOVE
        or cloudlocation == CloudPriceLocation.BELOW
    ):
        # this is in case the long EMA is very far away
        stop = min(
            cloud.longEMA, cloud.shortEMA - (directionmod * 2 * standard_deviation)
        )

    takeprofit = max(
        cloud.shortEMA + (standard_deviation * takeprofitmod),
        2 * abs(currentprice - stop),
    )

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
    ):
        self.stdev_period = (
            stdev_period  # period of calculation of the standard deviation
        )
        self.mindte = mindte  # days to expiration on the options contracts
        self.maxdte = maxdte
        self.max_contract_price = max_contract_price
        self.min_contract_price = min_contract_price
        self.max_spread = max_spread  # bid/ask spread
        self.max_loss = max_loss  # on price of contract so use option pricing convention ie .10 for 10 dollars
        self.min_risk_reward_ratio = min_risk_reward_ratio  # profit/loss expected_move_to_profit/expected_move_to_stop
        self.strike_count = strike_count  # number of strikes to ask the API for
        self.limit_padding = limit_padding  # if set to 0.01 the limit buy will
        # be set at ask+.01


class Position:
    def __init__(self, contract, limit, takeprofit, stop, opened_on):
        self.contract = contract  # contract symbol
        self.opened_on = opened_on  # signaler.Signals.OPEN or OPEN_OR_INCREASE
        # if opened on OPEN_OR_INCREASE only allow position size 1

        self.netpos = 0
        self.associated_orders = {}  # id:status

        self.state = None  # PositionState
        self.stop = stop
        self.takeprofit = takeprofit

    # possibly move these into order manager
    def open(
        self, client,
    ):
        pass

    def close():
        pass

    def increase():
        pass

    def updatePosition():
        # be sure to update stop with new ema or new ema+offset or whatever
        pass


class OrderManager:
    def __init__(
        self, config,
    ):
        self.config = config  # class OrderManagerConfig
        self.currentpositions = {}  # symbol:Position

    def update(self, client, symbol, signal, newprice):
        """
        update parameter is the output of
        signaler.update so update should be Signals.something
        or 0
        """
        # this will be a cloud color change
        if signal == Signals.CLOSE and symbol in self.currentpositions:
            self.currentpositions[symbol].close()
        elif symbol in self.currentpositions:
            self.currentpositions[symbol].updatePosition(signal, newprice)
        elif signal and signal != Signals.CLOSE:
            self.currentpositions[symbol] = self.openPositionFromSignal(
                symbol, signal, client, cloud
            )

    def updateFromAccountActivity():
        """
        handles new messages from the account activity stream
        like order fills or cancels
        """
        pass

    def getContractFromChain(
        self, client, symbol, take_profit, stop, currentprice,
    ):
        """
        returns an appropriate options contract symbol
        should validate risk/reward with the philrate
        """
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
        ]

        # there can only be one
        highest_delta_contract = sorted(
            contracts, key=lambda contract: abs(contract["delta"])
        )
        return highest_delta_contract

    def open(
        self, symbol, contract, limit, takeprofit, stop, opened_on_signal,
    ):
        self.currentpositions[symbol] = Position(
            contract, limit, takeprofit, stop, opened_on_signal
        )
        self.currentpositions[symbol].open()

    def close():
        pass

    def increase():
        pass

    def openPositionFromSignal(
        self, symbol, signal, client, cloud, price,
    ):
        period = 50
        standard_dev = getStdDevForSymbol(client, symbol, period)

        stop, takeprofit = levelSet(price, standard_dev, cloud)

        contract = getContractFromChain(symbol, price, stop, takeprofit, standard_dev,)
        limit = contract["ask"] + self.config.limit_padding

        self.open(
            symbol, contract, limit, takeprofit, stop, signal,
        )
