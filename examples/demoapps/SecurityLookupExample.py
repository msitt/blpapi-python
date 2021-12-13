from argparse import Action, ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi

from snippets.instruments import CurveListRequests
from snippets.instruments import GovtListRequests
from snippets.instruments import InstrumentListRequests
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions
from collections import namedtuple

INSTRUMENT_SERVICE = "//blp/instruments"

INSTRUMENT_LIST_REQUEST = "instrumentListRequest"
CURVE_LIST_REQUEST = "curveListRequest"
GOVT_LIST_REQUEST = "govtListRequest"

FILTERS_INSTRUMENTS = ["yellowKeyFilter", "languageOverride"]
FILTERS_GOVT = ["ticker", "partialMatch"]
FILTERS_CURVE = [
    "countryCode",
    "currencyCode",
    "type",
    "subtype",
    "curveid",
    "bbgid"
]

REQUEST_FAILURE = blpapi.Name("RequestFailure")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")
SESSION_STARTUP_FAILURE = blpapi.Name("SessionStartupFailure")
SERVICE_OPEN_FAILURE = blpapi.Name("ServiceOpenFailure")

# Defines a filter that is used in a //blp/instruments request.
InstrumentsFilter = namedtuple('InstrumentsFilter', ['name', 'value'])


class FilterAction(Action):
    """The action that parses filter options from user input"""

    def __call__(self, parser, args, values, option_string=None):
        vals = values.split('=', 1)
        if len(vals) != 2:
            parser.error(f"Invalid filter option '{values}'")

        filters = getattr(args, self.dest)
        filters.append(InstrumentsFilter(vals[0], vals[1]))


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Security Lookup Example")

    addConnectionAndAuthOptions(parser)

    lookup_group = parser.add_argument_group("Security Lookup Options")
    lookup_group.add_argument("-r", "--request",
                              dest="requestType",
                              choices=[INSTRUMENT_LIST_REQUEST,
                                       CURVE_LIST_REQUEST,
                                       GOVT_LIST_REQUEST],
                              help="specify the request type (default: %(default)s)",
                              metavar="requestType",
                              default=INSTRUMENT_LIST_REQUEST)
    lookup_group.add_argument("-S", "--security",
                              dest="query",
                              help="security query string",
                              metavar="security")
    lookup_group.add_argument("--max-results",
                              dest="maxResults",
                              help="max results returned in the response (default: %(default)d)",
                              metavar="maxResults",
                              type=int,
                              default=10)
    lookup_group.add_argument("-F", "--filter",
                              dest="filters",
                              help=f'''filter and value separated by '=', e.g., countryCode=US. Can be specified multiple times.
The applicable filters for each request:
{INSTRUMENT_LIST_REQUEST}: {FILTERS_INSTRUMENTS}
{CURVE_LIST_REQUEST} : {FILTERS_CURVE}
{GOVT_LIST_REQUEST} : {FILTERS_GOVT}''',
                              metavar="<filter>=<value>",
                              action=FilterAction,
                              default=[])

    options = parser.parse_args()

    return options


def sendRequest(options, session):
    """Sends a request based on the request type."""
    instrumentsService = session.getService(INSTRUMENT_SERVICE)
    requestType = options.requestType
    if requestType == CURVE_LIST_REQUEST:
        request = CurveListRequests.createRequest(
            instrumentsService,
            options.query,
            options.maxResults,
            options.filters)
    elif requestType == GOVT_LIST_REQUEST:
        request = GovtListRequests.createRequest(
            instrumentsService,
            options.query,
            options.maxResults,
            options.filters)
    elif requestType == INSTRUMENT_LIST_REQUEST:
        request = InstrumentListRequests.createRequest(
            instrumentsService,
            options.query,
            options.maxResults,
            options.filters)

    print(f"Sending Request {request}")
    session.sendRequest(request)


def waitForResponse(session, requestType):
    """Waits for response after sending the request"""

    # Success response can come with a number of PARTIAL_RESPONSE events
    # followed by a RESPONSE event.
    # Failures will be delivered in a REQUEST_STATUS event holding a
    # REQUEST_FAILURE message.

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
        else:
            for msg in event:
                if eventType == blpapi.Event.REQUEST_STATUS:
                    if msg.messageType() == REQUEST_FAILURE:
                        print(f"Request failed: {msg}")
                        done = True
                if eventType == blpapi.Event.SESSION_STATUS:
                    if msg.messageType() == SESSION_TERMINATED:
                        print(f"Session terminated: {msg}")
                        done = True


def processResponseEvent(event, requestType):
    """Processes a response to the request."""
    if requestType == CURVE_LIST_REQUEST:
        CurveListRequests.processResponse(event)
    elif requestType == GOVT_LIST_REQUEST:
        GovtListRequests.processResponse(event)
    elif requestType == INSTRUMENT_LIST_REQUEST:
        InstrumentListRequests.processResponse(event)


def main():
    """Main function"""

    options = parseCmdLine()
    sessionOptions = createSessionOptions(options)

    session = blpapi.Session(sessionOptions)
    try:
        if not session.start():
            print("Failed to start session.")
            return

        if not session.openService(INSTRUMENT_SERVICE):
            print(f"Failed to open {INSTRUMENT_SERVICE}")
            return

        sendRequest(options, session)
        waitForResponse(session, options.requestType)
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
