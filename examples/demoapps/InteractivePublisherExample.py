from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, \
    createSessionOptions
import threading
import time

RESOLVED_TOPIC = blpapi.Name("resolvedTopic")
TOPICS = blpapi.Name("topics")


class MyEventHandler(object):
    def __init__(self,
                 serviceName,
                 eids,
                 resolveSubServiceCode,
                 mutex,
                 stop,
                 condition,
                 isPageData):
        self.serviceName = serviceName
        self.eids = eids
        self.resolveSubServiceCode = resolveSubServiceCode
        self.mutex = mutex
        self.stop = stop
        self.condition = condition
        self.activeTopics = []
        self.isPageData = isPageData

    def processEvent(self, event, session):
        eventType = event.eventType()
        if eventType == blpapi.Event.SESSION_STATUS:
            for msg in event:
                print(msg)
                if msg.messageType() == blpapi.Names.SESSION_TERMINATED:
                    print("Received session terminated, stopping session")
                    self.stop.set()
                    break

        elif eventType == blpapi.Event.TOPIC_STATUS:
            self.processTopicStatusEvent(session, event)

        elif eventType == blpapi.Event.RESOLUTION_STATUS:
            for msg in event:
                print(msg)

                if msg.messageType() == blpapi.Names.RESOLUTION_SUCCESS:
                    resolvedTopic = msg.getElementAsString(RESOLVED_TOPIC)
                    print(f"ResolvedTopic:  {resolvedTopic}")
                elif msg.messageType() == blpapi.Names.RESOLUTION_FAILURE:
                    print("Topic resolution failed "
                          f"(CorrelationId = {msg.correlationId()})")

        elif eventType == blpapi.Event.REQUEST:
            for msg in event:
                print(msg)

                if msg.messageType() == blpapi.Names.PERMISSION_REQUEST:
                    self.processPermissionRequest(session, msg)
        else:
            for msg in event:
                print(msg)

        return True

    def processTopicStatusEvent(self, session, event):
        topicsToCreate = blpapi.TopicList()
        unsubscribedTopics = []
        for msg in event:
            print(msg)
            msgType = msg.messageType()
            topic = session.getTopic(msg)

            if msgType == blpapi.Names.TOPIC_SUBSCRIBED:
                if not topic.isValid():
                    # Add the topic contained in the message to TopicList
                    topicsToCreate.add(msg)

            elif msgType == blpapi.Names.TOPIC_UNSUBSCRIBED:
                unsubscribedTopics.append(topic)
                with self.mutex:
                    self.activeTopics.remove(topic)

            elif msgType == blpapi.Names.TOPIC_ACTIVATED:
                with self.mutex:
                    self.activeTopics.append(topic)
                    self.condition.notifyAll()

            elif msgType == blpapi.Names.TOPIC_RECAP:
                # Here we send a recap in response to a Recap request.
                service = topic.service()
                correlationId = msg.correlationId()
                recapEvent = service.createPublishEvent()
                eventFormatter = blpapi.EventFormatter(recapEvent)
                eventFormatter.appendRecapMessage(topic, correlationId)

                if self.isPageData:
                    formatPageRecapEvent(eventFormatter)
                else:
                    formatMarketDataRecapEvent(eventFormatter)

                session.publish(recapEvent)
                print("Published recap event:")
                for recapMsg in recapEvent:
                    print(recapMsg)

        if topicsToCreate.size() > 0:
            # createTopicsAsync will result in RESOLUTION_SUCCESS and
            # TOPIC_CREATED messages.
            session.createTopicsAsync(topicsToCreate)

        # Delete all the unsubscribed topics.
        if len(unsubscribedTopics) > 0:
            session.deleteTopics(unsubscribedTopics)


    def processPermissionRequest(self, session, msg):
        service = session.getService(self.serviceName)

        # Similar to createPublishEvent. We assume just one
        # service - self.serviceName. A responseEvent can only be
        # for single request so we can specify the correlationId -
        # which establishes context - when we create the Event.
        response = service.createResponseEvent(msg.correlationId())
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
                    print(f"Mapping topic {topic} to subServiceCode"
                          f" {self.resolveSubServiceCode}")
                except blpapi.Exception:
                    print("subServiceCode could not be set."
                          " Resolving without subServiceCode")
            ef.setElement("result", permission)
            if permission == 1:  # DENIED
                ef.pushElement("reason")
                ef.setElement("source", "My Publisher Name")
                ef.setElement("category", "NOT_AUTHORIZED")
                ef.setElement("subcategory", "Publisher Controlled")
                ef.setElement("description",
                              "Permission denied by My Publisher Name")
                ef.popElement()
            elif self.eids:
                ef.pushElement("permissions")
                ef.appendElement()
                ef.setElement("permissionService", "//blp/blpperm")
                ef.pushElement("eids")
                for eid in self.eids:
                    ef.appendValue(eid)
                ef.popElement()
                ef.popElement()
                ef.popElement()
            ef.popElement()
        ef.popElement()

        # Service is implicit in the Event. sendResponse has a second parameter
        # - partialResponse - that defaults to false.
        session.sendResponse(response)

