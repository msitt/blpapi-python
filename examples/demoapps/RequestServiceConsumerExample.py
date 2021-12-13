from blpapi_import_helper import blpapi
from util.ConnectionAndAuthOptions import addConnectionAndAuthOptions, createSessionOptions
from argparse import ArgumentParser, RawTextHelpFormatter
import time

SERVICE = "//example/refdata"
TIMESTAMP = blpapi.Name("timestamp")
FIELDS = blpapi.Name("fields")
SECURITIES = blpapi.Name("securities")


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Request service consumer example, to be used in "
                                        "conjunction with RequestServiceProviderExample")
    addConnectionAndAuthOptions(parser)
    options = parser.parse_args()
    return options


def main():
    options = parseCmdLine()
    sessionOptions = createSessionOptions(options)
    session = blpapi.Session(sessionOptions)

    try:
        if not session.start():
            print("Failed to start session.")
            return

        if not session.openService(SERVICE):
            print(f"Failed to open {SERVICE}")
            return

        service = session.getService(SERVICE)
        request = service.createRequest("ReferenceDataRequest")

        # Add securities to request
        securitiesElement = request.getElement(SECURITIES)
        securitiesElement.appendValue("IBM US Equity")
        securitiesElement.appendValue("MSFT US Equity")

        # Add fields to request
        fieldsElement = request.getElement(FIELDS)
        fieldsElement.appendValue("PX_LAST")
        fieldsElement.appendValue("DS002")

        # Set time stamp
        request.set("timestamp", time.time())

        print(f"Sending Request: {request}")

        session.sendRequest(request)

        done = True
        while done:
            event = session.nextEvent()

            for msg in event:
                if msg.messageType() == blpapi.Names.REQUEST_FAILURE:
                    print("Request failed!")
                    done = False
                    break
                if msg.hasElement(TIMESTAMP):
                    responseTime = msg.getElementAsFloat(TIMESTAMP)
                    print(f"Response latency = {time.time() - responseTime}")
                print(msg)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

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
