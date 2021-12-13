from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi

from snippets.requestresponse import IntradayTickRequests
from snippets.requestresponse import IntradayBarRequests
from snippets.requestresponse import ReferenceDataRequests
from snippets.requestresponse import HistoricalDataRequest
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions
from util.RequestOptions import addRequestOptions, setDefaultValues, \
    REFERENCE_DATA_REQUEST_TABLE_OVERRIDE, REFERENCE_DATA_REQUEST_OVERRIDE, INTRADAY_BAR_REQUEST, \
    INTRADAY_TICK_REQUEST, REFERENCE_DATA_REQUEST, HISTORICAL_DATA_REQUEST


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Request/Response Example")
    addConnectionAndAuthOptions(parser)
    addRequestOptions(parser)

    options = parser.parse_args()
    setDefaultValues(options)

    return options


def processGenericEvent(event):
    """Prints the messages in the event."""

    # When using a session identity, token generation
    # failure, authorization failure or revocation terminates
    # the session, in which case, applications only need to
    # check session status messages. Applications don't need
    # to handle token or authorization messages, which are
    # still printed. Will return True if session has failed
    # to start or is terminated. False will be returned if otherwise.

    eventType = event.eventType()
    for msg in event:
        print(msg)
        messageType = msg.messageType()
        if eventType == blpapi.Event.SESSION_STATUS:
            if messageType == blpapi.Names.SESSION_TERMINATED \
                    or messageType == blpapi.Names.SESSION_STARTUP_FAILURE:
                print("Session failed to start or terminated.")
                printContactSupportMessage(msg)
                return True
        elif eventType == blpapi.Event.SERVICE_STATUS:
            if messageType == blpapi.Names.SERVICE_OPEN_FAILURE:
                serviceName = msg.getElementAsString("serviceName")
                print(f"Failed to open {serviceName}")
                printContactSupportMessage(msg)

    return False


def checkFailures(session):
    """Checks failure events published by the session."""

    # Note that the loop uses `Session.tryNextEvent()` as all events have
    # been produced before calling this function, but there could be no events
    # at all in the queue if the OS fails to allocate resources.

    while True:
        event = session.tryNextEvent()
        if event is None:
            break
        if processGenericEvent(event):
            break


def printContactSupportMessage(msg):
    """Prints RequestId associated with a Message"""

    # Messages can have an associated RequestId
    # that is used to identify operations (related to them)
    # through the network.

    requestId = msg.getRequestId()
    if requestId is not None:
        print(f"When contacting support, please provide RequestId {requestId}")


def sendRequest(options, session):
    """Sends a request based on the request type."""
    service = session.getService(options.service)
    requestType = options.requestType
    if requestType == INTRADAY_BAR_REQUEST:
        request = IntradayBarRequests.createRequest(service, options)
    elif requestType == INTRADAY_TICK_REQUEST:
        request = IntradayTickRequests.createRequest(service, options)
    elif requestType in [REFERENCE_DATA_REQUEST, REFERENCE_DATA_REQUEST_OVERRIDE]:
        request = ReferenceDataRequests.createRequest(service, options)
    elif requestType == REFERENCE_DATA_REQUEST_TABLE_OVERRIDE:
        request = ReferenceDataRequests.createTableOverrideRequest(
            service, options)
    elif requestType == HISTORICAL_DATA_REQUEST:
        request = HistoricalDataRequest.createRequest(service, options)

    # Every request has a RequestId, which is automatically generated, and
    # used to identify the operation through the network and also present
    # in the response messages. The RequestId should be provided when
    # contacting support.
    print(f"Sending Request {request.getRequestId()}: {request}")
    session.sendRequest(request,
                        None)  # correlationId


def waitForResponse(session, requestType):
    """Waits for response after sending the request"""

    # Success response can come with a number of
    # PARTIAL_RESPONSE events followed by a RESPONSE event.
    # Failures will be delivered in a REQUEST_STATUS event
    # holding a REQUEST_FAILURE message.

    done = False
    while not done:
        event = session.nextEvent()
        eventType = event.eventType()
        if eventType == blpapi.Event.PARTIAL_RESPONSE:
            print("Processing Partial Response")
            processResponseEvent(event, requestType)
        elif eventType == blpapi.Event.RESPONSE:
            print("Processing Response")
            processResponseEvent(event, requestType)
            done = True
        elif eventType == blpapi.Event.REQUEST_STATUS:
            for msg in event:
                print(msg)
                if msg.messageType == blpapi.Names.REQUEST_FAILURE:
                    reason = msg.getElement("reason")
                    print(f"Request failed: {reason}")
                    printContactSupportMessage(msg)
                    done = True
        else:
            # SESSION_STATUS events can happen at any time and should be
            # handled as the session can be terminated, e.g.
            # session identity can be revoked at a later time, which
            # terminates the session.
            done = processGenericEvent(event)


def processResponseEvent(event, requestType):
    """Processes a response to the request."""
    if requestType == INTRADAY_BAR_REQUEST:
        IntradayBarRequests.processResponseEvent(event)
    elif requestType == INTRADAY_TICK_REQUEST:
        IntradayTickRequests.processResponseEvent(event)
    elif requestType in [REFERENCE_DATA_REQUEST,
                         REFERENCE_DATA_REQUEST_OVERRIDE,
                         REFERENCE_DATA_REQUEST_TABLE_OVERRIDE]:
        ReferenceDataRequests.processResponseEvent(event)
    elif requestType == HISTORICAL_DATA_REQUEST:
        HistoricalDataRequest.processResponseEvent(event)


def main():
    """Main function"""

    options = parseCmdLine()

    sessionOptions = createSessionOptions(options)
    session = blpapi.Session(sessionOptions)

    try:
        if not session.start():
            checkFailures(session)
            print("Failed to start session.")
            return

        if not session.openService(options.service):
            checkFailures(session)
            return

        sendRequest(options, session)
        waitForResponse(session, options.requestType)

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
furnished to do so, subject to the following conditions: The above copyright
notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
"""
