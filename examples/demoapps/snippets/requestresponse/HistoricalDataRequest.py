# HistoricalDataRequest.py

from blpapi import Name

SECURITIES = Name("securities")
PERIODICITY_ADJUSTMENT = Name("periodicityAdjustment")
PERIODICITY_SELECTION = Name("periodicitySelection")
START_DATE = Name("startDate")
END_DATE = Name("endDate")
MAX_DATA_POINTS = Name("maxDataPoints")
RETURN_EIDS = Name("returnEids")
FIELDS = Name("fields")


def createRequest(service, options):
    # NOTE: this function uses `Request.__setitem__` to format a `Request`. See
    # the other `createRequest` functions in this `requestresponse` directory
    # for examples of alternative interfaces for formatting a `Request`.
    # An alternative using `request.fromJson` is shown in the comments below.
    request = service.createRequest("HistoricalDataRequest")

    request[SECURITIES] = options.securities
    request[FIELDS] = options.fields

    request[PERIODICITY_ADJUSTMENT] = "ACTUAL"
    request[PERIODICITY_SELECTION] = "MONTHLY"
    request[START_DATE] = "20200101"
    request[END_DATE] = "20201231"
    request[MAX_DATA_POINTS] = 100
    request[RETURN_EIDS] = True

    # Alternative: Using `Request.fromJson` to format the request
    # import json
    # REQUEST_JSON = f"""
    # {{
    #     "securities": {json.dumps(options.securities)},
    #     "fields": {json.dumps(options.fields)},
    #     "periodicityAdjustment": "ACTUAL",
    #     "periodicitySelection": "MONTHLY",
    #     "startDate": "20200101",
    #     "endDate": "20201231",
    #     "maxDataPoints": 100,
    #     "returnEids": true
    # }}
    # """
    # request.fromJson(REQUEST_JSON)

    return request


def processResponseEvent(event):
    for msg in event:
        print(f"Received response to request {msg.getRequestId()}")
        print(msg)

        # Alternative: Using `Message.toJson` to convert the message to JSON
        # jsonStr = msg.toJson()
        # print(jsonStr)


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
