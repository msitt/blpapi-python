# ReferenceDataRequests.py

import blpapi

SECURITY_DATA = blpapi.Name("securityData")
SECURITY = blpapi.Name("security")
FIELD_DATA = blpapi.Name("fieldData")
RESPONSE_ERROR = blpapi.Name("responseError")
SECURITY_ERROR = blpapi.Name("securityError")
FIELD_EXCEPTIONS = blpapi.Name("fieldExceptions")
FIELD_ID = blpapi.Name("fieldId")
ERROR_INFO = blpapi.Name("errorInfo")
SECURITIES = blpapi.Name("securities")
FIELDS = blpapi.Name("fields")
OVERRIDES = blpapi.Name("overrides")
VALUE = blpapi.Name("value")
ROW = blpapi.Name("row")
TABLE_OVERRIDES = blpapi.Name("tableOverrides")


def createRequest(service, options):
    # NOTE: This function shows the `Element`-based interface of formatting
    # a `Request`. See `createTableOverrideRequest` for an example of
    # formatting a `Request` using `Request.fromPy`. See the other
    # `createRequest` functions in this `requestresponse` directory for
    # examples of alternative interfaces for formatting a `Request`.

    request = service.createRequest("ReferenceDataRequest")
    securitiesElement = request.getElement(SECURITIES)

    for security in options.securities:
        securitiesElement.appendValue(security)

    fieldsElement = request.getElement(FIELDS)
    for field in options.fields:
        fieldsElement.appendValue(field)

    if options.overrides:
        # Add overrides
        overridesElement = request.getElement(OVERRIDES)
        for override in options.overrides:
            overrideElement = overridesElement.appendElement()
            overrideElement.setElement(FIELD_ID, override.fieldId)
            overrideElement.setElement(VALUE, override.value)

    return request


def createTableOverrideRequest(service, options):
    # NOTE: This function shows how to format a `Request` using
    # `Request.fromPy`. See `createRequest` for an example of formatting a
    # `Request` using the `Element`-based interface.

    request = service.createRequest("ReferenceDataRequest")

    # (rate, duration, transition)
    rate1 = (1.0, 12, "S")  # S = Step
    rate2 = (2.0, 12, "R")  # R = Ramp

    requestDict = {
        SECURITIES: options.securities,
        FIELDS: options.fields,
        OVERRIDES: [
            {FIELD_ID: "ALLOW_DYNAMIC_CASHFLOW_CALCS", VALUE: "Y"},
            {FIELD_ID: "LOSS_SEVERITY", VALUE: 31},
        ],
        TABLE_OVERRIDES: [
            {
                FIELD_ID: "DEFAULT_VECTOR",
                ROW: [
                    {VALUE: ["Anchor", "PROJ"]},
                    {VALUE: ["Type", "CDR"]},
                    {VALUE: rate1},
                    {VALUE: rate2},
                ],
            }
        ],
    }
    request.fromPy(requestDict)

    return request


def processResponseEvent(event):
    # NOTE: This function shows the `Element` method interface for accessing
    # the contents of a `Message`. For examples of the `dict`-like interface,
    # see `IntradayTickRequests.processResponseEvent` and
    # `IntradayBarRequests.processResponseEvent`

    for msg in event:
        print(f"Received response to request {msg.getRequestId()}")

        if msg.hasElement(RESPONSE_ERROR):
            print(f"REQUEST FAILED: {msg.getElement(RESPONSE_ERROR)}")
            continue

        securities = msg.getElement(SECURITY_DATA)
        numSecurities = securities.numValues()
        print(f"Processing {numSecurities} securities:")

        for i in range(numSecurities):
            security = securities.getValueAsElement(i)
            ticker = security.getElementAsString(SECURITY)
            print(f"\nTicker: {ticker}")

            if security.hasElement(SECURITY_ERROR):
                print(
                    f"SECURITY FAILED: {security.getElement(SECURITY_ERROR)}"
                )
                continue

            if security.hasElement(FIELD_DATA):
                fields = security.getElement(FIELD_DATA)
                if fields.numElements() > 0:
                    print("FIELD\t\tVALUE")
                    print("-----\t\t-----")
                    numElements = fields.numElements()
                    for j in range(numElements):
                        field = fields.getElement(j)
                        print(f"{field.name()} \t\t {field} ")

            fieldExceptions = security.getElement(FIELD_EXCEPTIONS)
            if fieldExceptions.numValues() > 0:
                print("FIELD\t\tEXCEPTION")
                print("-----\t\t---------")
                for k in range(fieldExceptions.numValues()):
                    fieldException = fieldExceptions.getValueAsElement(k)
                    print(
                        f"{fieldException.getElementAsString(FIELD_ID)} "
                        f"\t\t {fieldException.getElement(ERROR_INFO)}"
                    )


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
