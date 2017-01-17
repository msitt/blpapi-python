# RequestServiceExample.py

import blpapi
import datetime
import time
import thread
import threading
from optparse import OptionParser, OptionValueError

AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
RESOLUTION_SUCCESS = blpapi.Name("ResolutionSuccess")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")
TOKEN = blpapi.Name("token")
TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")


g_running = True
g_mutex = threading.Lock()


class AuthorizationStatus:
    WAITING = 1
    AUTHORIZED = 2
    FAILED = 3
    __metaclass__ = blpapi.utils.MetaClassForClassesWithEnums


g_authorizationStatus = dict()


class MyProviderEventHandler(object):
    def __init__(self, serviceName):
        self.serviceName = serviceName

    def processEvent(self, event, session):
        global g_running

        print "Server received an event"
        if event.eventType() == blpapi.Event.SESSION_STATUS:
            for msg in event:
                print msg
                if msg.messageType() == SESSION_TERMINATED:
                    g_running = False

        elif event.eventType() == blpapi.Event.RESOLUTION_STATUS:
            for msg in event:
                print msg

        elif event.eventType() == blpapi.Event.REQUEST:
            service = session.getService(self.serviceName)
            for msg in event:
                print msg

                if msg.messageType() == blpapi.Name("ReferenceDataRequest"):
                    # Similar to createPublishEvent. We assume just one
                    # service - self.serviceName. A responseEvent can only be
                    # for single request so we can specify the correlationId -
                    # which establishes context - when we create the Event.

                    if msg.hasElement("timestamp"):
                        requestTime = msg.getElementAsFloat("timestamp")
                        latency = time.time() - requestTime
                        print "Response latency =", latency

                    response = \
                        service.createResponseEvent(msg.correlationIds()[0])
                    ef = blpapi.EventFormatter(response)

                    # In appendResponse the string is the name of the
                    # operation, the correlationId indicates which request we
                    # are responding to.
                    ef.appendResponse("ReferenceDataRequest")
                    securities = msg.getElement("securities")
                    fields = msg.getElement("fields")
                    ef.setElement("timestamp", time.time())
                    ef.pushElement("securityData")
                    for security in securities.values():
                        ef.appendElement()
                        ef.setElement("security", security)
                        ef.pushElement("fieldData")

                        for field in fields.values():
                            ef.appendElement()
                            ef.setElement("fieldId", field)
                            ef.pushElement("data")
                            ef.setElement("doubleValue", time.time())
                            ef.popElement()
                            ef.popElement()

                        ef.popElement()
                        ef.popElement()

                    # Service is implicit in the Event. sendResponse has a
                    # second parameter - partialResponse - that defaults to
                    # false.
                    session.sendResponse(response)

        else:
            for msg in event:
                print msg
                cids = msg.correlationIds()
                with g_mutex:
                    for cid in cids:
                        if cid in g_authorizationStatus:
                            if msg.messageType() == AUTHORIZATION_SUCCESS:
                                g_authorizationStatus[cid] = \
                                    AuthorizationStatus.AUTHORIZED
                            else:
                                g_authorizationStatus[cid] = \
                                    AuthorizationStatus.FAILED

        return True


class MyRequesterEventHandler(object):
    def processEvent(self, event, session):
        print "Client received an event"
        for msg in event:
            print msg
            cids = msg.correlationIds()
            with g_mutex:
                for cid in cids:
                    if cid in g_authorizationStatus:
                        if msg.messageType() == AUTHORIZATION_SUCCESS:
                            g_authorizationStatus[cid] = \
                                AuthorizationStatus.AUTHORIZED
                        else:
                            g_authorizationStatus[cid] = \
                                AuthorizationStatus.FAILED


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
    parser = OptionParser()
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
    parser.add_option("--service",
                      dest="service",
                      help="service name (default: %default)",
                      metavar="service",
                      default="//example/refdata")
    parser.add_option("-s",
                      dest="securities",
                      help="request security (default: IBM US Equity)",
                      metavar="security",
                      action="append",
                      default=[])
    parser.add_option("-f",
                      dest="fields",
                      help="request field (default: PX_LAST)",
                      metavar="field",
                      action="append",
                      default=[])
    parser.add_option("-r",
                      dest="role",
                      type="choice",
                      choices=["server", "client", "both"],
                      help="service role option: server|client|both " +
                           "(default: %default)",
                      metavar="option",
                      default="both")
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

    if not options.securities:
        options.securities = ["IBM US Equity"]

    if not options.fields:
        options.fields = ["PX_LAST"]

    return options


