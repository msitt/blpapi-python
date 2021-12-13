import time

from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi

from util.SubscriptionOptions import \
    addSubscriptionOptions, \
    setSubscriptionSessionOptions, \
    createSubscriptionList
from util.ConnectionAndAuthOptions import \
    addConnectionAndAuthOptions, \
    createSessionOptions

DEFAULT_QUEUE_SIZE = 10000


class SubscriptionEventHandler(object):
    def getTimeStamp(self):
        return time.strftime("%Y/%m/%d %X")

    def processSubscriptionStatus(self, event):
        timeStamp = self.getTimeStamp()
        for msg in event:
            topic = msg.correlationId().value()
            print(f"{timeStamp}: {topic}")
            print(msg)
            if msg.messageType() == blpapi.Names.SUBSCRIPTION_FAILURE:
                print(f"Subscription for {topic} failed")
            elif msg.messageType() == blpapi.Names.SUBSCRIPTION_TERMINATED:
                # Subscription can be terminated if the session identity
                # is revoked.
                print(f"Subscription for {topic} TERMINATED")

    def processSubscriptionDataEvent(self, event):
        timeStamp = self.getTimeStamp()
        for msg in event:
            topic = msg.correlationId().value()
            print(f"{timeStamp}: {topic}")
            print(msg)

    def processMiscEvents(self, event):
        for msg in event:
            if msg.messageType() == blpapi.Names.SLOW_CONSUMER_WARNING:
                print(f"{blpapi.Names.SLOW_CONSUMER_WARNING} - The event queue is " +
                      "beginning to approach its maximum capacity and " +
                      "the application is not processing the data fast " +
                      "enough. This could lead to ticks being dropped" +
                      " (DataLoss).\n")
            elif msg.messageType() == blpapi.Names.SLOW_CONSUMER_WARNING_CLEARED:
                print(f"{blpapi.Names.SLOW_CONSUMER_WARNING_CLEARED} - the event " +
                      "queue has shrunk enough that there is no " +
                      "longer any immediate danger of overflowing the " +
                      "queue. If any precautionary actions were taken " +
                      "when SlowConsumerWarning message was delivered, " +
                      "it is now safe to continue as normal.\n")
            elif msg.messageType() == blpapi.Names.DATA_LOSS:
                print(msg)
                topic = msg.correlationId().value()
                print(f"{blpapi.Names.DATA_LOSS} - The application is too slow to " +
                      "process events and the event queue is overflowing. " +
                      f"Data is lost for topic {topic}.\n")
            elif event.eventType() == blpapi.Event.SESSION_STATUS:
                # SESSION_STATUS events can happen at any time and
                # should be handled as the session can be terminated,
                # e.g. session identity can be revoked at a later
                # time, which terminates the session.
                if msg.messageType() == blpapi.Names.SESSION_TERMINATED:
                    print("Session terminated")
                    return

    def processEvent(self, event, _session):
        try:
            if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                self.processSubscriptionDataEvent(event)
            elif event.eventType() == blpapi.Event.SUBSCRIPTION_STATUS:
                self.processSubscriptionStatus(event)
            else:
                self.processMiscEvents(event)
        except blpapi.Exception as exception:
            print(f"Failed to process event {event}: {exception}")
        return False


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Asynchronous subscription with event handler")
    addConnectionAndAuthOptions(parser)
    addSubscriptionOptions(parser)

    parser.add_argument(
        "-q",
        "--event-queue-size",
        dest="eventQueueSize",
        help="The maximum number of events that is buffered by the session (default: %(default)d)",
        type=int,
        metavar="eventQueueSize",
        default=DEFAULT_QUEUE_SIZE)

    options = parser.parse_args()

    return options


def main():
    options = parseCmdLine()

    sessionOptions = createSessionOptions(options)
    setSubscriptionSessionOptions(sessionOptions, options)
    sessionOptions.setMaxEventQueueSize(options.eventQueueSize)
    handler = SubscriptionEventHandler()
    session = blpapi.Session(sessionOptions, handler.processEvent)

    try:
        if not session.start():
            print("Failed to start session.")
            return

        if not session.openService(options.service):
            print("Failed to open service.")
            return

        subscriptions = createSubscriptionList(options)
        session.subscribe(subscriptions)

        print("Press ENTER to quit")
        input()

    finally:
        session.stop()


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
