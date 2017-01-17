# ContributionsMktdataExample.py

import blpapi
import time
from optparse import OptionParser, OptionValueError
import datetime
import threading

TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")
AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
TOKEN = blpapi.Name("token")
MARKET_DATA = blpapi.Name("MarketData")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")


g_running = True
g_mutex = threading.Lock()


class AuthorizationStatus:
    WAITING = 1
    AUTHORIZED = 2
    FAILED = 3
    __metaclass__ = blpapi.utils.MetaClassForClassesWithEnums


g_authorizationStatus = dict()


class MyStream(object):
    def __init__(self, id=""):
        self.id = id


class MyEventHandler(object):
    def processEvent(self, event, session):
        global g_running

        for msg in event:
            print msg
            if event.eventType() == blpapi.Event.SESSION_STATUS:
                if msg.messageType() == SESSION_TERMINATED:
                    g_running = False
                continue

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
    parser = OptionParser(description="Market data contribution.")
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
                      default="//blp/mpfbapi")
    parser.add_option("-t",
                      dest="topic",
                      help="topic (default: %default)",
                      metavar="topic",
                      default="/ticker/AUDEUR Curncy")
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

    return options


def authorize(authService, identity, session, cid):
    with g_mutex:
        g_authorizationStatus[cid] = AuthorizationStatus.WAITING

    tokenEventQueue = blpapi.EventQueue()

    # Generate token
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
    WAIT_TIME_SECONDS = datetime.timedelta(seconds=10)
    while True:
        with g_mutex:
            if AuthorizationStatus.WAITING != g_authorizationStatus[cid]:
                return AuthorizationStatus.AUTHORIZED == \
                    g_authorizationStatus[cid]

        endTime = datetime.datetime.today()
        if endTime - startTime > WAIT_TIME_SECONDS:
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

    myEventHandler = MyEventHandler()

    # Create a Session
    session = blpapi.ProviderSession(sessionOptions,
                                     myEventHandler.processEvent)

    # Start a Session
    if not session.start():
        print "Failed to start session."
        return

    providerIdentity = session.createIdentity()

    if options.auth:
        isAuthorized = False
        authServiceName = "//blp/apiauth"
        if session.openService(authServiceName):
            authService = session.getService(authServiceName)
            isAuthorized = authorize(
                authService, providerIdentity, session,
                blpapi.CorrelationId("auth"))
        if not isAuthorized:
            print "No authorization"
            return

    topicList = blpapi.TopicList()
    topicList.add(options.service + options.topic,
                  blpapi.CorrelationId(MyStream(options.topic)))

    # Create topics
    session.createTopics(topicList,
                         blpapi.ProviderSession.AUTO_REGISTER_SERVICES,
                         providerIdentity)
    # createTopics() is synchronous, topicList will be updated
    # with the results of topic creation (resolution will happen
    # under the covers)

    streams = []
    for i in xrange(topicList.size()):
        stream = topicList.correlationIdAt(i).value()
        status = topicList.statusAt(i)
        topicString = topicList.topicStringAt(i)

        if (status == blpapi.TopicList.CREATED):
            stream.topic = session.getTopic(topicList.messageAt(i))
            streams.append(stream)
        else:
            print "Stream '%s': topic not resolved, status = %d" % (
                stream.id, status)

    service = session.getService(options.service)

    try:
        # Now we will start publishing
        value = 1
        while streams and g_running:
            event = service.createPublishEvent()
            eventFormatter = blpapi.EventFormatter(event)

            for stream in streams:
                value += 1
                eventFormatter.appendMessage(MARKET_DATA, stream.topic)
                eventFormatter.setElement("BID", 0.5 * value)
                eventFormatter.setElement("ASK", value)

            for msg in event:
                print msg

            session.publish(event)
            time.sleep(10)
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print "ContributionsMktdataExample"
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
