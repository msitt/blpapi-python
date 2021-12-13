from argparse import Action, ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi

AUTH_USER = "AuthenticationType=OS_LOGON"
AUTH_APP_PREFIX = "AuthenticationMode=APPLICATION_ONLY;ApplicationAuthenticationType=APPNAME_AND_KEY;ApplicationName="
AUTH_USER_APP_PREFIX = "AuthenticationMode=USER_AND_APPLICATION;AuthenticationType=OS_LOGON;ApplicationAuthenticationType=APPNAME_AND_KEY;ApplicationName="
AUTH_DIR_PREFIX = "AuthenticationType=DIRECTORY_SERVICE;DirSvcPropertyName="

AUTH_OPTION_USER = "user"
AUTH_OPTION_APP = "app"
AUTH_OPTION_USER_APP = "userapp"
AUTH_OPTION_DIR = "dir"


class AuthOptionsAction(Action):
    """The action that parses authorization options from user input"""

    def __call__(self, parser, args, values, option_string=None):
        vals = values.split('=', 1)

        if vals[0] == AUTH_OPTION_USER:
            authOptions = AUTH_USER
        elif vals[0] == AUTH_OPTION_APP and len(vals) == 2:
            appName = vals[1]
            authOptions = f"{AUTH_APP_PREFIX}{appName}"
        elif vals[0] == AUTH_OPTION_USER_APP and len(vals) == 2:
            appName = vals[1]
            authOptions = f"{AUTH_USER_APP_PREFIX}{appName}"
        elif vals[0] == AUTH_OPTION_DIR and len(vals) == 2:
            dirProperty = vals[1]
            authOptions = f"{AUTH_DIR_PREFIX}{dirProperty}"
        else:
            parser.error(f"Invalid auth option '{values}'")

        setattr(args, self.dest, authOptions)


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(
        description="Generate a token for a user to be used on the server side",
        formatter_class=RawTextHelpFormatter)
    parser.add_argument("-H",
                        "--host",
                        required=True,
                        dest="ipAndPort",
                        help="Server name or IP and port separated by ':'",
                        metavar="host:port")
    parser.add_argument("-a",
                        "--auth",
                        required=True,
                        dest="authOptions",
                        help="Authentication option: \n"
                             "    user              as a user using OS logon  information\n"
                             "    dir=<property>    as a user using directory services\n"
                             "    app=<app>         as the specified application\n"
                             "    userapp=<app>     as user and application using logon information for the user\n",
                        metavar="option",
                        action=AuthOptionsAction)

    options = parser.parse_args()

    ipAndPort = options.ipAndPort.split(':')
    if len(ipAndPort) != 2:
        parser.error(f"Invalid host '{options.ipAndPort}'")

    options.host = ipAndPort[0]
    options.port = ipAndPort[1]

    return options


def main():
    options = parseCmdLine()

    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(int(options.port))
    sessionOptions.setAuthenticationOptions(options.authOptions)

    print(f"Connecting to {options.host}:{options.port}")
    session = blpapi.Session(sessionOptions)
    try:
        if not session.start():
            print("Failed to start session.")
            return

        session.generateToken()

        while True:
            event = session.nextEvent()
            if event.eventType() != blpapi.Event.TOKEN_STATUS:
                continue

            for msg in event:
                msgType = msg.messageType()
                if msgType == blpapi.Names.TOKEN_GENERATION_SUCCESS:
                    token = msg.getElementAsString("token")
                    print(f"Token is successfully generated: {token}")
                elif msgType == blpapi.Names.TOKEN_GENERATION_FAILURE:
                    print(f"Failed to generate token: {msg}")

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
