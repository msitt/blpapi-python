# GenerateTokenSubscriptionExample.py

import blpapi
from optparse import OptionParser
import traceback

AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
AUTHORIZATION_FAILURE = blpapi.Name("AuthorizationFailure")
TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")


g_session = None
g_identity = None
g_securities = None
g_fields = None
g_options = None


def parseCmdLine():
    parser = OptionParser(description="Generate a token for authorization")
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
                      dest="securities",
                      help="security (default: IBM US Equity)",
                      metavar="security",
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
                      help="subscribtion options",
                      metavar="options",
                      action="append",
                      default=[])
    parser.add_option("-d",
                      dest="dirSvcProperty",
                      help="dirSvcProperty",
                      metavar="dirSvcProperty")

    (options, args) = parser.parse_args()

    if not options.securities:
        options.securities = ["IBM US Equity"]

    if not options.fields:
        options.fields = ["LAST_PRICE"]

    return options


def subscribe():
    # Create a SubscriptionList and populate it with securities, fields etc
    subscriptions = blpapi.SubscriptionList()

    for i, security in enumerate(g_securities):
        subscriptions.add(security,
                          g_fields,
                          g_options,
                          blpapi.CorrelationId(i))

    print "Subscribing..."
    g_session.subscribe(subscriptions, g_identity)


def processTokenStatus(event):
    global g_identity
    print "processTokenEvents"

    for msg in event:
        if msg.messageType() == TOKEN_SUCCESS:
            print msg

            # Authentication phase has passed; send authorization request
            authService = g_session.getService("//blp/apiauth")
            authRequest = authService.createAuthorizationRequest()
            authRequest.set("token", msg.getElementAsString("token"))
            g_identity = g_session.createIdentity()
            g_session.sendAuthorizationRequest(
                authRequest,
                g_identity,
                blpapi.CorrelationId(1))
        elif msg.messageType() == TOKEN_FAILURE:
            # Token generation failure
            print(msg)
            return False
    return True


def processEvent(event):
    print "processEvent"

    for msg in event:
        if msg.messageType() == AUTHORIZATION_SUCCESS:
            # Authorization phase has passed; subscribe to market data
            print "Authorization SUCCESS"
            subscribe()
        elif msg.messageType() == AUTHORIZATION_FAILURE:
            # Authorization failure
            print "Authorization FAILED"
            print msg
            return False
        else:
            print msg
    return True


def main():
    global g_session, g_securities, g_fields

    print "GenerateTokenSubscriptionExample"
    options = parseCmdLine()

    # Create SessionOptions object and populate it with data
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)
    authOptions = "AuthenticationType=OS_LOGON"
    if options.dirSvcProperty:
        authOptions = "AuthenticationType=DIRECTORY_SERVICE;" + \
            "DirSvcPropertyName=" + options.dirSvcProperty
    print "authOptions = %s" % authOptions
    sessionOptions.setAuthenticationOptions(authOptions)

    g_securities = options.securities
    g_fields = options.fields

    print "Connecting to %s:%s" % (options.host, options.port)
    g_session = blpapi.Session(sessionOptions)
    if not g_session.start():
        print("Failed to start session.")
        return

    # Open market data service
    if not g_session.openService("//blp/mktdata"):
        print("Failed to open //blp/mktdata")
        return

    # Open authorization service
    if not g_session.openService("//blp/apiauth"):
        print("Failed to open //blp/apiauth")
        return

    # Submit a token generation request
    tokenReqId = blpapi.CorrelationId(99)
    g_session.generateToken(tokenReqId)

    # Handle and respond to incoming events
    while True:
        # nextEvent() method below is called with a timeout to let
        # the program catch Ctrl-C between arrivals of new events
        event = g_session.nextEvent(1000)
        if event.eventType() != blpapi.Event.TIMEOUT:
            if event.eventType() == blpapi.Event.TOKEN_STATUS:
                # Handle response to token generation request
                if not processTokenStatus(event):
                    break
            else:
                # Handle all other events
                if not processEvent(event):
                    break


if __name__ == "__main__":
    print "GenerateTokenSubscriptionExample"
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