def formatPageRecapEvent(eventFormatter):
    numRows = 5
    eventFormatter.setElement("numRows", numRows)
    eventFormatter.setElement("numCols", 80)
    eventFormatter.pushElement("rowUpdate")

    for i in range(1, numRows + 1):
        eventFormatter.appendElement()
        eventFormatter.setElement("rowNum", i)
        eventFormatter.pushElement("spanUpdate")
        eventFormatter.appendElement()
        eventFormatter.setElement("startCol", 1)
        eventFormatter.setElement("length", 10)
        eventFormatter.setElement("text", "RECAP")
        eventFormatter.popElement()
        eventFormatter.popElement()
        eventFormatter.popElement()

    eventFormatter.popElement()

def formatMarketDataRecapEvent(eventFormatter):
    eventFormatter.setElement("OPEN", 100.0)


def parseCmdLine():
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Interactive data publisher.")
    addConnectionAndAuthOptions(parser)

    publisher_group = parser.add_argument_group("Publisher Options")
    publisher_group.add_argument("-s", "--service",
                                 dest="service",
                                 help="the service name",
                                 required=True,
                                 metavar="service")
    publisher_group.add_argument("-g", "--group-id",
                                 dest="groupId",
                                 help="the group ID of the service, default to an "
                                 "automatically generated unique value",
                                 metavar="groupId")
    publisher_group.add_argument("-p", "--priority",
                                 type=int,
                                 dest="priority",
                                 help="the service priority (default: %(default)s)",
                                 metavar="priority",
                                 default=blpapi.ServiceRegistrationOptions.PRIORITY_HIGH)
    publisher_group.add_argument("--register-ssc",
                                 dest="ssc",
                                 help="specify active sub-service code range and "
                                 "priority separated by ','",
                                 metavar="begin,end,priority")
    publisher_group.add_argument("--clear-cache",
                                 type=int,
                                 dest="clearInterval",
                                 help="number of events after which cache will be "
                                 "cleared (default: 0 i.e cache never cleared)",
                                 metavar="eventCount",
                                 default=0)
    publisher_group.add_argument("--resolve-ssc",
                                 dest="rssc",
                                 type=int,
                                 help="sub-service code to be used in permission response",
                                 metavar="subServiceCode")
    publisher_group.add_argument("-E", "--eid",
                                 dest="eids",
                                 type=int,
                                 help="EIDs that are used in permission response. Can be specified multiple times.",
                                 metavar="eid",
                                 action="append",
                                 default=[])
    publisher_group.add_argument("-P", "--page",
                                 dest="isPageData",
                                 help="publish as page data",
                                 action="store_true",
                                 default=False)

    options = parser.parse_args()

    # Parse sub-service code range and priority
    if options.ssc:
        options.sscBegin, options.sscEnd, options.sscPriority = map(
            int, options.ssc.split(","))

    return options


def activate(options, session):
    if options.ssc:
        print("Activating sub service code range ["
              f"{options.sscBegin}, {options.sscEnd}] @ {options.sscPriority}")
        session.activateSubServiceCodeRange(options.service,
                                            options.sscBegin,
                                            options.sscEnd,
                                            options.sscPriority)


def deactivate(options, session):
    if options.ssc:
        print("Deactivating sub service code range ["
              f"{options.sscBegin}, {options.sscEnd}] @ {options.sscPriority}")
        session.deactivateSubServiceCodeRange(options.service,
                                              options.sscBegin,
                                              options.sscEnd)


