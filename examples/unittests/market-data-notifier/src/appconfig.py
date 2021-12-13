"""Sample command line parser."""

from argparse import ArgumentParser, Action

class AuthOptionsAction(Action):  # pylint: disable=too-few-public-methods
    """Parse authorization args from user input."""

    def __call__(self, parser, args, values, option_string=None):

        value = values
        vals = value.split("=", 1)

        auth = None
        if value == "user":
            auth = {"option" : "AuthenticationType=OS_LOGON"}
        elif value == "none":
            auth = {"option" : None}
        elif vals[0] == "app" and len(vals) == 2:
            auth = {
                "option" : "AuthenticationMode=APPLICATION_ONLY;"
                           "ApplicationAuthenticationType=APPNAME_AND_KEY;"
                           "ApplicationName=" + vals[1]}
        elif vals[0] == "userapp" and len(vals) == 2:
            auth = {
                "option" : "AuthenticationMode"
                           "=USER_AND_APPLICATION;AuthenticationType=OS_LOGON;"
                           "ApplicationAuthenticationType=APPNAME_AND_KEY;"
                           "ApplicationName=" + vals[1]}
        elif vals[0] == "dir" and len(vals) == 2:
            auth = {
                "option" : "AuthenticationType=DIRECTORY_SERVICE;"
                           "DirSvcPropertyName=" + vals[1]}
        elif vals[0] == "manual":
            parts = []
            if len(vals) == 2:
                parts = vals[1].split(",")

            if len(parts) != 3:
                raise ValueError("Invalid auth option '%s'" % value)

            option = ("AuthenticationMode=USER_AND_APPLICATION;"
                      "AuthenticationType=MANUAL;"
                      "ApplicationAuthenticationType=APPNAME_AND_KEY;"
                      "ApplicationName=") + parts[0]

            auth = {"option" : option,
                    "manual" : {"ip"   : parts[1],
                                "user" : parts[2]}}
        else:
            raise ValueError("Invalid auth option '%s'" % value)

        setattr(args, self.dest, auth)


def parseCmdLine():
    """Parse command line arguments."""

    parser = ArgumentParser(description="Retrieve realtime data.")
    parser.add_argument("-a",
                        "--ip",
                        dest="hosts",
                        help="server name or IP (default: localhost)",
                        metavar="ipAddress",
                        action="append",
                        default=[])
    parser.add_argument("-p",
                        dest="port",
                        type=int,
                        help="server port (default: %default)",
                        metavar="tcpPort",
                        default=8194)
    parser.add_argument("-s",
                        dest="service",
                        help="service name (default: %default)",
                        metavar="service",
                        default="//viper/mktdata")
    parser.add_argument(
        "-t",
        dest="topics",
        help="topic name (default: //blp/mktdata/ticker/IBM Equity)",
        metavar="topic",
        action="append",
        default=['//blp/mktdata/ticker/IBM Equity'])
    parser.add_argument("-f",
                        dest="fields",
                        help="field to subscribe to (default: LAST_PRICE)",
                        metavar="field",
                        action="append",
                        default=['LAST_PRICE'])
    parser.add_argument("-o",
                        dest="options",
                        help="subscription options (default: empty)",
                        metavar="option",
                        action="append",
                        default=[])
    parser.add_argument("--auth",
                        dest="auth",
                        help="authentication option: "
                        "user|none|app=<app>|userapp=<app>|dir=<property>|"
                        "manual=<app,ip,user>"
                        " (default: none)",
                        metavar="option",
                        action=AuthOptionsAction,
                        default={"option" : None})

    args = parser.parse_args()
    return args

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
