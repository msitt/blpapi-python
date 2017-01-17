# SimpleAsyncSubscription.py

import blpapi
import time
import traceback
import thread
import weakref
from optparse import OptionParser
from blpapi import Event as EventType

SESSION_STARTED = blpapi.Name("SessionStarted")
SESSION_STARTUP_FAILURE = blpapi.Name("SessionStartupFailure")
TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")
AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
AUTHORIZATION_FAILURE = blpapi.Name("AuthorizationFailure")
TOKEN = blpapi.Name("token")
AUTH_SERVICE = "//blp/apiauth"


EVENT_TYPE_NAMES = {
    EventType.ADMIN: "ADMIN",
    EventType.SESSION_STATUS: "SESSION_STATUS",
    EventType.SUBSCRIPTION_STATUS: "SUBSCRIPTION_STATUS",
    EventType.REQUEST_STATUS: "REQUEST_STATUS",
    EventType.RESPONSE: "RESPONSE",
    EventType.PARTIAL_RESPONSE: "PARTIAL_RESPONSE",
    EventType.SUBSCRIPTION_DATA: "SUBSCRIPTION_DATA",
    EventType.SERVICE_STATUS: "SERVICE_STATUS",
    EventType.TIMEOUT: "TIMEOUT",
    EventType.AUTHORIZATION_STATUS: "AUTHORIZATION_STATUS",
    EventType.RESOLUTION_STATUS: "RESOLUTION_STATUS",
    EventType.TOPIC_STATUS: "TOPIC_STATUS",
    EventType.TOKEN_STATUS: "TOKEN_STATUS",
    EventType.REQUEST: "REQUEST"
}


class Error(Exception):
    pass


def getAuthentificationOptions(type, name):
    if type == "NONE":
        return None
    elif type == "USER_APP":
        return "AuthenticationMode=USER_AND_APPLICATION;"\
            "AuthenticationType=OS_LOGON;"\
            "ApplicationAuthenticationType=APPNAME_AND_KEY;"\
            "ApplicationName=" + name
    elif type == "APPLICATION":
        return "AuthenticationMode=APPLICATION_ONLY;"\
            "ApplicationAuthenticationType=APPNAME_AND_KEY;"\
            "ApplicationName=" + name
    elif type == "DIRSVC":
        return "AuthenticationType=DIRECTORY_SERVICE;"\
            "DirSvcPropertyName=" + name
    else:
        return "AuthenticationType=OS_LOGON"


def topicName(security):
    if security.startswith("//"):
        return security
    else:
        return "//blp/mktdata/" + security


def printMessage(msg, eventType):
    print "#{0} msg received: [{1}] => {2}/{3}".format(
        thread.get_ident(),
        ", ".join(map(str, msg.correlationIds())),
        EVENT_TYPE_NAMES[eventType],
        msg)


def parseCmdLine():
    parser = OptionParser()
    parser.add_option("-a",
                      "--host",
                      dest="host",
                      help="HOST address to connect to",
                      metavar="HOST",
                      default="localhost")
    parser.add_option("-p",
                      "--port",
                      dest="port",
                      type="int",
                      help="PORT to connect to (%default)",
                      metavar="PORT",
                      default=8194)
    parser.add_option("-s",
                      "--security",
                      dest="securities",
                      help="security to subscribe to "
                      "('IBM US Equity' by default)",
                      metavar="SECURITY",
                      action="append",
                      default=[])
    parser.add_option("-f",
                      "--fields",
                      dest="fields",
                      help="comma "
                      "separated list of FIELDS to subscribe to "
                      "('LAST_PRICE,BID,ASK' by default)",
                      metavar="FIELDS",
                      default="LAST_PRICE,BID,ASK")
    parser.add_option("",
                      "--auth-type",
                      type="choice",
                      choices=["LOGON", "NONE", "APPLICATION", "DIRSVC",
                      "USER_APP"],
                      dest="authType",
                      help="Authentification type: LOGON (default), NONE, "
                      "APPLICATION, DIRSVC or USER_APP",
                      default="LOGON")
    parser.add_option("",
                      "--auth-name",
                      dest="authName",
                      help="The name of application or directory service",
                      default="")

    (options, args) = parser.parse_args()

    if not options.securities:
        options.securities = ["IBM US Equity"]

    options.auth = getAuthentificationOptions(options.authType,
                                              options.authName)
    return options


