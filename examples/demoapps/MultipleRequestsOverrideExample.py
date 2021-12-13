from blpapi_import_helper import blpapi

from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions
from snippets.requestresponse import ReferenceDataRequests
from util.RequestOptions import Override, REFDATA_SERVICE
from collections import namedtuple
from argparse import ArgumentParser, RawTextHelpFormatter


def main():

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Multiple requests with override example")
    addConnectionAndAuthOptions(parser)
    options = parser.parse_args()

    sessionOptions = createSessionOptions(options)
    session = blpapi.Session(sessionOptions)

    try:
        if not session.start():
            print("Failed to connect!")
            return

        if not session.openService(REFDATA_SERVICE):
            print(f"Failed to open {REFDATA_SERVICE}")
            return

        service = session.getService(REFDATA_SERVICE)

        fieldIdVwapStartTime = "VWAP_START_TIME"
        fieldIdVwapEndTime = "VWAP_END_TIME"

        Options = namedtuple('Options', ['securities', 'fields', 'overrides'])

        # Request 1
        startTime1 = "9:30"
        endTime1 = "11:30"

        options = Options(["IBM US Equity", "MSFT US Equity"],
                          ["PX_LAST", "DS002"],
                          [Override(fieldIdVwapStartTime, startTime1),
                           Override(fieldIdVwapEndTime, endTime1)])

        request1 = ReferenceDataRequests.createRequest(service, options)

        print(f"Sending request 1: {request1}")
        correlationId1 = blpapi.CorrelationId("request 1")
        session.sendRequest(request1, correlationId=correlationId1)

        # Request 2
        startTime2 = "11:30"
        endTime2 = "13:30"

        options.overrides.clear()
        options.overrides.append(Override(fieldIdVwapStartTime, startTime2))
        options.overrides.append(Override(fieldIdVwapEndTime, endTime2))
        request2 = ReferenceDataRequests.createRequest(service, options)

        print(f"Sending request 2: {request2}")
        correlationId2 = blpapi.CorrelationId("request 2")
        session.sendRequest(request2, correlationId=correlationId2)

        # Wait for responses for both requests, expect 2 final responses
        # either failure or success.
        finalResponseCount = 0
        while finalResponseCount < 2:
            event = session.nextEvent()
            eventType = event.eventType()
            for msg in event:
                msgCorrelationId = msg.correlationId()
                if eventType == blpapi.Event.REQUEST_STATUS:
                    if msg.messageType() == blpapi.Names.REQUEST_FAILURE:
                        if correlationId1 == msgCorrelationId:
                            print("Request 1 failed.")
                        elif correlationId2 == msgCorrelationId:
                            print("Request 2 failed.")

                        finalResponseCount += 1
                elif eventType in [blpapi.Event.RESPONSE, blpapi.Event.PARTIAL_RESPONSE]:
                    if correlationId1 == msgCorrelationId:
                        print("Received response for request 1")
                    elif correlationId2 == msgCorrelationId:
                        print("Received response for request 2")

                    if eventType == blpapi.Event.RESPONSE:
                        finalResponseCount += 1

                print(msg)
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
