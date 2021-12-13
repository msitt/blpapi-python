import time
from threading import Event
from argparse import ArgumentParser, RawTextHelpFormatter
from blpapi_import_helper import blpapi
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions
from util.MaxEventsOption import addMaxEventsOption

MARKET_DATA = blpapi.Name("MarketData")
PAGE_DATA = blpapi.Name("PageData")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")
BID = blpapi.Name("BID")
ASK = blpapi.Name("ASK")
ROW_UPDATE = blpapi.Name("rowUpdate")
ROW_NUM = blpapi.Name("rowNum")
SPAN_UPDATE = blpapi.Name("spanUpdate")
START_COL = blpapi.Name("startCol")
LENGTH = blpapi.Name("length")
TEXT = blpapi.Name("text")
ATTR = blpapi.Name("attr")
CONTRIBUTION_ID = blpapi.Name("contributorId")
PRODUCT_CODE = blpapi.Name("productCode")
PAGE_NUMBER = blpapi.Name("pageNumber")
DEFAULT_MKT_DATA_TOPIC = "/ticker/AUDEUR Curncy"
DEFAULT_PAGE_DATA_TOPIC = "/page/220/660/1"
DATETIME_FORMAT = "%m/%d/%Y %H:%M"

class MyEventHandler(object):
    """Event handler for the session"""

    def __init__(self, stop):
        """ Construct a handler """
        self.stop = stop

    def processEvent(self, event, _sesssion):
        """Process session event"""

        for msg in event:
            print(msg)
            if event.eventType() == blpapi.Event.SESSION_STATUS:
                if msg.messageType() == SESSION_TERMINATED:
                    self.stop.set()
                continue

def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(
        description="Contribute market or page data to a topic",
        formatter_class=RawTextHelpFormatter)
    addConnectionAndAuthOptions(parser)
    addMaxEventsOption(parser)

    parser.add_argument("-s",
                        "--service",
                        dest="service",
                        help="service name (default: %(default)s)",
                        metavar="service",
                        default="//blp/mpfbapi")
    parser.add_argument("-t",
                        "--topic",
                        dest="topic",
                        help=f"topic to contribute (mktdata default: '{DEFAULT_MKT_DATA_TOPIC}'"
                        f", page default: '{DEFAULT_PAGE_DATA_TOPIC}')",
                        metavar="topic")

    # Page contributions options
    parser.add_argument("-P",
                        "--page",
                        dest="page_enabled",
                        action='store_true',
                        help="enable page contributions")
    parser.add_argument("-C",
                        "--contribution-id",
                        dest="contributionId",
                        help="contributor id (default: %(default)d), ignored unless page is enabled",
                        metavar="contributionId",
                        type=int,
                        default=8563)

    options = parser.parse_args()

    if not options.topic:
        options.topic = DEFAULT_MKT_DATA_TOPIC
        if options.page_enabled:
            options.topic = DEFAULT_PAGE_DATA_TOPIC
    elif options.topic[0] != '/':
        options.topic = f"/{options.topic}"

    return options

def formatMktDataEvent(eventFormatter, topic, value):
    """Format a Mktdata event. """
    eventFormatter.appendMessage(MARKET_DATA, topic)
    eventFormatter.setElement(BID, 0.5 * value)
    eventFormatter.setElement(ASK, value)

def formatPageDataEvent(eventFormatter, topic, contributorId):
    """Format a PageData event. """
    tm = time.strftime("%X")
    messageDict = {
        ROW_UPDATE: [
            {
                ROW_NUM: 1,
                SPAN_UPDATE: [
                    {
                        START_COL: 20,
                        LENGTH: 4,
                        TEXT: "TEST"
                    },
                    {
                        START_COL: 25,
                        LENGTH: 4,
                        TEXT: "PAGE"
                    },
                    {
                        START_COL: 30,
                        LENGTH: len(tm),
                        TEXT: tm,
                        ATTR: "BLINK"
                    }
                ]
            },
            {
                ROW_NUM: 2,
                SPAN_UPDATE: [
                    {
                        START_COL: 20,
                        LENGTH: 9,
                        TEXT: "---------",
                        ATTR: "UNDERLINE"
                    },
                ]
            },
            {
                ROW_NUM: 3,
                SPAN_UPDATE: [
                    {
                        START_COL: 10,
                        LENGTH: 9,
                        TEXT: "TEST LINE",
                    },
                    {
                        START_COL: 23,
                        LENGTH: 5,
                        TEXT: "THREE",
                    },
                ]
            }
        ],
        CONTRIBUTION_ID: contributorId,
        PRODUCT_CODE: 1,
        PAGE_NUMBER: 1,
    }

    eventFormatter.appendMessage(PAGE_DATA, topic)
    eventFormatter.fromPy(messageDict)

def main():
    """Main function"""

    options = parseCmdLine()

    sessionOptions = createSessionOptions(options)

    stop = Event()
    myEventHandler = MyEventHandler(stop)

    # Create a Session
    session = blpapi.ProviderSession(sessionOptions,
                                     myEventHandler.processEvent)

    try:
        # Start a Session
        if not session.start():
            print("Failed to start session.")
            return

        topicList = blpapi.TopicList()
        topicList.add(options.service + options.topic,
                      blpapi.CorrelationId(options.topic))

        # Create topics
        session.createTopics(topicList,
                             blpapi.ProviderSession.AUTO_REGISTER_SERVICES)
        # createTopics() is synchronous, topicList will be updated
        # with the results of topic creation (resolution will happen
        # under the covers)

        status = topicList.statusAt(0)

        if status == blpapi.TopicList.CREATED:
            topic = session.getTopic(topicList.messageAt(0))
        else:
            print(f"Topic not resolved, status = {status}")
            return

        service = session.getService(options.service)

        for i in range(int(options.maxEvents)):
            if stop.is_set():
                break

            # Now we will start publishing
            event = service.createPublishEvent()
            eventFormatter = blpapi.EventFormatter(event)

            if options.page_enabled:
                formatPageDataEvent(
                    eventFormatter, topic, options.contributionId)
            else:
                formatMktDataEvent(eventFormatter, topic, i)

            print(time.strftime("%X") + " -\nPublishing event: ")
            for msg in event:
                print(msg)

            session.publish(event)
            time.sleep(10)
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e: # pylint: disable=broad-except
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
