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

        if service == "ACCT_ACTIVITY":
            for content in msg["content"]:
                msg_type = content['MESSAGE_TYPE']
                if msg_type == "SUBSCRIBED":
                    continue
                msg_data = AccountActivityXMLParse().parse(
                    content["MESSAGE_DATA"])
                symbol = msg_data["Symbol"].split("_")[0]
                newdatafor.append(
                    ((symbol, msg_type, msg_data), "ACCT_ACTIVITY"))
                print(f"{symbol}:{msg_type}")
                [print(item) for item in msg_data.items()]
                print("-------------------------------------")
            return newdatafor

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
            newdatafor.append((symbol, service))

            print(f"New quote for {symbol}")
            [print(item) for item in relevantdata.items()]
            print("-------------------------------------")
        return newdatafor
