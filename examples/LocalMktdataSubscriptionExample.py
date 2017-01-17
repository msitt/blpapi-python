# LocalMktdataSubscriptionExample.py

import blpapi
import datetime
import time
import traceback
import thread
import weakref
from optparse import OptionParser, OptionValueError
from blpapi import Event as EventType

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


def parseCmdLine():
    parser = OptionParser(description="Retrieve realtime data.")
    parser.add_option("-a",
                      "--ip",
                      dest="hosts",
                      help="server name or IP (default: localhost)",
                      metavar="ipAddress",
                      action="append",
                      default=[])
    parser.add_option("-p",
                      dest="port",
                      type="int",
                      help="server port (default: %default)",
                      metavar="tcpPort",
                      default=8194)
    parser.add_option("-s",
                      dest="service",
                      help="service name (default: %default)",
                      metavar="service",
                      default="//viper/mktdata")
    parser.add_option("-t",
                      dest="topics",
                      help="topic name (default: /ticker/IBM Equity)",
                      metavar="topic",
                      action="append",
                      default=[])
    parser.add_option("-f",
                      dest="fields",
                      help="field to subscribe to (default: empty)",
                      metavar="field",
                      action="append",
                      default=[])
    parser.add_option("-o",
                      dest="options",
                      help="subscription options (default: empty)",
                      metavar="option",
                      default=[])
    parser.add_option("--me",
                      dest="maxEvents",
                      type="int",
                      help="stop after this many events (default: %default)",
                      metavar="maxEvents",
                      default=1000000)
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

    if not options.hosts:
        options.hosts = ["localhost"]

    if not options.topics:
        options.topics = ["/ticker/IBM Equity"]

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
            print msg
            if msg.messageType() == TOKEN_SUCCESS:
                token = msg.getElementAsString(TOKEN)
            elif msg.messageType() == TOKEN_FAILURE:
                break

    if not token:
        print "Failed to get token"
        return False

    # Create and fill the authorithation request
    authRequest = authService.createAuthorizationRequest()
    authRequest.set(TOKEN, token)

    # Send authorithation request to "fill" the Identity
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
                print msg
                if msg.messageType() == AUTHORIZATION_SUCCESS:
                    return True
                print "Authorization failed"
                return False

        endTime = datetime.datetime.today()
        if endTime - startTime > datetime.timedelta(seconds=WAIT_TIME_SECONDS):
            return False


def main():
    global options
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    for idx, host in enumerate(options.hosts):
        sessionOptions.setServerAddress(host, options.port, idx)
    sessionOptions.setAuthenticationOptions(options.auth)
    sessionOptions.setAutoRestartOnDisconnection(True)

    # NOTE: If running without a backup server, make many attempts to
    # connect/reconnect to give that host a chance to come back up (the
    # larger the number, the longer it will take for SessionStartupFailure
    # to come on startup, or SessionTerminated due to inability to fail
    # over).  We don't have to do that in a redundant configuration - it's
    # expected at least one server is up and reachable at any given time,
    # so only try to connect to each server once.
    sessionOptions.setNumStartAttempts(1 if len(options.hosts) > 1 else 1000)

    print "Connecting to port %d on %s" % (
        options.port, ", ".join(options.hosts))

    session = blpapi.Session(sessionOptions)

    if not session.start():
        print "Failed to start session."
        return

    subscriptionIdentity = session.createIdentity()

    if options.auth:
        isAuthorized = False
        authServiceName = "//blp/apiauth"
        if session.openService(authServiceName):
            authService = session.getService(authServiceName)
            isAuthorized = authorize(
                authService, subscriptionIdentity, session,
                blpapi.CorrelationId("auth"))
        if not isAuthorized:
            print "No authorization"
            return

    subscriptions = blpapi.SubscriptionList()
    for t in options.topics:
        topic = options.service + t
        subscriptions.add(topic,
                          options.fields,
                          options.options,
                          blpapi.CorrelationId(topic))

    session.subscribe(subscriptions, subscriptionIdentity)

    try:
        eventCount = 0
        while True:
            # Specify timeout to give a chance for Ctrl-C
            event = session.nextEvent(1000)
            for msg in event:
                if event.eventType() == blpapi.Event.SUBSCRIPTION_STATUS or \
                        event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                    print "%s - %s" % (msg.correlationIds()[0].value(), msg)
                else:
                    print msg
            if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                eventCount += 1
                if eventCount >= options.maxEvents:
                    break
    finally:
        session.stop()


if __name__ == "__main__":
    print "LocalMktdataSubscriptionExample"
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
