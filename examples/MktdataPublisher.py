# MktdataPublisher.py
from __future__ import print_function
from __future__ import absolute_import

import time
from optparse import OptionParser, OptionValueError
import datetime
import threading

import os
import platform as plat
import sys
if sys.version_info >= (3, 8) and plat.system().lower() == "windows":
    # pylint: disable=no-member
    with os.add_dll_directory(os.getenv('BLPAPI_LIBDIR')):
        import blpapi
else:
    import blpapi

PERMISSION_REQUEST = blpapi.Name("PermissionRequest")
RESOLUTION_SUCCESS = blpapi.Name("ResolutionSuccess")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")
TOPICS = blpapi.Name("topics")
TOPIC_CREATED = blpapi.Name("TopicCreated")
TOPIC_SUBSCRIBED = blpapi.Name("TopicSubscribed")
TOPIC_UNSUBSCRIBED = blpapi.Name("TopicUnsubscribed")
TOPIC_RECAP = blpapi.Name("TopicRecap")


class MyStream(object):
    def __init__(self, sid="", fields=None):
        self.id = sid
        self.fields = fields if fields else []
        self.lastValue = 0
        self.topic = blpapi.Topic()
        self.isSubscribed = False

    def fillData(self, eventFormatter, elementDef):
        for i, f in enumerate(self.fields):
            if not elementDef.typeDefinition().hasElementDefinition(f):
                print("Invalid field '%s'" % f)
                continue

            fieldDef = elementDef.typeDefinition().getElementDefinition(f)
            fieldType = fieldDef.typeDefinition().datatype()
            value = None

            if fieldType == blpapi.DataType.BOOL:
                value = bool((self.lastValue + i) % 2 == 0)
            elif fieldType == blpapi.DataType.CHAR:
                value = chr((self.lastValue + i) % 100 + 32)
            elif fieldType == blpapi.DataType.INT32 or \
                    fieldType == blpapi.DataType.INT64:
                value = self.lastValue + i
            elif fieldType == blpapi.DataType.FLOAT32 or \
                    fieldType == blpapi.DataType.FLOAT64:
                value = (self.lastValue + i) * 1.1
            elif fieldType == blpapi.DataType.STRING:
                value = "S%d" % (self.lastValue + i)
            elif fieldType == blpapi.DataType.DATE or \
                    fieldType == blpapi.DataType.TIME or \
                    fieldType == blpapi.DataType.DATETIME:
                value = datetime.datetime.today()
                value.replace(day=(self.lastValue / 100) % 28 + 1)
                value.replace(microsecond=i * 1000)

            eventFormatter.setElement(f, value)

    def fillDataNull(self, eventFormatter, elementDef):
        for f in self.fields:
            if not elementDef.typeDefinition().hasElementDefinition(f):
                print("Invalid field '%s'" % f)
                continue

            fieldDef = elementDef.typeDefinition().getElementDefinition(f)
            if fieldDef.typeDefinition().isSimpleType():
                # Publishing NULL value
                eventFormatter.setElementNull(f)

    def next(self):
        self.lastValue += 1

    def isAvailable(self):
        return self.topic.isValid() and self.isSubscribed


