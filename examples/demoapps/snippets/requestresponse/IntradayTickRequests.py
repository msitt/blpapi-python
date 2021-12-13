# IntradayTickRequests.py

import blpapi

TICK_DATA = blpapi.Name("tickData")
CONDITION_CODES = blpapi.Name("conditionCodes")
SIZE = blpapi.Name("size")
TIME = blpapi.Name("time")
TYPE = blpapi.Name("type")
VALUE = blpapi.Name("value")
RESPONSE_ERROR = blpapi.Name("responseError")

DATETIME_FORMAT = "%m/%d/%Y %H:%M"


def createRequest(service, options):
    # NOTE: this function uses `Request.fromPy` to format a `Request`. See
    # the other `createRequest` functions in this `requestresponse` directory
    # for examples of alternative interfaces for formatting a `Request`.
    request = service.createRequest("IntradayTickRequest")

    requestDict = {
        "security": options.securities[0],
        "eventTypes": options.eventTypes,
        # All times are in GMT
        "startDateTime": options.startDateTime,
        "endDateTime": options.endDateTime,
    }
    if options.conditionCodes:
        requestDict["includeConditionCodes"] = True

    request.fromPy(requestDict)

    return request


def processResponseEvent(response):
    # NOTE: This function demonstrates the `dict`-like interface for accessing
    # the contents of a `Message`. For an example of explicitly converting a
    # `Message` to a `dict`, see the use of `Message.toPy` in
    # `IntradayBarRequests.processResponseEvent`.

    for msg in response:
        print(f"Received response to request {msg.getRequestId()}")

        if RESPONSE_ERROR in msg:
            responseError = msg[RESPONSE_ERROR]
            print(f"REQUEST FAILED: {responseError}")
            continue

        data = msg[TICK_DATA][TICK_DATA]
        print("TIME\t\t\tTYPE\t\tVALUE\t\tSIZE\tCONDITION_CODES")
        print("----\t\t\t----\t\t-----\t\t----\t----")
        for item in data:
            itemTime = item[TIME]
            itemType = item[TYPE]
            itemValue = item[VALUE]
            itemSize = item[SIZE]
            itemConditionCodes = ""
            if CONDITION_CODES in item:
                itemConditionCodes = item[CONDITION_CODES]

            print(f"{itemTime.strftime(DATETIME_FORMAT)}\t{itemType}\t"
                  f"{itemValue:.2f}\t\t{itemSize}\t{itemConditionCodes}")


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
