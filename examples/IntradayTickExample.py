# IntradayTickExample.py
from __future__ import print_function
from __future__ import absolute_import

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
TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")
AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
TOKEN = blpapi.Name("token")

def authOptionCallback(option, opt, value, parser):
    vals = value.split('=', 1)

    if value == "user":
        parser.values.auth = "AuthenticationType=OS_LOGON"
    elif value == "none":
        parser.values.auth = None
    elif vals[0] == "app" and len(vals) == 2:
        parser.values.auth = "AuthenticationMode=APPLICATION_ONLY;"\
            "ApplicationAuthenticationType=APPNAME_AND_KEY;"\
            "ApplicationName=" + vals[1]
    elif vals[0] == "userapp" and len(vals) == 2:
        parser.values.auth = "AuthenticationMode=USER_AND_APPLICATION;"\
            "AuthenticationType=OS_LOGON;"\
            "ApplicationAuthenticationType=APPNAME_AND_KEY;"\
            "ApplicationName=" + vals[1]
    elif vals[0] == "dir" and len(vals) == 2:
        parser.values.auth = "AuthenticationType=DIRECTORY_SERVICE;"\
            "DirSvcPropertyName=" + vals[1]
    else:
        raise OptionValueError("Invalid auth option '%s'" % value)


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
                      default=None)
    parser.add_option("--ed",
                      dest="endDateTime",
                      type="datetime",
                      help="end date/time (default: %default)",
                      metavar="endDateTime",
                      default=None)
    parser.add_option("--cc",
                      dest="conditionCodes",
                      help="include condition codes",
                      action="store_true",
                      default=False)
    parser.add_option("--auth",
                      dest="auth",
                      help="authentication option: "
                      "user|none|app=<app>|userapp=<app>|dir=<property>"
                      " (default: %default)",
                      metavar="option",
                      action="callback",
                      callback=authOptionCallback,
                      type="string",
                      default="user")

    (options, args) = parser.parse_args()

    if not options.host:
        options.host = ["localhost"]

    if not options.events:
        options.events = ["TRADE"]

    return options

def authorize(authService, identity, session, cid):
    tokenEventQueue = blpapi.EventQueue()

    session.generateToken(eventQueue=tokenEventQueue)

    # Process related response
    ev = tokenEventQueue.nextEvent()
    token = None
    if ev.eventType() == blpapi.Event.TOKEN_STATUS or \
            ev.eventType() == blpapi.Event.REQUEST_STATUS:
        for msg in ev:
            print(msg)
            if msg.messageType() == TOKEN_SUCCESS:
                token = msg.getElementAsString(TOKEN)
            elif msg.messageType() == TOKEN_FAILURE:
                break

    if not token:
        print("Failed to get token")
        return False

    # Create and fill the authorization request
    authRequest = authService.createAuthorizationRequest()
    authRequest.set(TOKEN, token)

    # Send authorization request to "fill" the Identity
    session.sendAuthorizationRequest(authRequest, identity, cid)

    # Process related responses
    startTime = datetime.datetime.today()
    WAIT_TIME_SECONDS = 10
    while True:
        event = session.nextEvent(WAIT_TIME_SECONDS * 1000)
        if event.eventType() == blpapi.Event.RESPONSE or \
            event.eventType() == blpapi.Event.REQUEST_STATUS or \
                event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
            for msg in event:
                print(msg)
                if msg.messageType() == AUTHORIZATION_SUCCESS:
                    return True
                print("Authorization failed")
                return False

        endTime = datetime.datetime.today()
        if endTime - startTime > datetime.timedelta(seconds=WAIT_TIME_SECONDS):
            return False


def printErrorInfo(leadingStr, errorInfo):
    print("%s%s (%s)" % (leadingStr, errorInfo.getElementAsString(CATEGORY),
                         errorInfo.getElementAsString(MESSAGE)))


def processMessage(msg):
    data = msg.getElement(TICK_DATA).getElement(TICK_DATA)
    print("TIME\t\t\t\tTYPE\tVALUE\t\tSIZE\tCC")
    print("----\t\t\t\t----\t-----\t\t----\t--")

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

        print("%s\t%s\t%.3f\t\t%d\t%s" % (timeString, type, value, size, cc))


def processResponseEvent(event):
    for msg in event:
        print(msg)
        if msg.hasElement(RESPONSE_ERROR):
            printErrorInfo("REQUEST FAILED: ", msg.getElement(RESPONSE_ERROR))
            continue
        processMessage(msg)


def sendIntradayTickRequest(session, options, identity = None):
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

    print("Sending Request:", request)
    session.sendRequest(request, identity)


def eventLoop(session):
    done = False
    while not done:
        # nextEvent() method below is called with a timeout to let
        # the program catch Ctrl-C between arrivals of new events
        event = session.nextEvent(500)
        if event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
            print("Processing Partial Response")
            processResponseEvent(event)
        elif event.eventType() == blpapi.Event.RESPONSE:
            print("Processing Response")
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
    sessionOptions.setAuthenticationOptions(options.auth)

    print("Connecting to %s:%s" % (options.host, options.port))
    # Create a Session
    session = blpapi.Session(sessionOptions)

    # Start a Session
    if not session.start():
        print("Failed to start session.")
        return

    identity = None
    if options.auth:
        identity = session.createIdentity()
        isAuthorized = False
        authServiceName = "//blp/apiauth"
        if session.openService(authServiceName):
            authService = session.getService(authServiceName)
            isAuthorized = authorize(
                authService, identity, session,
                blpapi.CorrelationId("auth"))
        if not isAuthorized:
            print("No authorization")
            return

    try:
        # Open service to get historical data from
        if not session.openService("//blp/refdata"):
            print("Failed to open //blp/refdata")
            return

        sendIntradayTickRequest(session, options, identity)

        # wait for events from session.
        eventLoop(session)

    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print("IntradayTickExample")
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl+C pressed. Stopping...")

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
