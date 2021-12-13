from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions

import time

SERVICE = "//example/refdata"
SESSION_TERMINATED = blpapi.Name("SessionTerminated")
REFERENCE_DATA_REQUEST = blpapi.Name("ReferenceDataRequest")
TIMESTAMP = blpapi.Name("timestamp")
FIELD_DATA = blpapi.Name("fieldData")
FIELD_ID = blpapi.Name("fieldId")
FIELDS = blpapi.Name("fields")
SECURITY = blpapi.Name("security")
SECURITIES = blpapi.Name("securities")
SECURITY_DATA = blpapi.Name("securityData")
DATA = blpapi.Name("data")
DOUBLE_VALUE = blpapi.Name("doubleValue")


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Request service provider example, to be used in "
                                        "conjunction with RequestServiceConsumerExample")
    addConnectionAndAuthOptions(parser)
    options = parser.parse_args()
    return options


def processEvent(event, session):

    print("Server received an event")

    if event.eventType() == blpapi.Event.REQUEST:
        service = session.getService(SERVICE)
        for msg in event:
            print(msg)

            if msg.messageType() == REFERENCE_DATA_REQUEST:
                if msg.hasElement(TIMESTAMP):
                    requestTime = msg.getElementAsFloat(TIMESTAMP)
                    latency = time.time() - requestTime
                    print(f"Request latency = {latency}")

                # A response event must contain only one response
                # message and attach the correlation ID of the request
                # message.
                response = service.createResponseEvent(msg.correlationId())
                ef = blpapi.EventFormatter(response)

                # The parameter of EventFormatter.appendResponse(Name)
                # is the name of the operation instead of the response.
                ef.appendResponse(REFERENCE_DATA_REQUEST)
                securities = msg.getElement(SECURITIES)
                fields = msg.getElement(FIELDS)
                ef.setElement(TIMESTAMP, time.time())
                ef.pushElement(SECURITY_DATA)
                for security in securities.values():
                    ef.appendElement()
                    ef.setElement(SECURITY, security)
                    ef.pushElement(FIELD_DATA)

                    for field in fields.values():
                        ef.appendElement()
                        ef.setElement(FIELD_ID, field)
                        ef.pushElement(DATA)
                        ef.setElement(DOUBLE_VALUE, time.time())
                        ef.popElement()
                        ef.popElement()

                    ef.popElement()
                    ef.popElement()

                ef.popElement()

                print("Publishing Response")
                for responseMsg in response:
                    print(responseMsg)
                session.sendResponse(response)

        print("Waiting for requests..., Press ENTER to quit")

    else:
        for msg in event:
            print(msg)

    return True


def main():
    options = parseCmdLine()
    sessionOptions = createSessionOptions(options)

    providerSession = blpapi.ProviderSession(sessionOptions, processEvent)

    try:
        if not providerSession.start():
            print("Failed to start session.")
            return

        if not providerSession.registerService(SERVICE):
            print(f"Failed to register {SERVICE}")
            return

        # wait for enter key to exit application
        print("Press ENTER to quit")
        input()

    finally:
        providerSession.stop()


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
