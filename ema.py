"""
Module for calculating exponential moving averages.
Uses a list as input and assumes evenly spaced data.
"""
from enum import Enum


# takes a list and returns EMA
def exp_mov_avg(input_list, period, k=0):
    """
    Note: EMAs take more values than {period} values;
    if N is the total number of data points considered,
    N is typically greater than period, though
    the most recent period values are most heavily weighted.
    See:
    https://tlc.thinkorswim.com/center/reference/thinkScript/Functions/Tech-Analysis/ExpAverage
    I think thinkorswim typically uses data from beginning of day (for 1
    minute chart).
    """
    if len(input_list) == 1:
        # since EMA(t_1) = P_1
        return input_list.pop()
    if k == 0:
        # k is the smoothing coefficient, also called alpha
        k = 2 / (1 + period)  # constant 2/(period+1)

    current_price = input_list.pop()
    yesterday_ema = exp_mov_avg(input_list, period=period, k=k)  # EMA(t_{n-1})

    # below is the recursive formula for EMA
    return current_price * k + yesterday_ema * (1 - k)


class CloudColor(Enum):
    """Enum for color of EMA cloud"""
    RED, GREEN = range(2)


class CloudPriceLocation(Enum):
    """Location of the price relative to the cloud."""
    ABOVE, INSIDE, BELOW = range(3)


def determine_cloud_status(currentprice, short_ema, long_ema):
    """
    Determine the color of the cloud and the relative location of the
    current price to the cloud.
    """
    # determine color of cloud
    if short_ema >= long_ema:
        color = CloudColor.GREEN
    else:
        color = CloudColor.RED

    # determine location of cloud
    if currentprice > short_ema and currentprice > long_ema:
        location = CloudPriceLocation.ABOVE
    elif currentprice < short_ema and currentprice < long_ema:
        location = CloudPriceLocation.BELOW
    else:
        location = CloudPriceLocation.INSIDE

    return (color, location)


class Cloud:
    """
    A class to hold the values of the moving averages along with the
    status (color and relative price location) of the cloud.
    """

    def __init__(self, short_ema, long_ema, currentprice):
        """Store current EMA data and use price to determine the cloud status."""
        self.short_ema = short_ema
        self.long_ema = long_ema
        # self.status is in the form (CloudColor, CloudPriceLocation)
        self.status = determine_cloud_status(currentprice, short_ema, long_ema)

    def __eq__(self, other):
        """This will help indicate if there is a change in status or not"""
        return self.status == other.status

    def ema_cloud_status(self, currentprice):
        """
        To be called on initialization and when a new price is received.
        Returns the color of the cloud (green ie bullish if short_ema
        is above long_ema, red ie bearish otherwise)
        and the location of the price relative to the cloud
        """
        return determine_cloud_status(
            currentprice, self.short_ema, self.long_ema)


if __name__ == "__main__":
    pass
