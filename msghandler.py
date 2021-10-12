class MessageHandler:
    def __init__(self, fields=None):
        self.fields = fields or {"BID_PRICE", "ASK_PRICE", "key", "OPEN_PRICE", "CLOSE_PRICE", "HIGH_PRICE", "LOW_PRICE"}
        # desired fields from the stream, not relevant for account activity stream, that's handled elsewhere
        # {service: fields}
        self.last_messages = {service: {} for service in fields}  # dict
        # keys will be the 'service' ie QUOTE or CHART_EQUITY

    def handle(self, msg):
        service = msg["service"]
        newdatafor = []

        if service == "ACCOUNT_ACTIVITY":
            return [(content, "ACCOUNT_ACTIVITY")
                    for content in msg["content"]]

        # should be one content for each symbol
        for content in msg["content"]:
            symbol = content["key"]
            relevantdata = {
                field: content[field]
                for field in content
                if field in self.fields[service]
            }

            # dict update operator
            self.last_messages[service][symbol] |= relevantdata
            newdatafor.append((symbol, service))
        return newdatafor
