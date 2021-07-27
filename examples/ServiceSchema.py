# ServiceSchema.py
from __future__ import print_function
from __future__ import absolute_import

from optparse import OptionParser, OptionValueError

import os
import platform as plat
import sys
if sys.version_info >= (3, 8) and plat.system().lower() == "windows":
    # pylint: disable=no-member
    with os.add_dll_directory(os.getenv('BLPAPI_LIBDIR')):
        import blpapi
else:
    import blpapi

REFERENCE_DATA_RESPONSE = blpapi.Name("ReferenceDataResponse")

ELEMENT_DATATYPE_NAMES = {
    blpapi.DataType.BOOL: "BOOL",
    blpapi.DataType.CHAR: "CHAR",
    blpapi.DataType.BYTE: "BYTE",
    blpapi.DataType.INT32: "INT32",
    blpapi.DataType.INT64: "INT64",
    blpapi.DataType.FLOAT32: "FLOAT32",
    blpapi.DataType.FLOAT64: "FLOAT64",
    blpapi.DataType.STRING: "STRING",
    blpapi.DataType.BYTEARRAY: "BYTEARRAY",
    blpapi.DataType.DATE: "DATE",
    blpapi.DataType.TIME: "TIME",
    blpapi.DataType.DECIMAL: "DECIMAL",
    blpapi.DataType.DATETIME: "DATETIME",
    blpapi.DataType.ENUMERATION: "ENUMERATION",
    blpapi.DataType.SEQUENCE: "SEQUENCE",
    blpapi.DataType.CHOICE: "CHOICE",
    blpapi.DataType.CORRELATION_ID: "CORRELATION_ID"
}


SCHEMA_STATUS_NAMES = {
    blpapi.SchemaStatus.ACTIVE: "ACTIVE",
    blpapi.SchemaStatus.DEPRECATED: "DEPRECATED",
    blpapi.SchemaStatus.INACTIVE: "INACTIVE",
    blpapi.SchemaStatus.PENDING_DEPRECATION: "PENDING"
}


def authOptionCallback(_option, _opt, value, parser):
    """Parse authorization options from user input"""

    vals = value.split('=', 1)

    if value == "user":
        authUser = blpapi.AuthUser.createWithLogonName()
        authOptions = blpapi.AuthOptions.createWithUser(authUser)
    elif value == "none":
        authOptions = None
    elif vals[0] == "app" and len(vals) == 2:
        appName = vals[1]
        authOptions = blpapi.AuthOptions.createWithApp(appName)
    elif vals[0] == "userapp" and len(vals) == 2:
        appName = vals[1]
        authUser = blpapi.AuthUser.createWithLogonName()
        authOptions = blpapi.AuthOptions\
            .createWithUserAndApp(authUser, appName)
    elif vals[0] == "dir" and len(vals) == 2:
        activeDirectoryProperty = vals[1]
        authUser = blpapi.AuthUser\
            .createWithActiveDirectoryProperty(activeDirectoryProperty)
        authOptions = blpapi.AuthOptions.createWithUser(authUser)
    elif vals[0] == "manual":
        parts = []
        if len(vals) == 2:
            parts = vals[1].split(',')

        if len(parts) != 3:
            raise OptionValueError("Invalid auth option {}".format(value))

        appName, ip, userId = parts

        authUser = blpapi.AuthUser.createWithManualOptions(userId, ip)
        authOptions = blpapi.AuthOptions.createWithUserAndApp(authUser, appName)
    else:
        raise OptionValueError("Invalid auth option '{}'".format(value))

    parser.values.auth = {'option' : authOptions}

def parseCmdLine():
    parser = OptionParser()
    parser.add_option("-a",
                      "--host",
                      dest="host",
                      help="HOST address to connect to",
                      metavar="HOST",
                      default="localhost")
    parser.add_option("-p",
                      "--port",
                      dest="port",
                      type="int",
                      help="PORT to connect to (%default)",
                      metavar="PORT",
                      default=8194)
    parser.add_option("-s",
                      "--service",
                      default="//blp/apiflds",
                      help="SERVICE to print the schema of "
                      "('//blp/apiflds' by default)")
    parser.add_option("--auth",
                      dest="auth",
                      help="authentication option: "
                           "user|none|app=<app>|userapp=<app>|dir=<property>"
                           "|manual=<app,ip,user>"
                           " (default: user)\n"
                           "'none' is applicable to Desktop API product "
                           "that requires Bloomberg Professional service "
                           "to be installed locally.",
                      metavar="option",
                      action="callback",
                      callback=authOptionCallback,
                      type="string",
                      default={"option" :
                               blpapi.AuthOptions.createWithUser(
                                      blpapi.AuthUser.createWithLogonName())})
    (options, _) = parser.parse_args()
    return options


