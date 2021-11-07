"""
Module to parse messages from the TD Ameritrade API
and store some of the most recent data.
Stores price data for example, so even if no new price data
was received from the last message in the stream, the most recent
data will still be available.
"""
from botutils import AccountActivityXMLParse


class MessageHandler:
    """
    For handling messages and their data received from TD Ameritrade.

    The class uses methods to return a list, new_data_for, containing tuples.
    The second item of the tuples in new_data_for is the service name.

    If the message is from account activity the data is returned in the
    first element of the tuple. Otherwise the relevant data is saved
    and the first element of the returned tuples is simply the symbol
    for which there is new data.
    """
    def __init__(self, fields=None, symbols=None):
        """"A default list of fields and symbols is available."""

        # Desired fields from the stream;
        # not relevant for account activity stream, that's handled elsewhere.
        self.fields = fields or {
            "BID_PRICE",
            "LAST_PRICE",
            "ASK_PRICE",
            "key",
            "OPEN_PRICE",
            "CLOSE_PRICE",
            "HIGH_PRICE",
            "LOW_PRICE"}

        symbols = symbols or {"SPY"}
        # symbol: {service: fields}
        self.last_messages = {symbol: {} for symbol in symbols}

    def handle(self, msg):
        """Catch-all function for handling messages from TD Ameritrade."""
        service = msg["service"]
        new_data_for = []

        if service == "ACCT_ACTIVITY":
            for content in msg["content"]:
                msg_type = content['MESSAGE_TYPE']
                if msg_type == "SUBSCRIBED":
                    continue
                msg_data = AccountActivityXMLParse().parse(
                    content["MESSAGE_DATA"])
                # Because msg_data["Symbol"] is the contract symbol:
                symbol = msg_data["Symbol"].split("_")[0]
                new_data_for.append(
                    ((symbol, msg_type, msg_data), "ACCT_ACTIVITY"))
            return new_data_for

        # should be one content for each symbol
        for content in msg["content"]:
            symbol = content["key"]
            relevantdata = {
                field: content[field]
                for field in content
                if field in self.fields
            }

            # dict update operator
            self.last_messages[symbol] |= relevantdata
            new_data_for.append((symbol, service))

        return new_data_for