class MyEventHandler(object):
    def __init__(self,
                 serviceName,
                 messageType,
                 fields,
                 eids,
                 resolveSubServiceCode,
                 mutex,
                 stop,
                 condition):
        self.serviceName = serviceName
        self.messageType = messageType
        self.fields = fields
        self.eids = eids
        self.resolveSubServiceCode = resolveSubServiceCode
        self.mutex = mutex
        self.stop = stop
        self.condition = condition
        self.streams = dict()
        self.availableTopicCount = 0

    def processEvent(self, event, session):
        if event.eventType() == blpapi.Event.SESSION_STATUS:
            for msg in event:
                print(msg)
                if msg.messageType() == SESSION_TERMINATED:
                    self.stop.set()

        elif event.eventType() == blpapi.Event.TOPIC_STATUS:
            topicList = blpapi.TopicList()

            for msg in event:
                print(msg)
                if msg.messageType() == TOPIC_SUBSCRIBED:
                    topicStr = msg.getElementAsString("topic")
                    with self.mutex:
                        if topicStr not in self.streams:
                            # TopicList knows how to add an entry based on a
                            # TOPIC_SUBSCRIBED message.
                            topicList.add(msg)
                            self.streams[topicStr] = MyStream(topicStr,
                                                           self.fields)
                        stream = self.streams[topicStr]
                        stream.isSubscribed = True
                        if stream.isAvailable():
                            self.availableTopicCount += 1
                            self.condition.notifyAll()

                elif msg.messageType() == TOPIC_UNSUBSCRIBED:
                    topicStr = msg.getElementAsString("topic")
                    with self.mutex:
                        if topicStr not in self.streams:
                            # We should never be coming here.
                            # TOPIC_UNSUBSCRIBED can not come before
                            # a TOPIC_SUBSCRIBED or TOPIC_CREATED
                            continue
                        stream = self.streams[topicStr]
                        if stream.isAvailable():
                            self.availableTopicCount -= 1
                            self.condition.notifyAll()
                        stream.isSubscribed = False

                elif msg.messageType() == TOPIC_CREATED:
                    topicStr = msg.getElementAsString("topic")
                    with self.mutex:
                        if topicStr not in self.streams:
                            self.streams[topicStr] = MyStream(topicStr,
                                                           self.fields)
                        stream = self.streams[topicStr]
                        try:
                            stream.topic = session.getTopic(msg)
                        except blpapi.Exception as e:
                            print("Exception while processing " \
                                "TOPIC_CREATED: %s" % e)
                            continue

                        if stream.isAvailable():
                            self.availableTopicCount += 1
                            self.condition.notifyAll()

                elif msg.messageType() == TOPIC_RECAP:
                    # Here we send a recap in response to a Recap request.
                    try:
                        topicStr = msg.getElementAsString("topic")
                        recapEvent = None

                        with self.mutex:
                            if topicStr not in self.streams:
                                continue
                            stream = self.streams[topicStr]
                            if not stream.isAvailable():
                                continue

                            topic = session.getTopic(msg)
                            service = topic.service()
                            recapCid = msg.correlationIds()[0]

                            recapEvent = service.createPublishEvent()
                            elementDef = \
                                service.getEventDefinition(self.messageType)

                            eventFormatter = blpapi.EventFormatter(recapEvent)
                            eventFormatter.appendRecapMessage(topic, recapCid)

                            stream.fillData(eventFormatter, elementDef)

                        session.publish(recapEvent)

                    except blpapi.Exception as e:
                        print("Exception while processing TOPIC_RECAP: %s" % e)
                        continue

            if topicList.size() > 0:
                # createTopicsAsync will result in RESOLUTION_STATUS,
                # TOPIC_CREATED events.
                session.createTopicsAsync(topicList)

        elif event.eventType() == blpapi.Event.RESOLUTION_STATUS:
            for msg in event:
                print(msg)

        elif event.eventType() == blpapi.Event.REQUEST:
            service = session.getService(self.serviceName)
            for msg in event:
                print(msg)

                if msg.messageType() == PERMISSION_REQUEST:
                    # Similar to createPublishEvent. We assume just one
                    # service - self.serviceName. A responseEvent can only be
                    # for single request so we can specify the correlationId -
                    # which establishes context - when we create the Event.

                    response = \
                        service.createResponseEvent(msg.correlationIds()[0])
                    permission = 1  # ALLOWED: 0, DENIED: 1
                    ef = blpapi.EventFormatter(response)
                    if msg.hasElement("uuid"):
                        msg.getElementAsInteger("uuid")
                        permission = 0
                    if msg.hasElement("applicationId"):
                        msg.getElementAsInteger("applicationId")
                        permission = 0

                    # In appendResponse the string is the name of the
                    # operation, the correlationId indicates which request we
                    # are responding to.
                    ef.appendResponse("PermissionResponse")
                    ef.pushElement("topicPermissions")

                    # For each of the topics in the request, add an entry to
                    # the response.
                    topicsElement = msg.getElement(TOPICS).values()
                    for topic in topicsElement:
                        ef.appendElement()
                        ef.setElement("topic", topic)
                        if self.resolveSubServiceCode:
                            try:
                                ef.setElement("subServiceCode",
                                              self.resolveSubServiceCode)
                                print(("Mapping topic %s to subServiceCode %s" %
                                      (topic, self.resolveSubServiceCode)))
                            except blpapi.Exception:
                                print("subServiceCode could not be set."
                                      " Resolving without subServiceCode")
                        ef.setElement("result", permission)
                        if permission == 1:  # DENIED
                            ef.pushElement("reason")
                            ef.setElement("source", "My Publisher Name")
                            ef.setElement("category", "NOT_AUTHORIZED")
                            ef.setElement("subcategory",
                                          "Publisher Controlled")
                            ef.setElement(
                                "description",
                                "Permission denied by My Publisher Name")
                            ef.popElement()
                        elif self.eids:
                            ef.pushElement("permissions")
                            ef.appendElement()
                            ef.setElement("permissionService", "//blp/blpperm")
                            ef.pushElement("eids")
                            for e in self.eids:
                                ef.appendValue(e)
                            ef.popElement()
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
                print(msg)

        return True