def printMessage(msg):
    print("[{0}]: {1}".format(", ".join(map(str, msg.correlationIds())), msg))


def getIndent(level):
    return "" if level == 0 else " ".ljust(level * 2)


# Print enumeration (constant list)
def printEnumeration(cl, level):
    indent = getIndent(level + 1)
    print(indent + "  {0} {1} {2} \"{3}\" possible values:".format(
        cl.name(),
        SCHEMA_STATUS_NAMES[cl.status()],
        ELEMENT_DATATYPE_NAMES[cl.datatype()],
        cl.description()))

    # Enumerate and print all constant list's values (constants)
    for i in cl:
        print(indent + "    {0} {1} {2} \"{3}\" = {4!s}".format(
            i.name(),
            SCHEMA_STATUS_NAMES[i.status()],
            ELEMENT_DATATYPE_NAMES[i.datatype()],
            i.description(),
            i.getValue()))


# Recursively print element definition
def printElementDefinition(ed, level=0):
    indent = getIndent(level)

    maxValues = ed.maxValues()
    if maxValues == blpapi.SchemaElementDefinition.UNBOUNDED:
        valuesRange = "[{0}, INF)".format(ed.minValues())
    else:
        valuesRange = "[{0}, {1}]".format(ed.minValues(), maxValues)

    # Get and print alternate element names
    alternateNames = ed.alternateNames()
    if alternateNames:
        alternateNames = "[{0}]".format(",".join(map(str, alternateNames)))
    else:
        alternateNames = ""

    print(indent + "* {0} {1} {2} {3} \"{4}\"".format(
        ed.name(),
        SCHEMA_STATUS_NAMES[ed.status()],
        valuesRange,
        alternateNames,
        ed.description()))

    # Get and print related type definition
    td = ed.typeDefinition()

    print(indent + "  {0} {1} {2} {3}{4}{5}\"{6}\"".format(
        td.name(),
        SCHEMA_STATUS_NAMES[td.status()],
        ELEMENT_DATATYPE_NAMES[td.datatype()],
        "complex " if td.isComplexType() else "",
        "simple " if td.isSimpleType() else "",
        "enum " if td.isEnumerationType() else "",
        td.description()))

    # Get and print all possible values for enumeration type
    enumeration = td.enumeration()
    if not enumeration is None:
        printEnumeration(enumeration, level)

    if td.numElementDefinitions():
        print(indent + "  Elements[{0}]:".format(
            td.numElementDefinitions()))
        # Enumerate and print all sub-element definitions
        for i in td.elementDefinitions():
            printElementDefinition(i, level + 1)


def printOperation(operation, _service):
    print("{0} \"{1}\" Request:".format(
        operation.name(),
        operation.description()))

    # Print operation's request definition
    printElementDefinition(operation.requestDefinition(), 1)
    print("Responses[{0}]:".format(operation.numResponseDefinitions()))

    # Enumerate and print all operation's response definitions
    for r in operation.responseDefinitions():
        printElementDefinition(r, 1)
    print()


def main():
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)
    sessionOptions.setSessionIdentityOptions(options.auth['option'])

    # Create a Session
    session = blpapi.Session(sessionOptions)

    # Start a Session
    if not session.start():
        raise Exception("Can't start session.")

    try:
        print("Session started.")

        # Open service to get reference data from
        if not session.openService(options.service):
            raise Exception("Can't open '{0}' service.".format(
                options.service))

        # Obtain previously opened service
        service = session.getService(options.service)
        print("Service {0}:".format(options.service))

        print("Service event definitions[{0}]:".format(
            service.numEventDefinitions()))
        # Enumerate and print all service's event definitions
        for ed in service.eventDefinitions():
            printElementDefinition(ed)
        print()

        print("Operations[{0}]:".format(service.numOperations()))
        # Enumerate and print all service's operations
        for operation in service.operations():
            printOperation(operation, service)
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print("ServiceSchema")
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl+C pressed. Stopping...")

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
