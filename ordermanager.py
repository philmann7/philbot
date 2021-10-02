# tracks and manages positions
# sends orders
# moves stoploss to take profits
# https://tda-api.readthedocs.io/en/latest/client.html#orders
from signaler import Signals

class Position:
    def __init__(self, contract):
        self.contract = contract
        self.netpos = 0
        self.associated_orders = {} # id:status
        self.stop = None

class OrderManager:
    def __init__(self):
        self.currentpositions = {} # symbol:Position

    def update(self, symbol, signal, newprice):
    """
    update parameter is the output of
    signaler.update if it didn't return 0.
    so update should be Signals.something
    """
        pass
