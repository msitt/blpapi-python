# IntradayTickExample.py

import blpapi
import copy
import datetime
from optparse import OptionParser, Option, OptionValueError


TICK_DATA = blpapi.Name("tickData")
COND_CODE = blpapi.Name("conditionCodes")
TICK_SIZE = blpapi.Name("size")
TIME = blpapi.Name("time")
TYPE = blpapi.Name("type")
VALUE = blpapi.Name("value")
RESPONSE_ERROR = blpapi.Name("responseError")
CATEGORY = blpapi.Name("category")
MESSAGE = blpapi.Name("message")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")


def checkDateTime(option, opt, value):
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as ex:
        raise OptionValueError(
            "option {0}: invalid datetime value: {1} ({2})".format(
                opt, value, ex))


class ExampleOption(Option):
    TYPES = Option.TYPES + ("datetime",)
    TYPE_CHECKER = copy.copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["datetime"] = checkDateTime


def parseCmdLine():
    parser = OptionParser(description="Retrieve intraday rawticks.",
                          epilog="Notes: " +
                          "1) All times are in GMT. " +
                          "2) Only one security can be specified.",
                          option_class=ExampleOption)
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
    parser.add_option("-s",
                      dest="security",
                      help="security (default: %default)",
                      metavar="security",
                      default="IBM US Equity")
    parser.add_option("-e",
                      dest="events",
                      help="events (default: TRADE)",
                      metavar="event",
                      action="append",
                      default=[])
    parser.add_option("--sd",
                      dest="startDateTime",
                      type="datetime",
                      help="start date/time (default: %default)",
                      metavar="startDateTime",
                      default=datetime.datetime(2008, 8, 11, 15, 30, 0))
    parser.add_option("--ed",
                      dest="endDateTime",
                      type="datetime",
                      help="end date/time (default: %default)",
                      metavar="endDateTime",
                      default=datetime.datetime(2008, 8, 11, 15, 35, 0))
    parser.add_option("--cc",
                      dest="conditionCodes",
                      help="include condition codes",
                      action="store_true",
                      default=False)

    (options, args) = parser.parse_args()

    if not options.events:
        options.events = ["TRADE"]

    return options


def printErrorInfo(leadingStr, errorInfo):
    print "%s%s (%s)" % (leadingStr, errorInfo.getElementAsString(CATEGORY),
                         errorInfo.getElementAsString(MESSAGE))


def processMessage(msg):
    data = msg.getElement(TICK_DATA).getElement(TICK_DATA)
    print "TIME\t\t\t\tTYPE\tVALUE\t\tSIZE\tCC"
    print "----\t\t\t\t----\t-----\t\t----\t--"

    for item in data.values():
        time = item.getElementAsDatetime(TIME)
        timeString = item.getElementAsString(TIME)
        type = item.getElementAsString(TYPE)
        value = item.getElementAsFloat(VALUE)
        size = item.getElementAsInteger(TICK_SIZE)
        if item.hasElement(COND_CODE):
            cc = item.getElementAsString(COND_CODE)
        else:
            cc = ""

        print "%s\t%s\t%.3f\t\t%d\t%s" % (timeString, type, value, size, cc)


def processResponseEvent(event):
    for msg in event:
        print msg
        if msg.hasElement(RESPONSE_ERROR):
            printErrorInfo("REQUEST FAILED: ", msg.getElement(RESPONSE_ERROR))
            continue
        processMessage(msg)


def sendIntradayTickRequest(session, options):
    refDataService = session.getService("//blp/refdata")
    request = refDataService.createRequest("IntradayTickRequest")

    # only one security/eventType per request
    request.set("security", options.security)

    # Add fields to request
    eventTypes = request.getElement("eventTypes")
    for event in options.events:
        eventTypes.appendValue(event)

    # All times are in GMT
    if not options.startDateTime or not options.endDateTime:
        tradedOn = getPreviousTradingDate()
        if tradedOn:
            startTime = datetime.datetime.combine(tradedOn,
                                                  datetime.time(15, 30))
            request.set("startDateTime", startTime)
            endTime = datetime.datetime.combine(tradedOn,
                                                datetime.time(15, 35))
            request.set("endDateTime", endTime)
    else:
        if options.startDateTime and options.endDateTime:
            request.set("startDateTime", options.startDateTime)
            request.set("endDateTime", options.endDateTime)

    if options.conditionCodes:
        request.set("includeConditionCodes", True)

    print "Sending Request:", request
    session.sendRequest(request)


def eventLoop(session):
    done = False
    while not done:
        # nextEvent() method below is called with a timeout to let
        # the program catch Ctrl-C between arrivals of new events
        event = session.nextEvent(500)
        if event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
            print "Processing Partial Response"
            processResponseEvent(event)
        elif event.eventType() == blpapi.Event.RESPONSE:
            print "Processing Response"
            processResponseEvent(event)
            done = True
        else:
            for msg in event:
                if event.eventType() == blpapi.Event.SESSION_STATUS:
                    if msg.messageType() == SESSION_TERMINATED:
                        done = True


def getPreviousTradingDate():
    tradedOn = datetime.date.today()

    while True:
        try:
            tradedOn -= datetime.timedelta(days=1)
        except OverflowError:
            return None

        if tradedOn.weekday() not in [5, 6]:
            return tradedOn


def main():
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)

    print "Connecting to %s:%s" % (options.host, options.port)
    # Create a Session
    session = blpapi.Session(sessionOptions)

    # Start a Session
    if not session.start():
        print "Failed to start session."
        return

    try:
        # Open service to get historical data from
        if not session.openService("//blp/refdata"):
            print "Failed to open //blp/refdata"
            return

        sendIntradayTickRequest(session, options)

        # wait for events from session.
        eventLoop(session)

    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print "IntradayTickExample"
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
