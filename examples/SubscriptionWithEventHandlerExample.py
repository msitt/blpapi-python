# SubscriptionWithEventHandlerExample.py

import blpapi
from optparse import OptionParser
import time


EXCEPTIONS = blpapi.Name("exceptions")
FIELD_ID = blpapi.Name("fieldId")
REASON = blpapi.Name("reason")
CATEGORY = blpapi.Name("category")
DESCRIPTION = blpapi.Name("description")


class SubscriptionEventHandler(object):
    def getTimeStamp(self):
        return time.strftime("%Y/%m/%d %X")

    def processSubscriptionStatus(self, event):
        timeStamp = self.getTimeStamp()
        print "Processing SUBSCRIPTION_STATUS"
        for msg in event:
            topic = msg.correlationIds()[0].value()
            print "%s: %s - %s" % (timeStamp, topic, msg.messageType())

            if msg.hasElement(REASON):
                # This can occur on SubscriptionFailure.
                reason = msg.getElement(REASON)
                print "        %s: %s" % (
                    reason.getElement(CATEGORY).getValueAsString(),
                    reason.getElement(DESCRIPTION).getValueAsString())

            if msg.hasElement(EXCEPTIONS):
                # This can occur on SubscriptionStarted if at least
                # one field is good while the rest are bad.
                exceptions = msg.getElement(EXCEPTIONS)
                for exInfo in exceptions.values():
                    fieldId = exInfo.getElement(FIELD_ID)
                    reason = exInfo.getElement(REASON)
                    print "        %s: %s" % (
                        fieldId.getValueAsString(),
                        reason.getElement(CATEGORY).getValueAsString())

    def processSubscriptionDataEvent(self, event):
        timeStamp = self.getTimeStamp()
        print
        print "Processing SUBSCRIPTION_DATA"
        for msg in event:
            topic = msg.correlationIds()[0].value()
            print "%s: %s - %s" % (timeStamp, topic, msg.messageType())
            for field in msg.asElement().elements():
                if field.numValues() < 1:
                    print "        %s is NULL" % field.name()
                    continue

                # Assume all values are scalar.
                print "        %s = %s" % (field.name(),
                                           field.getValueAsString())

    def processMiscEvents(self, event):
        timeStamp = self.getTimeStamp()
        for msg in event:
            print "%s: %s" % (timeStamp, msg.messageType())

    def processEvent(self, event, session):
        try:
            if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                return self.processSubscriptionDataEvent(event)
            elif event.eventType() == blpapi.Event.SUBSCRIPTION_STATUS:
                return self.processSubscriptionStatus(event)
            else:
                return self.processMiscEvents(event)
        except blpapi.Exception as e:
            print "Library Exception !!! %s" % e.description()
        return False


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
    parser.add_option("-t",
                      dest="topics",
                      help="topic name (default: IBM US Equity)",
                      metavar="topic",
                      action="append",
                      default=[])
    parser.add_option("-f",
                      dest="fields",
                      help="field to subscribe to (default: LAST_PRICE)",
                      metavar="field",
                      action="append",
                      default=[])
    parser.add_option("-o",
                      dest="options",
                      help="subscription options (default: empty)",
                      metavar="option",
                      default=[])

    (options, args) = parser.parse_args()

    if not options.topics:
        options.topics = ["IBM US Equity"]

    if not options.fields:
        options.fields = ["LAST_PRICE"]

    return options


def main():
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)

    print "Connecting to %s:%d" % (options.host, options.port)

    eventHandler = SubscriptionEventHandler()
    # Create a Session
    session = blpapi.Session(sessionOptions, eventHandler.processEvent)

    # Start a Session
    if not session.start():
        print "Failed to start session."
        return

    print "Connected successfully"

    service = "//blp/mktdata"
    if not session.openService(service):
        print "Failed to open %s service" % service
        return

    subscriptions = blpapi.SubscriptionList()
    for t in options.topics:
        topic = service
        if not t.startswith("/"):
            topic += "/"
        topic += t
        subscriptions.add(topic, options.fields, options.options,
                          blpapi.CorrelationId(t))

    print "Subscribing..."
    session.subscribe(subscriptions)

    try:
        # Wait for enter key to exit application
        print "Press ENTER to quit"
        raw_input()
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print "SubscriptionWithEventHandlerExample"
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
