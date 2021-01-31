""" SessionIdentityExample """
from __future__ import print_function

# pylint: disable=deprecated-module
from optparse import OptionParser, OptionValueError

import os
import platform as plat
import sys
if sys.version_info >= (3, 8) and plat.system().lower() == "windows":
    # pylint: disable=no-member
    with os.add_dll_directory(os.getenv('BLPAPI_LIBDIR')):
        import blpapi
        from blpapi import AuthOptions, AuthUser
else:
    import blpapi
    from blpapi import AuthOptions, AuthUser

NONE = "none"
USER = "user"
APP = "app"
USERAPP = "userapp"

def authOptionCallback(_option, _opt, value, parser):
    """Parse authorization options from user input"""

    vals = value.split('=', 1)

    parser.values.authType = vals[0]
    if value == NONE:
        parser.values.appName = None
    elif value == USER:
        parser.values.appName = None
    elif vals[0] == APP and len(vals) == 2:
        parser.values.appName = vals[1]
    elif vals[0] == USERAPP and len(vals) == 2:
        parser.values.appName = vals[1]
    else:
        raise OptionValueError("Invalid auth option '%s'" % value)

def parseCmdLine():
    """Parse command line arguments"""

    parser = OptionParser(description="Example of session identity"
                                      " authorization mechanisms.")
    parser.add_option("-a",
                      "--ip",
                      dest="host",
                      help="server name or IP (default: localhost)",
                      default="localhost")
    parser.add_option("-p",
                      dest="port",
                      type="int",
                      help="server port (default: %default)",
                      default=8194)
    parser.add_option("--auth",
                      dest="authType",
                      help="authorization option: "
                           "none|user|app=<appName>|userapp=<appName>"
                           " (default: user)\n"
                           "'none' is applicable to Desktop API product "
                           "that requires Bloomberg Professional service "
                           "to be installed locally.",
                      metavar="option",
                      action="callback",
                      callback=authOptionCallback,
                      type="string",
                      default=USER)

    options, _ = parser.parse_args()

    return options


class SessionIdentityExample: # pylint: disable=too-few-public-methods
    """This example shows how to authorize the session identity."""

    def __init__(self, options):
        self.host = options.host
        self.port = options.port
        self.authOptionsType = options.authType
        if hasattr(options, "appName"):
            self.appName = options.appName

    def run(self):
        """ Start a session using the session identity. """

        if self.authOptionsType == USER:
            authOptions = AuthOptions \
                .createWithUser(AuthUser.createWithLogonName())
        elif self.authOptionsType == APP:
            authOptions = AuthOptions.createWithApp(self.appName)
        elif self.authOptionsType == USERAPP:
            authOptions = AuthOptions \
                .createWithUserAndApp(AuthUser.createWithLogonName(),
                                      self.appName)
        else:
            authOptions = None

        sessionOptions = blpapi.SessionOptions()
        sessionOptions.setServerAddress(self.host, self.port, 0)
        sessionOptions.setSessionIdentityOptions(authOptions)
        sessionOptions.setAutoRestartOnDisconnection(True)

        session = blpapi.Session(sessionOptions)
        if not session.start():
            print("Failed to start session.")
            return

        while True:
            event = session.tryNextEvent()
            if event is None:
                break
            for msg in event:
                print(msg)


def main():
    """ Main function. """
    print("SessionIdentityExample")

    options = parseCmdLine()

    example = SessionIdentityExample(options)

    try:
        example.run()
    except Exception as e: # pylint: disable=broad-except
        print("Blpapi exception: {}".format(e))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl+C pressed. Stopping...")

__copyright__ = """
Copyright 2020. Bloomberg Finance L.P.

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
