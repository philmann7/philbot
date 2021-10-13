from enum import Enum


# takes a list and returns EMA
def expMovAvg(input_list, period, k=0):
    # Note: EMAs take more values than period values
    # if N is the total number of data points considered,
    # N is typically greater than period, though
    # the most recent period values are most heavily weighted
    # see:
    # https://tlc.thinkorswim.com/center/reference/thinkScript/Functions/Tech-Analysis/ExpAverage
    # i think thinkorswim typically uses data from beginning of day (for 1
    # minute chart)

    if len(input_list) == 1:
        return input_list.pop()
        # since EMA(t_1) = P_1
    if k == 0:
        k = 2 / (1 + period)  # constant 2/(period+1)
        # k is the smoothing coefficient, also called alpha

    current_price = input_list.pop()
    yesterday_ema = expMovAvg(input_list, period=period, k=k)  # EMA(t_{n-1})

    # below is the recursive formula for EMA
    return current_price * k + yesterday_ema * (1 - k)


class CloudColor(Enum):
    RED, GREEN = range(2)


class CloudPriceLocation(Enum):
    # location of the price relative to the cloud
    # for example ABOVE means the price is above the cloud
    ABOVE, INSIDE, BELOW = range(3)


def determine_cloud_status(currentprice, shortEMA, longEMA):
    # determine color of cloud
    if shortEMA >= longEMA:
        color = CloudColor.GREEN
    else:
        color = CloudColor.RED
    # determine location of cloud
    if currentprice > shortEMA and currentprice > longEMA:
        location = CloudPriceLocation.ABOVE
    if currentprice < shortEMA and currentprice < longEMA:
        location = CloudPriceLocation.BELOW
    else:
        location = CloudPriceLocation.INSIDE

    return (color, location)


class Cloud:
    def __init__(self, shortEMA, longEMA, currentprice):
        self.shortEMA = shortEMA
        self.longEMA = longEMA
        # self.status is in the form (CloudColor, CloudPriceLocation)
        self.status = determine_cloud_status(currentprice, shortEMA, longEMA)

    # this will help indicate if there is a change in status or not
    def __eq__(self, other):
        return self.status == other.status

    # to be called on initialization and when a new price is received
    # returns the color of the cloud (green ie bullish if shortEMA
    # is above longEMA, red ie bearish otherwise)
    # and the location of the price relative to the cloud
    def ema_cloud_status(self, currentprice):
        return determine_cloud_status(
            currentprice, self.shortEMA, self.longEMA)


if __name__ == "__main__":
    pass
