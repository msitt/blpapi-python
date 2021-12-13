from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions
from util.MaxEventsOption import addMaxEventsOption

from threading import Event
import time

DEFAULT_MARKET_DATA_TOPIC = "IBM Equity"
DEFAULT_PAGE_TOPIC = "1245/4/5"

class MyStream(object):
    def __init__(self, sid=""):
        self.id = sid


class MyEventHandler(object):
    def __init__(self, stop):
        self.stop = stop

    def processEvent(self, event, _session):
        for msg in event:
            print(msg)
            if event.eventType() == blpapi.Event.SESSION_STATUS:
                if msg.messageType() == blpapi.Names.SESSION_TERMINATED:
                    print("Received session terminated, stopping session")
                    self.stop.set()
                continue


def parseCmdLine():
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Broadcast data publisher.")

    addConnectionAndAuthOptions(parser)

    publisher_group = parser.add_argument_group("Broadcast Publisher Options")
    publisher_group.add_argument("-s", "--service",
                                 dest="service",
                                 help="the service name",
                                 required=True,
                                 metavar="service")
    publisher_group.add_argument("-t", "--topic",
                                 dest="topics",
                                 help="topic to publish (default: "
                                 f"{DEFAULT_MARKET_DATA_TOPIC}; or for page "
                                 f"data {DEFAULT_PAGE_TOPIC})."
                                 "Can be specified multiple times.",
                                 metavar="topic",
                                 action="append",
                                 default=[])
    publisher_group.add_argument("-g", "--group-id",
                                 dest="groupId",
                                 metavar="groupId",
                                 help="publisher groupId (default to an "
                                 "automatically generated unique value)")
    publisher_group.add_argument("-p", "--priority",
                                 dest="priority",
                                 metavar="priority",
                                 type=int,
                                 help="publisher's priority (default: %(default)d)",
                                 default=blpapi.ServiceRegistrationOptions.PRIORITY_HIGH)
    publisher_group.add_argument("--page",
                                 dest="isPageData",
                                 help="publish as page data",
                                 action="store_true",
                                 default=False)

    addMaxEventsOption(parser)

    options = parser.parse_args()

    if not options.topics:
        options.topics = [DEFAULT_PAGE_TOPIC] if options.isPageData \
            else [DEFAULT_MARKET_DATA_TOPIC]

    return options


def formatMarketData(eventFormatter, topic):
    # NOTE: This function demonstrates how to use `EventFormatter.fromPy` to
    # format an `Event`. For an example of formatting an `Event` using the
    # `Element`-based` interface of `EventFormatter`, see
    # `InteractivePublisherExample.formatMarketDataEvent`.
    MARKET_DATA_EVENTS = blpapi.Name("MarketDataEvents")
    HIGH = blpapi.Name("HIGH")
    LOW = blpapi.Name("LOW")

    eventFormatter.appendMessage(MARKET_DATA_EVENTS, topic)

    secondsStr = time.strftime("%S", time.localtime())
    seconds = int(secondsStr)
    messageDict = {
        HIGH: seconds * 1.0,
        LOW: seconds * 0.5
    }

    eventFormatter.fromPy(messageDict)

def formatPageData(eventFormatter, topic):
    # NOTE: This function demonstrates how to use the `Element`-based interface
    # of `EventFormatter` to format an `Event`. For an example of formatting an
    # `Event` using `EventFormatter.fromPy`, see
    # `InteractivePublisherExample.formatPageEvent`.
    numRows = 5
    for i in range(1, numRows + 1):
        eventFormatter.appendMessage("RowUpdate", topic)
        eventFormatter.setElement("rowNum", i)
        eventFormatter.pushElement("spanUpdate")
        eventFormatter.appendElement()
        eventFormatter.setElement("startCol", 1)
        secondsStr = time.strftime("%S", time.localtime())
        eventFormatter.setElement("length", len(secondsStr))
        eventFormatter.setElement("text", secondsStr)
        eventFormatter.popElement()

        eventFormatter.popElement()

def main():
    options = parseCmdLine()

    stop = Event()
    myEventHandler = MyEventHandler(stop)

    # Create a Session
    sessionOptions = createSessionOptions(options)
    session = blpapi.ProviderSession(sessionOptions,
                                     myEventHandler.processEvent)

    # Start a Session
    if not session.start():
        print("Failed to start session.")
        return

    if options.groupId is not None:
        # NOTE: perform explicit service registration here, instead
        # of letting createTopics() do it, as the latter approach doesn't
        # allow for custom ServiceRegistrationOptions.
        serviceOptions = blpapi.ServiceRegistrationOptions()
        serviceOptions.setGroupId(options.groupId)
        serviceOptions.setServicePriority(options.priority)
        if not session.registerService(options.service,
                                       session.getAuthorizedIdentity(),
                                       serviceOptions):
            print(f"Failed to register {options.service}")
            session.stop()
            return

    topicList = blpapi.TopicList()
    for topic in options.topics:
        userTopic = topic
        if userTopic and not userTopic.startswith("/"):
            userTopic = "/" + userTopic
        topicList.add(f"{options.service}{userTopic}",
                      blpapi.CorrelationId(MyStream(topic)))

    # createTopics() is synchronous, topicList will be updated with the
    # results of topic creation (resolution will happen under the covers)
    session.createTopics(topicList,
                         blpapi.ProviderSession.AUTO_REGISTER_SERVICES)

    streams = []
    for i in range(topicList.size()):
        stream = topicList.correlationIdAt(i).value()
        status = topicList.statusAt(i)
        topicString = topicList.topicStringAt(i)

        if (status == blpapi.TopicList.CREATED):
            print(f"Start publishing on topic: {topicString}")
            stream.topic = session.getTopic(topicList.messageAt(i))
            streams.append(stream)
        else:
            print(f"Stream '{stream.id}': topic not created, status = {status}")

    service = session.getService(options.service)

    if not streams:
        return

    try:
        eventCount = 0

        # Now we will start publishing
        while not stop.is_set() and eventCount < options.maxEvents:
            event = service.createPublishEvent()
            eventFormatter = blpapi.EventFormatter(event)

            for stream in streams:
                topic = stream.topic
                if options.isPageData:
                    formatPageData(eventFormatter, topic)
                else:
                    formatMarketData(eventFormatter, topic)

            print("Publishing event:")
            for msg in event:
                print(msg)

            session.publish(event)
            eventCount += 1
            time.sleep(10)
    finally:
        # Stop the session
        print("Stopping the session")
        session.stop()

if __name__ == "__main__":
    print("BroadcastPublisherExample")
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
