# puts out buy (open) signals
# except for cloud color change
# take profits and stop losses will
# be calculated elsewhere

from enum import Enum
import asyncio

from ema import expMovAvg, Cloud, CloudColor, CloudPriceLocation
from botutils import gethistory


class Signals(Enum):
    OPEN, OPEN_OR_INCREASE, CLOSE = range(3)


class Signaler:
    def __init__(
        self,
        client,
        symbol,
        shortEMAlength,
        longEMAlength,
    ):
        history = gethistory(client, symbol)
        closevals = [candle["close"] for candle in history]

        self.shortEMAlength = shortEMAlength
        self.longEMAlength = longEMAlength

        shortEMA = expMovAvg(closevals.copy(), shortEMAlength)
        longEMA = expMovAvg(closevals.copy(), longEMAlength)
        currentprice = closevals[-1]

        # from completed candles, only change on new completed candle
        self.historical = {"short": shortEMA, "long": longEMA}
        self.first_chart_equity = True  # so as to ignore the first
        # candle from the chart equity stream.
        # if not ignored would add redundant data to ema calculations
        # since the close of the current candle should be covered by gethistory
        self.symbol = symbol
        self.cloud = Cloud(shortEMA, longEMA, currentprice)

    def updateCloud(self, service, newprice):
        """
        Update EMAs and cloud based on new data.
        To be called after recieving new quote.
        Called by update and passes 0 if cloud status is
        unchanged and (oldstatus, newstatus) otherwise

        A lot of this could likely be moved inside the
        cloud class.
        """
        status = self.cloud.status
        self.cloud.shortEMA = expMovAvg(
            [self.historical["short"], newprice], self.shortEMAlength)
        self.cloud.longEMA = expMovAvg(
            [self.historical["long"], newprice], self.longEMAlength)

        newstatus = self.cloud.ema_cloud_status(newprice)
        self.cloud.status = newstatus

        if newstatus != status:
            return (status, newstatus)
        else:
            return 0

    def cloudStatusToSignal(self, status, newstatus):
        """
        Input should come from the update function
        Takes a change of status (oldstatus, newstatus)
        and returns a signal from the Signal enum or 0.
        Returns Signals.CLOSE in event of cloud color change
        """
        color, location = status
        newcolor, newlocation = newstatus

        if color != newcolor:
            # exit any entered position on color change
            return Signals.CLOSE

        if color == CloudColor.GREEN:
            # bullish moves up
            if (
                location == CloudPriceLocation.BELOW
                and newlocation == CloudPriceLocation.INSIDE
            ):
                return Signals.OPEN
            if (
                location == CloudPriceLocation.INSIDE
                and newlocation == CloudPriceLocation.ABOVE
            ):
                return Signals.OPEN_OR_INCREASE

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
                return 0

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
                return 0

            # bearish moves down
            if (
                location == CloudPriceLocation.ABOVE
                and newlocation == CloudPriceLocation.INSIDE
            ):
                return Signals.OPEN
            if (
                location == CloudPriceLocation.INSIDE
                and newlocation == CloudPriceLocation.BELOW
            ):
                return Signals.OPEN_OR_INCREASE

        # in case of confusion
        return 0

    def update(self, service, data,):
        """
        updates cloud and outputs signal if any, and newprice
        """
        if service == "QUOTE":
            try:
                newprice = data["LAST_PRICE"]
                print(f"New Quote: {newprice}")
            except KeyError as e:
                print(f"No new price from quote stream: {e}")
                print("-----------------------------------")
                return 0, None

        elif service == "CHART_EQUITY":
            if self.first_chart_equity:
                self.first_chart_equity = False
                return 0, None
            close_price = data["CLOSE_PRICE"]
            self.historical["short"] = expMovAvg(
                [self.historical["short"], close_price], self.shortEMAlength)
            self.historical["long"] = expMovAvg(
                [self.historical["long"], close_price], self.longEMAlength)
            return 0, None

        status_update = self.updateCloud(service, newprice,)
        if status_update:
            oldstatus, newstatus = status_update
            return self.cloudStatusToSignal(oldstatus, newstatus), newprice
        return 0, newprice
