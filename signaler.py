from enum import Enum
import asyncio

from ema import expMovAvg, Cloud, CloudColor, CloudPriceLocation
from botutils import gethistory


class Signals(Enum):
    BUY_TO_OPEN = "BUY_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"
    EXIT = "EXIT"


class Signaler:
    def __init__(
        self, client, symbol, history,
    ):
        history = history
        closevals = [candle["close"] for candle in history]

        shortEMA = expMovAvg(closevals.copy(), 9)
        longEMA = expMovAvg(closevals.copy(), 21)
        currentprice = closevals[-1]

        # from completed candles, only change on new completed candle
        self.historical = {"short": shortEMA, "long": longEMA}
        self.symbol = symbol
        self.cloud = Cloud(shortEMA, longEMA, currentprice)

    def updateCloud(self, service, newprice):
        """
        Update EMAs and cloud based on new data.
        Called by update and passes 0 if cloud status is
        unchanged and (oldstatus, newstatus) otherwise

        A lot of this could likely be moved inside the
        cloud class.
        """
        status = self.cloud.status
        self.cloud.shortEMA = expMovAvg([self.historical["short"], newprice])
        self.cloud.longEMA = expMovAvg([self.historical["long"], newprice])

        if service == "CHART_EQUITY":
            self.historical["short"] = self.cloud.shortEMA
            self.historical["long"] = self.cloud.longEMA

        newstatus = self.cloud.ema_cloud_status(newprice)
        self.cloud.status = newstatus

        if newstatus != status:
            return (status, newstatus)
        else:
            return 0

    def update(self, service, data):
        """
        This updates the cloud values based on new data.
        Takes data from msghandler as input.
        Returns 0 if no change in cloud status
        or (oldstatus, newstatus) otherwise.
        Also returns the most recent price.
        to be passed to cloudStatusToSignal
        """
        if service == "QUOTE":
            newprice = data["LAST_PRICE"]
        if service == "CHART_EQUITY":
            newprice = data["CLOSE_PRICE"]
        return self.updateCloud(newprice), newprice

    def cloudStatusToSignal(status, newstatus):
        """
        Input should come from the update function
        Takes a change of status (oldstatus, newstatus)
        and returns a signal from the Signal enum.
        Returns Signals.EXIT in event of cloud color change
        or in case of any undefined changes.
        """
        color, location = status
        newcolor, newlocation = newstatus

        if color != newcolor:
            # exit any entered position on color change
            return Signals.EXIT

        if color == CloudColor.GREEN:
            # bullish moves up
            if (
                location == CloudPriceLocation.BELOW
                and newlocation == CloudPriceLocation.INSIDE
            ):
                return Signals.BUY_TO_OPEN
            if (
                location == CloudPriceLocation.INSIDE
                and newlocation == CloudPriceLocation.ABOVE
            ):
                return Signals.BUY_TO_OPEN

            # bearish moves down
            if (
                location == CloudPriceLocation.ABOVE
                and newlocation == CloudPriceLocation.INSIDE
            ):
                return 0
            if (
                location == CloudPriceLocation.INSIDE
                and newlocation == CloudPriceLocation.BELOW
            ):
                return Signals.SELL_TO_CLOSE

        if color == CloudColor.RED:
            # bullish moves up
            if (
                location == CloudPriceLocation.BELOW
                and newlocation == CloudPriceLocation.INSIDE
            ):
                return 0
            if (
                location == CloudPriceLocation.INSIDE
                and newlocation == CloudPriceLocation.ABOVE
            ):
                return Signals.BUY_TO_CLOSE

            # bearish moves down
            if (
                location == CloudPriceLocation.ABOVE
                and newlocation == CloudPriceLocation.INSIDE
            ):
                return Signals.SELL_TO_OPEN
            if (
                location == CloudPriceLocation.INSIDE
                and newlocation == CloudPriceLocation.BELOW
            ):
                return Signals.SELL_TO_OPEN

        # in case of confusion
        return Signals.EXIT
