# SimpleFieldInfoExample.py

import blpapi
from optparse import OptionParser


APIFLDS_SVC = "//blp/apiflds"
PADDING = "                                            "

FIELD_ID = blpapi.Name("id")
FIELD_MNEMONIC = blpapi.Name("mnemonic")
FIELD_DATA = blpapi.Name("fieldData")
FIELD_DESC = blpapi.Name("description")
FIELD_INFO = blpapi.Name("fieldInfo")
FIELD_ERROR = blpapi.Name("fieldError")
FIELD_MSG = blpapi.Name("message")

ID_LEN = 13
MNEMONIC_LEN = 36
DESC_LEN = 40


def parseCmdLine():
    parser = OptionParser(description="Retrieve reference data.")
    parser.add_option("-a",
                      "--ip",
                      dest="host",
                      help="server name or IP (default: %default)",
                      metavar="ipAddress",
                      default="localhost")
    parser.add_option("-p",
                      dest="port",
                      type="int",
                      help="server port (default: %default)",
                      metavar="tcpPort",
                      default=8194)

    (options, args) = parser.parse_args()

    return options


def printField(field):
    fldId = field.getElementAsString(FIELD_ID)
    if field.hasElement(FIELD_INFO):
        fldInfo = field.getElement(FIELD_INFO)
        fldMnemonic = fldInfo.getElementAsString(FIELD_MNEMONIC)
        fldDesc = fldInfo.getElementAsString(FIELD_DESC)

        print "%s%s%s" % (fldId.ljust(ID_LEN), fldMnemonic.ljust(MNEMONIC_LEN),
                          fldDesc.ljust(DESC_LEN))
    else:
        fldError = field.getElement(FIELD_ERROR)
        errorMsg = fldError.getElementAsString(FIELD_MSG)

        print
        print " ERROR: %s - %s" % (fldId, errorMsg)


def printHeader():
    print "%s%s%s" % ("FIELD ID".ljust(ID_LEN), "MNEMONIC".ljust(MNEMONIC_LEN),
                      "DESCRIPTION".ljust(DESC_LEN))
    print "%s%s%s" % ("-----------".ljust(ID_LEN), "-----------".ljust(MNEMONIC_LEN),
                      "-----------".ljust(DESC_LEN))


def main():
    global options
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)

    print "Connecting to %s:%d" % (options.host, options.port)

    # Create a Session
    session = blpapi.Session(sessionOptions)

    # Start a Session
    if not session.start():
        print "Failed to start session."
        return

    if not session.openService(APIFLDS_SVC):
        print "Failed to open", APIFLDS_SVC
        return

    fieldInfoService = session.getService(APIFLDS_SVC)
    request = fieldInfoService.createRequest("FieldInfoRequest")
    request.append("id", "LAST_PRICE")
    request.append("id", "pq005")
    request.append("id", "zz0002")

    request.set("returnFieldDocumentation", True)

    print "Sending Request:", request
    session.sendRequest(request)

    try:
        # Process received events
        while(True):
            # We provide timeout to give the chance to Ctrl+C handling:
            event = session.nextEvent(500)
            if event.eventType() != blpapi.Event.RESPONSE and \
                    event.eventType() != blpapi.Event.PARTIAL_RESPONSE:
                continue
            for msg in event:
                fields = msg.getElement("fieldData")
                printHeader()
                for field in fields.values():
                    printField(field)
                print
            # Response completly received, so we could exit
            if event.eventType() == blpapi.Event.RESPONSE:
                break
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print "SimpleFieldInfoExample"
    try:
        main()
    except KeyboardInterrupt:
        print "Ctrl+C pressed. Stopping..."

__copyright__ = """
Copyright 2012. Bloomberg Finance L.P.

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