# Subscribe 'session' for the securities and fields specified in 'options'
def subscribe(session, options, identity=None):
    sl = blpapi.SubscriptionList()
    for s in options.securities:
        topic = topicName(s)
        cid = blpapi.CorrelationId(s)
        print "Subscribing {0} => {1}".format(cid, topic)
        sl.add(topic, options.fields, correlationId=cid)
    session.subscribe(sl, identity)


# Event handler
def processEvent(event, session):
    global identity
    global options

    try:
        eventType = event.eventType()
        for msg in event:
            # Print all aincoming messages including the SubscriptionData
            printMessage(msg, eventType)

            if eventType == EventType.SESSION_STATUS:
                if msg.messageType() == SESSION_STARTED:
                    # Session.startAsync completed successfully
                    # Start the authorization if needed
                    if options.auth:
                        # Generate token
                        session.generateToken()
                    else:
                        identity = None
                        # Subscribe for the specified securities/fields
                        subscribe(session, options)
                elif msg.messageType() == SESSION_STARTUP_FAILURE:
                    # Session.startAsync failed, raise exception to exit
                    raise Error("Can't start session")

            elif eventType == EventType.TOKEN_STATUS:
                if msg.messageType() == TOKEN_SUCCESS:
                    # Token generated successfully
                    # Continue the authorization
                    # Get generated token
                    token = msg.getElementAsString(TOKEN)
                    # Open auth service (we do it syncroniously, just in case)
                    if not session.openService(AUTH_SERVICE):
                        raise Error("Failed to open auth service")
                    # Obtain opened service
                    authService = session.getService(AUTH_SERVICE)
                    # Create and fill the authorization request
                    authRequest = authService.createAuthorizationRequest()
                    authRequest.set(TOKEN, token)
                    # Create Identity
                    identity = session.createIdentity()
                    # Send authorization request to "fill" the Identity
                    session.sendAuthorizationRequest(authRequest, identity)
                else:
                    # Token generation failed, raise exception to exit
                    raise Error("Failed to generate token")

            elif eventType == EventType.RESPONSE \
                    or eventType == EventType.PARTIAL_RESPONSE:
                if msg.messageType() == AUTHORIZATION_SUCCESS:
                    # Authorization passed, identity "filled" and can be used
                    # Subscribe for the specified securities/fields with using
                    # of the identity
                    subscribe(session, options, identity)
                elif msg.messageType() == AUTHORIZATION_FAILURE:
                    # Authorization failed, raise exception to exit
                    raise Error("Failed to pass authorization")
    except Error as ex:
        print "Error in event handler:", ex
        # Interrupt a "sleep loop" in main thread
        thread.interrupt_main()


def main():
    global options
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)
    if options.auth:
        sessionOptions.setAuthenticationOptions(options.auth)

    # Create an EventDispatcher with 2 processing threads
    dispatcher = blpapi.EventDispatcher(2)

    # Create a Session
    session = blpapi.Session(sessionOptions, processEvent, dispatcher)

    # Start dispatcher to "pump" the received events
    dispatcher.start()

    # Start session asyncroniously
    if not session.startAsync():
        raise Exception("Can't initiate session start.")

    # Sleep until application will be interrupted by user (Ctrl+C pressed)
    # or because of the exception in event handler
    try:
        # Note that: 'thread.interrupt_main()' could be used to
        # correctly stop the application from 'processEvent'
        while True:
            time.sleep(1)
    finally:
        session.stop()
        dispatcher.stop()


if __name__ == "__main__":
    print "SimpleAsyncSubscription"
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