def main():
    options = parseCmdLine()

    mutex = threading.Lock()
    stop = threading.Event()
    condition = threading.Condition(mutex)

    myEventHandler = MyEventHandler(options.service,
                                    options.eids,
                                    options.rssc,
                                    mutex,
                                    stop,
                                    condition,
                                    options.isPageData)

    sessionOptions = createSessionOptions(options)
    session = blpapi.ProviderSession(sessionOptions,
                                     myEventHandler.processEvent)

    if not session.start():
        print("Failed to start session.")
        return

    serviceOptions = blpapi.ServiceRegistrationOptions()
    if options.groupId is not None:
        serviceOptions.setGroupId(options.groupId)
    serviceOptions.setServicePriority(options.priority)

    if options.ssc:
        print("Adding active sub-service code range ["
              f"{options.sscBegin}, {options.sscEnd}] @ {options.sscPriority}")
        try:
            serviceOptions.addActiveSubServiceCodeRange(options.sscBegin,
                                                        options.sscEnd,
                                                        options.sscPriority)
        except blpapi.Exception as exception:
            print("FAILED to add active sub-service codes."
                  f" Exception {exception.description()}")

    try:
        if not session.registerService(options.service,
                                       session.getAuthorizedIdentity(),
                                       serviceOptions):
            print(f"Failed to register '{options.service}'")
            return

        service = session.getService(options.service)
        eventCount = 0
        while not stop.is_set():
            with condition:
                if not condition.wait_for(
                        lambda: len(myEventHandler.activeTopics) > 0,
                        timeout=1):
                    continue

            publishNull = False
            if options.clearInterval > 0 \
                    and eventCount == options.clearInterval:
                eventCount = 0
                publishNull = True

            event = service.createPublishEvent()
            eventFormatter = blpapi.EventFormatter(event)

            with mutex:
                for topic in myEventHandler.activeTopics:
                    if options.isPageData:
                        formatPageEvent(eventFormatter, topic, publishNull)
                    else:
                        formatMarketDataEvent(eventFormatter, topic, publishNull)

            print("Publishing event:")
            for msg in event:
                print(msg)

            session.publish(event)
            time.sleep(10)
            eventCount += 1
            if eventCount % 10 == 0:
                deactivate(options, session)
                time.sleep(30)
                activate(options, session)

    finally:
        print("Stopping the session")
        session.stop()

def formatMarketDataEvent(eventFormatter, topic, publishNull):
    # NOTE: This function demonstrates how to use the `Element`-based interface
    # of `EventFormatter` to format an `Event`. For an example of formatting an
    # `Event` using `EventFormatter.fromPy`, see
    # `BroadcastPublisherExample.formatMarketData`.
    MARKET_DATA_EVENTS = blpapi.Name("MarketDataEvents")
    HIGH = blpapi.Name("HIGH")
    LOW = blpapi.Name("LOW")

    eventFormatter.appendMessage(MARKET_DATA_EVENTS, topic)
    if publishNull:
        eventFormatter.setElementNull(HIGH)
        eventFormatter.setElementNull(LOW)
    else:
        secondsStr = time.strftime("%S", time.localtime())
        seconds = int(secondsStr)
        eventFormatter.setElement(HIGH, seconds * 1.0)
        eventFormatter.setElement(LOW, seconds * 0.5)


def formatPageEvent(eventFormatter, topic, publishNull):
    # NOTE: This function demonstrates how to use `EventFormatter.fromPy` to
    # format an `Event`. For an example of formatting an `Event` using the
    # `Element`-based` interface of `EventFormatter`, see
    # `BroadcastPublisherExample.formatPageData`.
    numRows = 5
    for i in range(1, numRows + 1):
        eventFormatter.appendMessage("RowUpdate", topic)

        secondsStr = time.strftime("%S", time.localtime())
        messageDict = {
            "rowNum": i
        }
        if publishNull:
            messageDict["spanUpdate"] = {}
        else:
            messageDict["spanUpdate"] = [
                {
                    "startCol": 1,
                    "length": len(secondsStr),
                    "text": secondsStr,
                }
            ]

        eventFormatter.fromPy(messageDict)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # pylint: disable=broad-except
        print(e)

__copyright__ = """
Copyright 2021, Bloomberg Finance L.P.

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