def serverRun(session, options):
    print "Server is starting------"

    if not session.start():
        print "Failed to start server session."
        return

    providerIdentity = session.createIdentity()

    if options.auth:
        isAuthorized = False
        authServiceName = "//blp/apiauth"
        if session.openService(authServiceName):
            authService = session.getService(authServiceName)
            isAuthorized = authorize(
                authService, providerIdentity, session,
                blpapi.CorrelationId("sauth"))
        if not isAuthorized:
            print "No authorization"
            return

    if not session.registerService(options.service, providerIdentity):
        print "Failed to register", options.service
        return


def clientRun(session, options):
    print "Client is starting------"

    if not session.start():
        print "Failed to start client session."
        return

    identity = session.createIdentity()

    if options.auth:
        isAuthorized = False
        authServiceName = "//blp/apiauth"
        if session.openService(authServiceName):
            authService = session.getService(authServiceName)
            isAuthorized = authorize(
                authService, identity, session,
                blpapi.CorrelationId("cauth"))
        if not isAuthorized:
            print "No authorization"
            return

    if not session.openService(options.service):
        print "Failed to open", options.service
        return

    service = session.getService(options.service)
    request = service.createRequest("ReferenceDataRequest")

    # append securities to request
    # Add securities to request
    securities = request.getElement("securities")
    for security in options.securities:
        securities.appendValue(security)

    # Add fields to request
    fields = request.getElement("fields")
    for field in options.fields:
        fields.appendValue(field)

    request.set("timestamp", time.time())

    print "Sendind Request:", request

    eventQueue = blpapi.EventQueue()
    session.sendRequest(request, identity, blpapi.CorrelationId("AddRequest"),
                        eventQueue)

    while True:
        # Specify timeout to give a chance for Ctrl-C
        event = eventQueue.nextEvent(500)

        if event.eventType() == blpapi.Event.TIMEOUT:
            continue

        print "Client received an event"
        for msg in event:
            with g_mutex:
                if event.eventType() == blpapi.Event.RESPONSE:
                    if msg.hasElement("timestamp"):
                        responseTime = msg.getElementAsFloat("timestamp")
                        print "Response latency =", time.time() - responseTime
                print msg

        if event.eventType() == blpapi.Event.RESPONSE:
            break


def authorize(authService, identity, session, cid):
    with g_mutex:
        g_authorizationStatus[cid] = AuthorizationStatus.WAITING

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
        with g_mutex:
            if AuthorizationStatus.WAITING != g_authorizationStatus[cid]:
                return AuthorizationStatus.AUTHORIZED == g_authorizationStatus[cid]

        endTime = datetime.datetime.today()
        if endTime - startTime > datetime.timedelta(seconds=WAIT_TIME_SECONDS):
            return False

        time.sleep(1)


def main():
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    for idx, host in enumerate(options.hosts):
        sessionOptions.setServerAddress(host, options.port, idx)
    sessionOptions.setAuthenticationOptions(options.auth)
    sessionOptions.setAutoRestartOnDisconnection(True)
    sessionOptions.setNumStartAttempts(len(options.hosts))

    print "Connecting to port %d on %s" % (
        options.port, ", ".join(options.hosts))

    providerEventHandler = MyProviderEventHandler(options.service)
    providerSession = blpapi.ProviderSession(sessionOptions,
                                             providerEventHandler.processEvent)

    requesterEventHandler = MyRequesterEventHandler()
    requesterSession = blpapi.Session(sessionOptions,
                                      requesterEventHandler.processEvent)

    if options.role in ["server", "both"]:
        serverRun(providerSession, options)

    if options.role in ["client", "both"]:
        clientRun(requesterSession, options)

    # wait for enter key to exit application
    print "Press ENTER to quit"
    raw_input()

    if options.role in ["server", "both"]:
        providerSession.stop()

    if options.role in ["client", "both"]:
        requesterSession.stop()


if __name__ == "__main__":
    print "RequestServiceExample"
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
