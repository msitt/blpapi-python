# PagePublisherExample.py

import blpapi
import time
from optparse import OptionParser, OptionValueError
import datetime
import threading

AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
RESOLUTION_SUCCESS = blpapi.Name("ResolutionSuccess")
PERMISSION_REQUEST = blpapi.Name("PermissionRequest")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")
TOKEN = blpapi.Name("token")
TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")
TOPICS = blpapi.Name("topics")
TOPIC_CREATED = blpapi.Name("TopicCreated")
TOPIC_RECAP = blpapi.Name("TopicRecap")
TOPIC_SUBSCRIBED = blpapi.Name("TopicSubscribed")
TOPIC_UNSUBSCRIBED = blpapi.Name("TopicUnsubscribed")


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
        self.isInitialPaintSent = False
        self.topic = blpapi.Topic()
        self.isSubscribed = False

    def isAvailable(self):
        return self.topic.isValid() and self.isSubscribed

g_streams = dict()
g_availableTopicCount = 0
g_mutex = threading.Lock()
# Indicates if g_availableTopicCount is non-zero
g_condition = threading.Condition(g_mutex)


class MyEventHandler(object):
    def __init__(self, serviceName):
        self.serviceName = serviceName

    def processEvent(self, event, session):
        global g_availableTopicCount, g_running

        if event.eventType() == blpapi.Event.SESSION_STATUS:
            for msg in event:
                print msg
                if msg.messageType() == SESSION_TERMINATED:
                    g_running = False

        elif event.eventType() == blpapi.Event.TOPIC_STATUS:
            topicList = blpapi.TopicList()

            for msg in event:
                print msg
                if msg.messageType() == TOPIC_SUBSCRIBED:
                    topicStr = msg.getElementAsString("topic")
                    with g_mutex:
                        if topicStr not in g_streams:
                            # TopicList knows how to add an entry based on a
                            # TOPIC_SUBSCRIBED message.
                            topicList.add(msg)
                            g_streams[topicStr] = MyStream(topicStr)
                        stream = g_streams[topicStr]
                        stream.isSubscribed = True
                        if stream.isAvailable():
                            g_availableTopicCount += 1
                            g_condition.notifyAll()

                elif msg.messageType() == TOPIC_UNSUBSCRIBED:
                    topicStr = msg.getElementAsString("topic")
                    with g_mutex:
                        if topicStr not in g_streams:
                            # We should never be coming here.
                            # TOPIC_UNSUBSCRIBED can not come before
                            # a TOPIC_SUBSCRIBED or TOPIC_CREATED
                            continue
                        stream = g_streams[topicStr]
                        if stream.isAvailable():
                            g_availableTopicCount -= 1
                            g_condition.notifyAll()
                        stream.isSubscribed = False

                elif msg.messageType() == TOPIC_CREATED:
                    topicStr = msg.getElementAsString("topic")
                    with g_mutex:
                        if topicStr not in g_streams:
                            g_streams[topicStr] = MyStream(topicStr)
                        stream = g_streams[topicStr]
                        try:
                            stream.topic = session.getTopic(msg)
                        except blpapi.Exception as e:
                            print "Exception while processing " \
                                "TOPIC_CREATED: %s" % e
                            continue

                        if stream.isAvailable():
                            g_availableTopicCount += 1
                            g_condition.notifyAll()

                elif msg.messageType() == TOPIC_RECAP:
                    # Here we send a recap in response to a Recap request.
                    try:
                        topicStr = msg.getElementAsString("topic")
                        recapEvent = None

                        with g_mutex:
                            if topicStr not in g_streams:
                                continue
                            stream = g_streams[topicStr]
                            if not stream.isAvailable():
                                continue

                            topic = session.getTopic(msg)
                            service = topic.service()
                            recapCid = msg.correlationIds()[0]

                            recapEvent = service.createPublishEvent()
                            evFormatter = blpapi.EventFormatter(recapEvent)
                            evFormatter.appendRecapMessage(topic, recapCid)
                            evFormatter.setElement("numRows", 25)
                            evFormatter.setElement("numCols", 80)
                            evFormatter.pushElement("rowUpdate")

                            for i in xrange(1, 6):
                                evFormatter.appendElement()
                                evFormatter.setElement("rowNum", i)
                                evFormatter.pushElement("spanUpdate")
                                evFormatter.appendElement()
                                evFormatter.setElement("startCol", 1)
                                evFormatter.setElement("length", 10)
                                evFormatter.setElement("text", "RECAP")
                                evFormatter.popElement()
                                evFormatter.popElement()
                                evFormatter.popElement()

                            evFormatter.popElement()

                        session.publish(recapEvent)

                    except blpapi.Exception as e:
                        print "Exception while processing TOPIC_RECAP: %s" % e
                        continue

            if topicList.size() > 0:
                # createTopicsAsync will result in RESOLUTION_STATUS,
                # TOPIC_CREATED events.
                session.createTopicsAsync(topicList)

        elif event.eventType() == blpapi.Event.RESOLUTION_STATUS:
            for msg in event:
                print msg

        elif event.eventType() == blpapi.Event.REQUEST:
            service = session.getService(self.serviceName)
            for msg in event:
                print msg

                if msg.messageType() == PERMISSION_REQUEST:
                    # This example always sends a 'PERMISSIONED' response.
                    # See 'MktdataPublisherExample' on how to parse a
                    # Permission request and send an appropriate
                    # 'PermissionResponse'.

                    response = \
                        service.createResponseEvent(msg.correlationIds()[0])
                    permission = 0  # ALLOWED: 0, DENIED: 1
                    ef = blpapi.EventFormatter(response)
                    ef.appendResponse("PermissionResponse")
                    ef.pushElement("topicPermissions")

                    # For each of the topics in the request, add an entry to
                    # the response.
                    topicsElement = msg.getElement(TOPICS).values()
                    for topic in topicsElement:
                        ef.appendElement()
                        ef.setElement("topic", topic)
                        ef.setElement("result", permission)
                        ef.popElement()
                    ef.popElement()

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
    parser = OptionParser(description="Publish on a topic.")
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
                      default="//viper/page")
    parser.add_option("-g",
                      dest="groupId",
                      help="publisher groupId (defaults to unique value)",
                      metavar="groupId")
    parser.add_option("-r",
                      "--pri",
                      type="int",
                      dest="priority",
                      help="set publisher priority level (default: %default)",
                      metavar="priority",
                      default=10)
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

    print "Connecting to port %d on %s" % (
        options.port, " ".join(options.hosts))

    myEventHandler = MyEventHandler(options.service)

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

    serviceOptions = blpapi.ServiceRegistrationOptions()
    if options.groupId is not None:
        serviceOptions.setGroupId(options.groupId)
    serviceOptions.setServicePriority(options.priority)

    if not session.registerService(options.service,
                                   providerIdentity,
                                   serviceOptions):
        print "Failed to register '%s'" % options.service
        return

    service = session.getService(options.service)

    try:
        # Now we will start publishing
        value = 1
        while g_running:
            event = service.createPublishEvent()

            with g_condition:
                while g_availableTopicCount == 0:
                    # Set timeout to 1 - give a chance for CTRL-C
                    g_condition.wait(1)
                    if not g_running:
                        return

                eventFormatter = blpapi.EventFormatter(event)
                for topicName, stream in g_streams.iteritems():
                    if not stream.isAvailable():
                        continue

                    value += 1

                    if not stream.isInitialPaintSent:
                        eventFormatter.appendRecapMessage(stream.topic)
                        eventFormatter.setElement("numRows", 25)
                        eventFormatter.setElement("numCols", 80)
                        eventFormatter.pushElement("rowUpdate")
                        for i in xrange(1, 6):
                            eventFormatter.appendElement()
                            eventFormatter.setElement("rowNum", i)
                            eventFormatter.pushElement("spanUpdate")
                            eventFormatter.appendElement()
                            eventFormatter.setElement("startCol", 1)
                            eventFormatter.setElement("length", 10)
                            eventFormatter.setElement("text", "INITIAL")
                            eventFormatter.setElement("fgColor", "RED")
                            eventFormatter.popElement()
                            eventFormatter.popElement()
                            eventFormatter.popElement()
                        eventFormatter.popElement()
                        stream.isInitialPaintSent = True

                    eventFormatter.appendMessage("RowUpdate", stream.topic)
                    eventFormatter.setElement("rowNum", 1)
                    eventFormatter.pushElement("spanUpdate")
                    eventFormatter.appendElement()
                    START_COL = blpapi.Name("startCol")
                    eventFormatter.setElement(START_COL, 1)
                    strValue = str(value)
                    eventFormatter.setElement("length", len(strValue))
                    eventFormatter.setElement("text", strValue)
                    eventFormatter.popElement()
                    eventFormatter.popElement()

            for msg in event:
                print msg

            session.publish(event)
            time.sleep(10)

    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print "PagePublisherExample"
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
