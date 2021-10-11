# tracks and manages positions
# sends orders
# moves stoploss to take profits
# https://tda-api.readthedocs.io/en/latest/client.html#orders
from signaler import Signals
from ema import CloudColor, CloudPriceLocation
from botutils import getStdDevForSymbol, getFlattenedChain

from enum import Enum


class StopType(Enum):
    EMALong, EMAShort = range(2)

    @classmethod
    def stopTypeToLevel(enm, stoptype, cloud):
        """
        gets a number from the type of stop (ie EMALong etc.)
        """
        match stoptype:
            case enm.EMAShort:
                return cloud.shortEMA
            case enm.EMALong:
                return cloud.longEMA
            case other:
                return other

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

    if cloudlocation == CloudPriceLocation.INSIDE:  # ie passing through long ema
        stop = (StopType.EMALong, (standard_deviation * stopmod * -1))

    if (
        cloudlocation == CloudPriceLocation.ABOVE
        or cloudlocation == CloudPriceLocation.BELOW # ie passing through short ema
    ):
        stop = (StopType.EMALong, 0)
        # or in case the long EMA is very far away
        if abs(cloud.longEMA - currentprice) > abs(currentprice - (cloud.shortEMA - (directionmod * 2 * standard_deviation))):
            stop = (StopType.EMAShort, (directionmod * 2 * standard_deviation))

    takeprofit = cloud.shortEMA + (standard_deviation * takeprofitmod)

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
    """
    Controls and tracks an options position
    """

    def __init__(self, contract, limit, takeprofit, stop, opened_on):
        self.contract = contract  # contract symbol
        self.opened_on = opened_on  # signaler.Signals.OPEN or OPEN_OR_INCREASE
        # if opened on OPEN_OR_INCREASE only allow position size 1

        self.netpos = 0
        self.associated_orders = {}  # id:status

        self.state = None  # PositionState
        self.stop = stop  # (StopType, offset)
        self.takeprofit = takeprofit


    # possibly move these into order manager
    # an initializer. for adding to a position use updatePositionFromQuote
    def open(
        self, client,
    ):
        """
        For opening a position on the first valid buy signal.

        This method should not be used to add to a position, for
        that use updatePositionFromQuote and increase.
        """
        pass

    def close():
        pass

    def increase():
        self.opened_on = Signals.OPEN_OR_INCREASE

    def updatePositionFromQuote(self, cloud, signal, price):
        """
        Handles stop loss, take profit and adding to a position.
        Opening a position and closing for other reasons
        are handled elsewhere.
        """
        if signal == Signals.OPEN_OR_INCREASE and self.opened_on == Signals.OPEN:
            return self.increase()

        stop_type, stop_offset = self.stop
        stop_level = stopTypeToLevel(stop_type, cloud)
        if price < stop_level + stop_offset:
            return self.close()

        if price > self.takeprofit + (philrate * 0.25):
            self.stop = (self.takeprofit, 0)
            self.takeprofit = self.takeprofit + (philrate * 0.5)

    def updateFromAccountActivity():
        """
        Handles order status updates like order fills or UROUT messages
        """
        pass


class OrderManager:
    def __init__(
        self, config,
    ):
        self.config = config  # class OrderManagerConfig
        self.currentpositions = {}  # symbol:Position

    def updateFromQuote(self, client, cloud, symbol, signal, newprice):
        """
        update parameter is the output of
        signaler.update so update should be Signals.something
        or 0
        """
        # this will be a cloud color change
        if signal == Signals.CLOSE and symbol in self.currentpositions:
            self.currentpositions[symbol].close()
        elif symbol in self.currentpositions:
            self.currentpositions[symbol].updatePositionFromQuote(signal, newprice)
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
            and contract["putCall"] == putorcall
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

        contract = getContractFromChain(
            symbol, price, stop, takeprofit, standard_dev, cloud.status[0]
        )
        limit = contract["ask"] + self.config.limit_padding

        self.open(
            symbol, contract, limit, takeprofit, stop, signal,
        )
