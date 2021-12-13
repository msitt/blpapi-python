# IntradayBarRequests.py

BAR_DATA = "barData"
BAR_TICK_DATA = "barTickData"
OPEN = "open"
HIGH = "high"
LOW = "low"
CLOSE = "close"
VOLUME = "volume"
NUM_EVENTS = "numEvents"
TIME = "time"
RESPONSE_ERROR = "responseError"
CATEGORY = "category"
MESSAGE = "message"

DATETIME_FORMAT = "%m/%d/%Y %H:%M"


def createRequest(service, options):
    # NOTE: this function uses `Request.set` to format a `Request`. See
    # the other `createRequest` functions in this `requestresponse` directory
    # for examples of alternative interfaces for formatting a `Request`.
    request = service.createRequest("IntradayBarRequest")

    # Only one security / eventType per request
    request.set("security", options.securities[0])
    request.set("eventType", options.eventTypes[0])
    request.set("interval", options.barInterval)

    request.set("startDateTime", options.startDateTime)
    request.set("endDateTime", options.endDateTime)

    if options.gapFillInitialBar:
        request.set("gapFillInitialBar", options.gapFillInitialBar)

    return request


def processResponseEvent(response):
    # NOTE: This function demonstrates the use of `Message.toPy` for accessing
    # the contents of a `Message`. Here, the contents of the `Message` get
    # converted to a `dict`. See `IntradayTickRequests.processResponseEvent`
    # for an example of accessing the contents of a `Message` using
    # `Message.__getitem__`, without having to convert to a `dict`.

    for msg in response:
        print(f"Received response to request {msg.getRequestId()}")

        msgDict = msg.toPy()

        if RESPONSE_ERROR in msgDict:
            responseError = msg[RESPONSE_ERROR]
            print(f"REQUEST FAILED: {responseError}")
            continue

        data = msgDict[BAR_DATA][BAR_TICK_DATA]
        print(f"Response contains {len(data)} bar(s)")
        spaces = "\t\t\t\t"
        print(f"Datetime{spaces}Open{spaces}High{spaces}Low{spaces}Close{spaces}NumEvents{spaces}Volume")
        for bar in data:
            barTime = bar[TIME]
            barOpen = bar[OPEN]
            barHigh = bar[HIGH]
            barLow = bar[LOW]
            barClose = bar[CLOSE]
            barNumEvents = bar[NUM_EVENTS]
            barVolume = bar[VOLUME]

            print(f"{barTime.strftime(DATETIME_FORMAT)}{spaces}{barOpen:.2f}"
                  f"{spaces}{barHigh:.2f}{spaces}{barLow:.2f}{spaces}"
                  f"{barClose:.2f}{spaces}{barNumEvents}{spaces}{barVolume}")


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
