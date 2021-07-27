# ConnectionAndAuthExample.py

"""This example shows how to configure the library to establish connections
using different host and ports, with a session identity.
"""

from __future__ import print_function
from argparse import ArgumentParser, Action, RawTextHelpFormatter
import os
import sys
import platform as plat
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
DIR = "dir"


class AuthOptionsAction(Action):  # pylint: disable=too-few-public-methods
    """Parse authorization args from user input"""

    def __call__(self, parser, args, values, option_string=None):
        vals = values.split("=", 1)

        auth = None
        if vals[0] == NONE:
            auth = None
        elif vals[0] == USER:
            user = AuthUser.createWithLogonName()
            auth = AuthOptions.createWithUser(user)
        elif vals[0] == APP and len(vals) == 2:
            appName = vals[1]
            auth = AuthOptions.createWithApp(appName)
        elif vals[0] == USERAPP and len(vals) == 2:
            appName = vals[1]
            user = AuthUser.createWithLogonName()
            auth = AuthOptions.createWithUserAndApp(user, appName)
        elif vals[0] == DIR and len(vals) == 2:
            dirProperty = vals[1]
            user = AuthUser.createWithActiveDirectoryProperty(dirProperty)
            auth = AuthOptions.createWithUser(user)
        elif vals[0] == "manual":
            parts = []
            if len(vals) == 2:
                parts = vals[1].split(",")

            if len(parts) != 3:
                raise ValueError("Invalid auth option '%s'" % values)

            appName, ipAddress, userId = parts
            user = AuthUser.createWithManualOptions(userId, ipAddress)
            auth = AuthOptions.createWithUserAndApp(user, appName)
        else:
            raise ValueError("Invalid auth option '%s'" % values)

        setattr(args, self.dest, auth)


class HostAction(Action):  # pylint: disable=too-few-public-methods
    """ Helper class to parse host arguments """

    def __call__(self, parser, namespace, values, option_string=None):
        host = values.split(":")
        if len(host) != 2:
            raise ValueError("Invalid host:port '%s'" % values)
        host[1] = int(host[1])
        hosts = getattr(namespace, self.dest)
        if not hosts:
            setattr(namespace, self.dest, [host])
        else:
            hosts.append(host)


def getTlsOptions(args):
    """Create TlsOptions from user input"""

    if (args.tls_client_credentials is None or
            args.tls_trust_material is None):
        return None

    print("TlsOptions enabled")
    if args.read_certificate_files:
        credential_blob = None
        trust_blob = None
        with open(args.tls_client_credentials, 'rb') as credentialfile:
            credential_blob = credentialfile.read()
        with open(args.tls_trust_material, 'rb') as trustfile:
            trust_blob = trustfile.read()
        return blpapi.TlsOptions.createFromBlobs(
            credential_blob,
            args.tls_client_credentials_password,
            trust_blob)

    return blpapi.TlsOptions.createFromFiles(
        args.tls_client_credentials,
        args.tls_client_credentials_password,
        args.tls_trust_material)


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(description="Connection and Auth example",
                            formatter_class=lambda prog: RawTextHelpFormatter(
                                                               prog, width=99))
    defaultUser = AuthUser.createWithLogonName()
    defaultAuthOptions = AuthOptions.createWithUser(defaultUser)

    parser.add_argument("--auth",
                        dest="auth",
                        help="authentication option: "
                        "user|none|app=<app>|userapp=<app>|dir=<property>|"
                        "manual=<app,ip,user>"
                        " (default: user)\n"
                        "'none' is applicable to Desktop API product "
                        "that requires Bloomberg Professional service "
                        "to be installed locally.",
                        metavar="option",
                        action=AuthOptionsAction,
                        default=defaultAuthOptions)

    parser.add_argument("--host",
                        dest="host",
                        help="server name or IP, and port <ipAddress:port>"
                        "(default 'localhost:8194')",
                        metavar="<ipAddress:port>",
                        action=HostAction)

    parser.add_argument("--retries",
                        dest="retries",
                        help="number of connection retries "
                        "(default: number of hosts)",
                        metavar="option",
                        type=int)

    # TLS Options
    parser.add_argument("--tls-client-credentials",
                        dest="tls_client_credentials",
                        help="name a PKCS#12 file to use as a source of "
                        "client credentials",
                        metavar="option")
    parser.add_argument("--tls-client-credentials-password",
                        dest="tls_client_credentials_password",
                        help="specify password for accessing"
                             " client credentials",
                        metavar="option",
                        default="")
    parser.add_argument("--tls-trust-material",
                        dest="tls_trust_material",
                        help="name a PKCS#7 file to use as a source of trusted"
                        " certificates",
                        metavar="option")
    parser.add_argument("--read-certificate-files",
                        dest="read_certificate_files",
                        help="(optional) read the TLS files and pass the blobs",
                        action="store_true")

    args = parser.parse_args()

    args.tlsOptions = getTlsOptions(args)

    if not args.host:
        args.host = [["localhost", 8194]]

    if args.retries is None:
        args.retries = len(args.host)

    return args


class ConnectionAndAuthExample: # pylint: disable=too-few-public-methods
    """This example shows how to configure the library to establish
    connections using different host and ports, with a session identity.
    """

    def __init__(self, options):
        self.config = options

    def run(self):
        """ Execute the example """

        sessionOptions = blpapi.SessionOptions()
        for i, host in enumerate(self.config.host):
            sessionOptions.setServerAddress(host[0], host[1], i)

        sessionOptions.setSessionIdentityOptions(self.config.auth)
        sessionOptions.setAutoRestartOnDisconnection(True)
        sessionOptions.setNumStartAttempts(self.config.retries)

        if self.config.tlsOptions:
            sessionOptions.setTlsOptions(self.config.tlsOptions)

        session = blpapi.Session(sessionOptions)
        if not session.start():
            print("Failed to start session.")
            return
        print("Session started")

        while True:
            event = session.nextEvent(1000)
            if event:
                for message in event:
                    print(message)


def main():
    """ Main function. """
    print("ConnectionAndAuthExample. Press Ctrl+C to stop.")

    options = parseCmdLine()

    example = ConnectionAndAuthExample(options)

    try:
        example.run()
    except blpapi.Exception as err:
        print("Exception caught: {}".format(err))


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
