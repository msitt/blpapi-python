from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi
from blpapi import Names

from util.SubscriptionOptions import \
    addSubscriptionOptions, \
    setSubscriptionSessionOptions, \
    createSubscriptionList
from util.ConnectionAndAuthOptions import \
    addConnectionAndAuthOptions, \
    createSessionOptions
from util.MaxEventsOption import addMaxEventsOption


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Subscription example with event polling")
    addSubscriptionOptions(parser)
    addConnectionAndAuthOptions(parser)
    addMaxEventsOption(parser)

    options = parser.parse_args()

    return options

def checkFailures(session):
    """Checks failure events published by the session."""

    # Note that the loop uses 'session.tryNextEvent' as all events have
    # been produced before calling this function, but there could be no events
    # at all in the queue if the OS fails to allocate resources.
    while True:
        event = session.tryNextEvent()
        if event is None:
            return

        eventType = event.eventType()
        for msg in event:
            print(msg)
            if processGenericMessage(eventType, msg):
                return

def processSubscriptionEvents(session, maxEvents):
    eventCount = 0
    while True:
        # Specify timeout to give a chance for Ctrl-C
        event = session.nextEvent(1000)
        eventType = event.eventType()
        for msg in event:
            print(msg)
            messageType = msg.messageType()
            messageCorrelationId = msg.correlationId()
            if eventType == blpapi.Event.SUBSCRIPTION_STATUS:
                if messageType == Names.SUBSCRIPTION_FAILURE \
                        or messageType == Names.SUBSCRIPTION_TERMINATED:
                    topic = messageCorrelationId.value()
                    print(f"Subscription failed for topic {topic}")
                    printContactSupportMessage(msg)
            elif eventType == blpapi.Event.SUBSCRIPTION_DATA:
                topic = messageCorrelationId.value()
                print(f"Received subscription data for topic {topic}")

                if msg.recapType() == blpapi.Message.RECAPTYPE_SOLICITED:
                    if msg.getRequestId() is not None:
                        # An init paint tick can have an associated
                        # RequestId that is used to identify the
                        # source of the data and can be used when
                        # contacting support
                        print(f"Received init paint with RequestId {msg.getRequestId()}")
            else:

                # SESSION_STATUS events can happen at any time and
                # should be handled as the session can be terminated,
                # e.g. session identity can be revoked at a later
                # time, which terminates the session.
                if processGenericMessage(eventType, msg):
                    return

        if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
            eventCount += 1
            if eventCount >= maxEvents:
                break

def processGenericMessage(eventType, message):
    """Prints error information if the 'message' is a failure message."""

    messageType = message.messageType()

    # When using a session identity, i.e.
    # 'SessionOptions.setSessionIdentityOptions(AuthOptions)', token
    # generation failure, authorization failure or revocation terminates the
    # session, in which case, applications only need to check session status
    # messages. Applications don't need to handle token or authorization messages
    if eventType == blpapi.Event.SESSION_STATUS:
        if messageType == Names.SESSION_TERMINATED or \
                messageType == Names.SESSION_STARTUP_FAILURE:
            print("Session failed to start or terminated")
            printContactSupportMessage(message)
            # Session failed to start/terminated
            return True
    elif eventType == blpapi.Event.SERVICE_STATUS:
        if messageType == Names.SERVICE_OPEN_FAILURE:
            serviceName = message.getElementAsString("serviceName")
            print(f"Failed to open {serviceName}")
            printContactSupportMessage(message)

    # Session OK
    return False

def printContactSupportMessage(msg):
    """Prints contact support message."""

    # Messages can have associated RequestIds which
    # identify operations (related to them) through the network.
    requestId = msg.getRequestId()
    if requestId is not None:
        print(f"When contacting support, please provide RequestId {requestId}")


def main():
    """Main function"""

    options = parseCmdLine()

    sessionOptions = createSessionOptions(options)
    setSubscriptionSessionOptions(sessionOptions, options)
    session = blpapi.Session(sessionOptions)

    try:
        if not session.start():
            checkFailures(session)
            print("Failed to start session.")
            return

        if not session.openService(options.service):
            checkFailures(session)
            return

        subscriptions = createSubscriptionList(options)
        session.subscribe(subscriptions)

        processSubscriptionEvents(session, options.maxEvents)
    finally:
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
