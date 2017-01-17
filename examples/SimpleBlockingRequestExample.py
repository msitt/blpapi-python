# SimpleBlockingRequestExample.py

import blpapi
from optparse import OptionParser


LAST_PRICE = blpapi.Name("LAST_PRICE")


class MyEventHandler(object):
    def processEvent(self, event, session):
        try:
            if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                for msg in event:
                    if msg.hasElement(LAST_PRICE):
                        field = msg.getElement(LAST_PRICE)
                        print field.name(), "=", field.getValueAsString()
            return True
        except Exception as e:
            print "Exception:", e
            return False


def parseCmdLine():
    parser = OptionParser(description="Retrieve reference data.")
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

    (options, args) = parser.parse_args()

    return options


def main():
    global options
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)

    print "Connecting to %s:%d" % (options.host, options.port)

    myEventHandler = MyEventHandler()
    # Create a Session
    session = blpapi.Session(sessionOptions, myEventHandler.processEvent)

    # Start a Session
    if not session.start():
        print "Failed to start session."
        return

    if not session.openService("//blp/mktdata"):
        print "Failed to open //blp/mktdata"
        return

    if not session.openService("//blp/refdata"):
        print "Failed to open //blp/refdata"
        return

    print "Subscribing to IBM US Equity"
    cid = blpapi.CorrelationId(1)
    subscriptions = blpapi.SubscriptionList()
    subscriptions.add("IBM US Equity", "LAST_PRICE", "", cid)
    session.subscribe(subscriptions)

    print "Requesting reference data IBM US Equity"
    refDataService = session.getService("//blp/refdata")
    request = refDataService.createRequest("ReferenceDataRequest")
    request.append("securities", "IBM US Equity")
    request.append("fields", "DS002")

    cid2 = blpapi.CorrelationId(2)
    eventQueue = blpapi.EventQueue()
    session.sendRequest(request, correlationId=cid2, eventQueue=eventQueue)

    try:
        # Process received events
        while(True):
            # We provide timeout to give the chance to Ctrl+C handling:
            ev = eventQueue.nextEvent(500)
            for msg in ev:
                print msg
            # Response completly received, so we could exit
            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        # Wait for enter key to exit application
        print "Press ENTER to quit"
        raw_input()
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print "SimpleBlockingRequestExample"
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
