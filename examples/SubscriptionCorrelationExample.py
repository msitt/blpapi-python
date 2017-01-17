# SubscriptionCorrelationExample.py

import blpapi
from optparse import OptionParser


class GridWindow(object):
    def __init__(self, name, securities):
        self.name = name
        self.securities = securities

    def processSecurityUpdate(self, msg, row):
        topicName = self.securities[row]
        print "%s:%s,%s" % (self.name, row, topicName)


def parseCmdLine():
    parser = OptionParser(description="Retrieve realtime data.")
    parser.add_option("-a",
                      "--ip",
                      dest="host",
                      help="server name or IP (default: %default)",
                      metavar="ipAddress",
                      default="localhost")
    parser.add_option("-p",
                      dest="port",
                      type="int",
                      help="server port (default: %default)",
                      metavar="tcpPort",
                      default=8194)
    parser.add_option("--me",
                      dest="maxEvents",
                      type="int",
                      help="stop after this many events (default: %default)",
                      metavar="maxEvents",
                      default=1000000)

    (options, args) = parser.parse_args()

    return options


def main():
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)

    print "Connecting to %s:%d" % (options.host, options.port)

    # Create a Session
    session = blpapi.Session(sessionOptions)

    # Start a Session
    if not session.start():
        print "Failed to start session."
        return

    if not session.openService("//blp/mktdata"):
        print "Failed to open //blp/mktdata"
        return

    securities = ["IBM US Equity", "VOD LN Equity"]
    gridWindow = GridWindow("SecurityInfo", securities)

    subscriptions = blpapi.SubscriptionList()
    for i, security in enumerate(securities):
        subscriptions.add(security,
                          "LAST_PRICE",
                          "",
                          blpapi.CorrelationId(i))

    session.subscribe(subscriptions)

    try:
        # Process received events
        eventCount = 0
        while(True):
            # We provide timeout to give the chance to Ctrl+C handling:
            event = session.nextEvent(500)
            if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                for msg in event:
                    row = msg.correlationIds()[0].value()
                    gridWindow.processSecurityUpdate(msg, row)

                eventCount += 1
                if eventCount >= options.maxEvents:
                    break
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print "SubscriptionCorrelationExample"
    try:
        main()
    except KeyboardInterrupt:
        print "Ctrl+C pressed. Stopping..."

__copyright__ = """
Copyright 2012. Bloomberg Finance L.P.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:  The above
copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
"""
