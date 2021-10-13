from botutils import AccountActivityXMLParse


class MessageHandler:
    def __init__(self, fields=None):
        self.fields = fields or {
            "BID_PRICE",
            "ASK_PRICE",
            "key",
            "OPEN_PRICE",
            "CLOSE_PRICE",
            "HIGH_PRICE",
            "LOW_PRICE"}
        # desired fields from the stream, not relevant for account activity stream, that's handled elsewhere
        # {service: fields}
        self.last_messages = {symbol: {} for symbol in {"SPY"}}

    def handle(self, msg):
        service = msg["service"]
        newdatafor = []

        if service == "ACCOUNT_ACTIVITY":
            for content in msg["content"]:
                msg_type = content['MESSAGE_TYPE']
                msg_data = AccountActivityXMLParse().parse(msg["MESSAGE_DATA"])
                symbol = msg_data["Symbol"].split("_")[0]
                newdatafor.append(
                    ((symbol, msg_type, msg_data), "ACCOUNT_ACTIVITY"))
            return newdatafor

        # should be one content for each symbol
        for content in msg["content"]:
            symbol = content["key"]
            relevantdata = {
                field: content[field]
                for field in content
                if field in self.fields[service]
            }

            # dict update operator
            self.last_messages[symbol] |= relevantdata
            newdatafor.append((symbol, service))
        return newdatafor
