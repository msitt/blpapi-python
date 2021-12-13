from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions

from snippets.apiflds import CategorizedFieldSearchRequests
from snippets.apiflds import FieldInfoRequests
from snippets.apiflds import FieldListRequests
from snippets.apiflds import FieldSearchRequests

APIFLDS_SVC = "//blp/apiflds"

CATEGORIZED_FIELD_SEARCH_REQUEST = "CategorizedFieldSearchRequest"
FIELD_INFO_REQUEST = "FieldInfoRequest"
FIELD_LIST_REQUEST = "FieldListRequest"
FIELD_SEARCH_REQUEST = "FieldSearchRequest"


def createRequest(requestType, session):
    """Sends a request based on the request type."""

    apifldsService = session.getService(APIFLDS_SVC)
    if requestType == CATEGORIZED_FIELD_SEARCH_REQUEST:
        return CategorizedFieldSearchRequests.createRequest(apifldsService)

    if requestType == FIELD_INFO_REQUEST:
        return FieldInfoRequests.createRequest(apifldsService)

    if requestType == FIELD_LIST_REQUEST:
        return FieldListRequests.createRequest(apifldsService)

    if requestType == FIELD_SEARCH_REQUEST:
        return FieldSearchRequests.createRequest(apifldsService)


def processResponse(requestType, event):
    """Processes a response to the request."""

    if requestType == CATEGORIZED_FIELD_SEARCH_REQUEST:
        return CategorizedFieldSearchRequests.processResponse(event)

    if requestType == FIELD_INFO_REQUEST:
        return FieldInfoRequests.processResponse(event)

    if requestType == FIELD_LIST_REQUEST:
        return FieldListRequests.processResponse(event)

    if requestType == FIELD_SEARCH_REQUEST:
        return FieldSearchRequests.processResponse(event)


def main():
    parser = ArgumentParser(
        description="Retrieve API data fields",
        formatter_class=RawTextHelpFormatter)
    addConnectionAndAuthOptions(parser)
    parser.add_argument("-r",
                        "--request",
                        dest="requestType",
                        help="API fields request type, choices are: %(choices)s",
                        required=True,
                        choices=[CATEGORIZED_FIELD_SEARCH_REQUEST,
                                 FIELD_INFO_REQUEST,
                                 FIELD_LIST_REQUEST,
                                 FIELD_SEARCH_REQUEST],
                        metavar="requestType")

    options = parser.parse_args()

    sessionOptions = createSessionOptions(options)

    session = blpapi.Session(sessionOptions)

    try:
        if not session.start():
            print("Failed to start session.")
            return

        if not session.openService(APIFLDS_SVC):
            print(f"Failed to open {APIFLDS_SVC}.")
            return

        request = createRequest(options.requestType, session)
        print(f"Sending Request: {request}")
        session.sendRequest(request)

        done = False
        while not done:
            event = session.nextEvent()
            eventType = event.eventType()
            if eventType == blpapi.Event.REQUEST_STATUS:
                for msg in event:
                    if msg.messageType() == blpapi.Names.REQUEST_FAILURE:

                        # Request has failed, exit
                        print(msg)
                        done = True
                        break
            elif eventType in [blpapi.Event.RESPONSE,
                               blpapi.Event.PARTIAL_RESPONSE]:

                processResponse(options.requestType, event)

                # Received the final response, no further response events are
                # expected.
                if eventType == blpapi.Event.RESPONSE:
                    done = True
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
