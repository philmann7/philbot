# tracks and manages positions
# sends orders
# moves stoploss to take profits
# https://tda-api.readthedocs.io/en/latest/client.html#orders
from signaler import Signals
from ema import CloudColor, CloudPriceLocation

from enum import Enum


class PositionState(Enum):
    OPEN, TRAIL_STOP = range(2)


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

    stopmod = 1
    takeprofitmod = 2

    directionmod = 1
    if cloudcolor == CloudColor.RED:
        directionmod = -1

    takeprofitmod = takeprofitmod * directionmod
    stopmod = stopmod * directionmod

    takeprofit = cloud.shortEMA + (standard_deviation * takeprofitmod)

    if cloudlocation == CloudPriceLocation.INSIDE:
        stop = cloud.longEMA - (standard_deviation * stopmod)

    if (
        cloudlocation == CloudPriceLocation.ABOVE
        or cloudlocation == CloudPriceLocation.BELOW
    ):
        stop = min(cloud.longEMA, currentprice - (directionmod * standard_deviation))

    return stop, takeprofit


class LevelSetter:
    """
    holds levelsetter settings
    """

    pass


class OrderManagerConfig:
    def __init__(self,):
        pass


class Position:
    def __init__(self, contract, limit, takeprofit, stop, opened_on):
        self.contract = contract  # contract symbol
        self.opened_on = opened_on  # signaler.Signals.OPEN or OPEN_OR_INCREASE
        self.netpos = 0
        self.associated_orders = {}  # id:status

        self.state = None  # PositionState
        self.stop = stop
        self.takeprofit = takeprofit

    # possibly move these into order manager
    def open():
        pass

    def close():
        pass

    def increase():
        pass


class OrderManager:
    def __init__(
        self, config,
    ):
        self.config = config  # class OrderManagerConfig
        self.currentpositions = {}  # symbol:Position

    def update(self, symbol, signal, newprice):
        """
        update parameter is the output of
        signaler.update so update should be Signals.something
        or 0
        """
        pass

    def getContractFromChain():
        """
        returns an appropriate options contract symbol
        """
        pass

    def open():
        pass

    def close():
        pass

    def increase():
        pass
