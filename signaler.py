"""
A class that wraps an ema.Cloud object and its relevant data.
Uses that information to emit signals (from the enum like OPEN, CLOSE)
which are then interpreted as buy/sell signals based on cloud status
and current positions.

Signals may or may not be followed up on based on stop/take profit
levels and availability of suitable contracts. These determinations
are irrelevant to this module.
"""

from enum import Enum

from ema import exp_mov_avg, Cloud, CloudColor, CloudPriceLocation
from botutils import get_history


class Signals(Enum):
    """The outputting of these signals is the primary purpose of this module."""
    OPEN, OPEN_OR_INCREASE, CLOSE, EXIT = range(4)


class Signaler:
    """
    A class for sending signals from the Signals enum,
    and to hold the relevant data and objects for
    determining what signals to send.
    """
    def __init__(
        self,
        client,
        symbol,
        short_ema_length,
        long_ema_length,
        timeframe_minutes,
    ):
        """
        Fields:
        short_ema_length
        long_ema_length
        historical
        first_chart_equity
        symbol
        cloud
        timeframe_minutes
        """
        history = get_history(client, symbol)[timeframe_minutes-1::timeframe_minutes]
        closevals = [candle["close"] for candle in history]

        self.short_ema_length = short_ema_length
        self.long_ema_length = long_ema_length

        short_ema = exp_mov_avg(closevals.copy(), short_ema_length)
        long_ema = exp_mov_avg(closevals.copy(), long_ema_length)
        currentprice = closevals[-1]

        # From completed candles, only change on new completed candle.
        self.historical = {"short": short_ema, "long": long_ema}

        # So as to ignore the first candle from the chart equity stream.
        # (ie. the current data which will have already been retrieved from get_history)
        # If not ignored would add redundant data to ema calculations.
        self.first_chart_equity = True

        self.symbol = symbol
        self.cloud = Cloud(short_ema, long_ema, currentprice)

        self.candle_counter = 0

    def update_cloud(self, new_price):
        """
        Update EMAs and cloud based on new data.
        To be called after recieving new quote.
        Called by update and returns 0 if cloud status is
        unchanged and (old_status, new_status) otherwise.
        """
        status = self.cloud.status
        self.cloud.short_ema = exp_mov_avg(
            [self.historical["short"], new_price], self.short_ema_length)
        self.cloud.long_ema = exp_mov_avg(
            [self.historical["long"], new_price], self.long_ema_length)

        new_status = self.cloud.ema_cloud_status(new_price)

        if new_status != status:
            self.cloud.status = new_status
            return (status, new_status)

        return 0

    def cloud_status_to_signal(self, status, new_status):
        """
        Input should come from the update function.
        Takes a change of status (old_status, new_status)
        and returns a signal from the Signal enum or 0.

        Returns Signals.CLOSE in event of cloud color change.
        Primarily intended for buy signals, stop losses and
        take profit levels are handled outside this module.
        """
        color, location = status
        new_color, new_location = new_status

        if color != new_color:
            # Exit any entered position on color change.
            return Signals.CLOSE

        if color == CloudColor.GREEN:
            # Bullish moves up.
            if (
                location == CloudPriceLocation.BELOW
                and new_location == CloudPriceLocation.INSIDE
            ):
                return Signals.OPEN
            if (
                location == CloudPriceLocation.INSIDE
                and new_location == CloudPriceLocation.ABOVE
            ):
                return Signals.OPEN_OR_INCREASE

            # Bearish moves down.
            if (
                location == CloudPriceLocation.ABOVE
                and new_location == CloudPriceLocation.INSIDE
            ):
                return 0
            if (
                location == CloudPriceLocation.INSIDE
                and new_location == CloudPriceLocation.BELOW
            ):
                return 0

        if color == CloudColor.RED:
            # Bullish moves up.
            if (
                location == CloudPriceLocation.BELOW
                and new_location == CloudPriceLocation.INSIDE
            ):
                return 0
            if (
                location == CloudPriceLocation.INSIDE
                and new_location == CloudPriceLocation.ABOVE
            ):
                return 0

            # Bearish moves down.
            if (
                location == CloudPriceLocation.ABOVE
                and new_location == CloudPriceLocation.INSIDE
            ):
                return Signals.OPEN
            if (
                location == CloudPriceLocation.INSIDE
                and new_location == CloudPriceLocation.BELOW
            ):
                return Signals.OPEN_OR_INCREASE

        # In case of confusion.
        return 0

    def update(self, service, data, ui):
        """
        Updates cloud and outputs signal if any (0 if none), and new_price.
        Wraps the other functions of this clss in the appropriate logic.

        Takes data output by the message handler and uses the new price
        to emit signals as output.

        I think the CLOSE_PRICE of the CHART_EQUITY stream can end up behind
        the most recent data given by the QUOTE stream. For this reason CLOSE_PRICE
        is not returned as a new_price.
        """
        if service == "QUOTE":
            try:
                new_price = data["LAST_PRICE"]
            except KeyError as _:
                return 0, None

        elif service == "CHART_EQUITY":

            # Check if this is the first message from the stream.
            # The first message should be ignored for sensible
            # EMA calculation.
            if self.first_chart_equity:
                self.first_chart_equity = False
                return 0, None

            candle_counter += 1
            if candle_counter < timeframe_minutes:
                return 0, None

            candle_counter = 0

            close_price = data["CLOSE_PRICE"]
            self.historical["short"] = exp_mov_avg(
                [self.historical["short"], close_price], self.short_ema_length)
            self.historical["long"] = exp_mov_avg(
                [self.historical["long"], close_price], self.long_ema_length)
            return 0, None

        status_update = self.update_cloud(new_price)
        if status_update:
            old_status, new_status = status_update
            signal = self.cloud_status_to_signal(old_status, new_status)
            ui.messages.append(f"New Signal for {self.symbol}: {signal}")
            return signal, new_price
        return 0, new_price