def authOptionCallback(_option, _opt, value, parser):
    """Parse authorization options from user input"""

    vals = value.split('=', 1)

    if value == "user":
        authUser = blpapi.AuthUser.createWithLogonName()
        authOptions = blpapi.AuthOptions.createWithUser(authUser)
    elif value == "none":
        authOptions = None
    elif vals[0] == "app" and len(vals) == 2:
        appName = vals[1]
        authOptions = blpapi.AuthOptions.createWithApp(appName)
    elif vals[0] == "userapp" and len(vals) == 2:
        appName = vals[1]
        authUser = blpapi.AuthUser.createWithLogonName()
        authOptions = blpapi.AuthOptions\
            .createWithUserAndApp(authUser, appName)
    elif vals[0] == "dir" and len(vals) == 2:
        activeDirectoryProperty = vals[1]
        authUser = blpapi.AuthUser\
            .createWithActiveDirectoryProperty(activeDirectoryProperty)
        authOptions = blpapi.AuthOptions.createWithUser(authUser)
    elif vals[0] == "manual":
        parts = []
        if len(vals) == 2:
            parts = vals[1].split(',')

        if len(parts) != 3:
            raise OptionValueError("Invalid auth option {}".format(value))

        appName, ip, userId = parts

        authUser = blpapi.AuthUser.createWithManualOptions(userId, ip)
        authOptions = blpapi.AuthOptions.createWithUserAndApp(authUser, appName)
    else:
        raise OptionValueError("Invalid auth option '{}'".format(value))

    parser.values.auth = {'option' : authOptions}

def parseCmdLine():
    parser = OptionParser(description="Publish market data.")
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
    parser.add_option("-f",
                      dest="fields",
                      help="field to subscribe to (default: LAST_PRICE)",
                      metavar="field",
                      action="append",
                      default=[])
    parser.add_option("-m",
                      dest="messageType",
                      help="type of published event (default: %default)",
                      metavar="messageType",
                      default="MarketDataEvents")
    parser.add_option("-e",
                      dest="eids",
                      help="permission eid for all subscriptions",
                      metavar="EID",
                      action="append",
                      default=[])
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
    parser.add_option("-c",
                      type="int",
                      dest="clearInterval",
                      help="number of events after which cache will be "
                      "cleared (default: 0 i.e cache never cleared)",
                      metavar="clearInterval",
                      default=0)
    parser.add_option("--auth",
                      dest="auth",
                      help="authentication option: "
                           "user|none|app=<app>|userapp=<app>|dir=<property>"
                           "|manual=<app,ip,user>"
                           " (default: user)\n"
                           "'none' is applicable to Desktop API product "
                           "that requires Bloomberg Professional service "
                           "to be installed locally.",
                      metavar="option",
                      action="callback",
                      callback=authOptionCallback,
                      type="string",
                      default={"option" :
                               blpapi.AuthOptions.createWithUser(
                                      blpapi.AuthUser.createWithLogonName())})
    parser.add_option("--ssc",
                      dest="ssc",
                      help="active sub-service code option: "
                      "<begin>,<end>,<priority>",
                      metavar="ssc",
                      default="")
    parser.add_option("--rssc",
                      dest="rssc",
                      help="sub-service code to be used in resolves",
                      metavar="rssc",
                      default="")

    (options, _) = parser.parse_args()

    if not options.hosts:
        options.hosts = ["localhost"]

    if not options.fields:
        options.fields = ["LAST_PRICE"]

    return options


def activate(options, session):
    if options.ssc:
        sscBegin, sscEnd, sscPriority = map(int, options.ssc.split(","))
        print(("Activating sub service code range [%s, %s] @ %s" %
            (sscBegin, sscEnd, sscPriority)))
        session.activateSubServiceCodeRange(options.service,
                                            sscBegin,
                                            sscEnd,
                                            sscPriority)


def deactivate(options, session):
    if options.ssc:
        sscBegin, sscEnd, sscPriority = map(int, options.ssc.split(","))
        print(("DeActivating sub service code range [%s, %s] @ %s" %
            (sscBegin, sscEnd, sscPriority)))
        session.deactivateSubServiceCodeRange(options.service,
                                              sscBegin,
                                              sscEnd)


def main():
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    for idx, host in enumerate(options.hosts):
        sessionOptions.setServerAddress(host, options.port, idx)
    sessionOptions.setSessionIdentityOptions(options.auth['option'])
    sessionOptions.setAutoRestartOnDisconnection(True)

    # NOTE: If running without a backup server, make many attempts to
    # connect/reconnect to give that host a chance to come back up (the
    # larger the number, the longer it will take for SessionStartupFailure
    # to come on startup, or SessionTerminated due to inability to fail
    # over).  We don't have to do that in a redundant configuration - it's
    # expected at least one server is up and reachable at any given time,
    # so only try to connect to each server once.
    sessionOptions.setNumStartAttempts(1 if len(options.hosts) > 1 else 1000)

    print("Connecting to port %d on %s" % (
        options.port, " ".join(options.hosts)))

    PUBLISH_MESSAGE_TYPE = blpapi.Name(options.messageType)
    mutex = threading.Lock()
    stop = threading.Event()
    condition = threading.Condition(mutex)

    myEventHandler = MyEventHandler(options.service,
                                    PUBLISH_MESSAGE_TYPE,
                                    options.fields,
                                    options.eids,
                                    options.rssc,
                                    mutex,
                                    stop,
                                    condition)

    # Create a Session
    session = blpapi.ProviderSession(sessionOptions,
                                     myEventHandler.processEvent)

    # Start a Session
    if not session.start():
        print("Failed to start session.")
        return

    serviceOptions = blpapi.ServiceRegistrationOptions()
    if options.groupId is not None:
        serviceOptions.setGroupId(options.groupId)
    serviceOptions.setServicePriority(options.priority)

    if options.ssc:
        sscBegin, sscEnd, sscPriority = map(int, options.ssc.split(","))
        print(("Adding active sub service code range [%s, %s] @ %s" %
            (sscBegin, sscEnd, sscPriority)))
        try:
            serviceOptions.addActiveSubServiceCodeRange(sscBegin,
                                                        sscEnd,
                                                        sscPriority)
        except blpapi.Exception as e:
            print(("FAILED to add active sub service codes."
                  " Exception %s" % e.description()))

    try:
        if not session.registerService(options.service,
                                       session.getAuthorizedIdentity(),
                                       serviceOptions):
            print("Failed to register '%s'" % options.service)
            return

        service = session.getService(options.service)
        elementDef = service.getEventDefinition(PUBLISH_MESSAGE_TYPE)
        eventCount = 0
        numPublished = 0
        while not stop.is_set():
            event = service.createPublishEvent()

            with condition:
                while myEventHandler.availableTopicCount == 0:
                    # Set timeout to 1 - give a chance for CTRL-C
                    condition.wait(1)
                    if stop.is_set():
                        return

                publishNull = False
                if (options.clearInterval > 0 and
                        eventCount == options.clearInterval):
                    eventCount = 0
                    publishNull = True
                eventFormatter = blpapi.EventFormatter(event)
                for _,stream in myEventHandler.streams.items():
                    if not stream.isAvailable():
                        continue
                    eventFormatter.appendMessage(PUBLISH_MESSAGE_TYPE,
                                                 stream.topic)
                    if publishNull:
                        stream.fillDataNull(eventFormatter, elementDef)
                    else:
                        eventCount += 1
                        stream.next()
                        stream.fillData(eventFormatter, elementDef)

            for msg in event:
                print(msg)

            session.publish(event)
            time.sleep(1)
            numPublished += 1
            if numPublished % 10 == 0:
                deactivate(options, session)
                time.sleep(30)
                activate(options, session)

    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print("MktdataPublisher")
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
