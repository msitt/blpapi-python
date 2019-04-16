# ZfpOverLeasedLinesSessionExample.py

"""The example demonstrates how to establish a ZFP session that leverages
private leased line connectivity. To see how to use the resulting session
(authorizing a session, establishing subscriptions or making requests etc.),
 please refer to the other examples.
"""

from __future__ import absolute_import
from __future__ import print_function

from argparse import ArgumentParser, Action
import blpapi

class AuthOptionsAction(Action):  # pylint: disable=too-few-public-methods
    """Parse authorization args from user input"""

    def __call__(self, parser, args, values, option_string=None):

        value = values
        vals = value.split("=", 1)

        auth = None
        value = values
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
    """Parse command line arguments"""

    parser = ArgumentParser(description="Create a ZFP session.")
    parser.add_argument("--zfp-over-leased-line",
                        dest="zfpPort",
                        help="enable ZFP connections over leased lines on the"
                             " specified port (8194 or 8196) "
                             "(default: %(default)s)",
                        type=int,
                        default=8194,
                        metavar="port")

    parser.add_argument("--auth",
                        dest="auth",
                        help="authentication option: "
                        "user|none|app=<app>|userapp=<app>|dir=<property>|"
                        "manual=<app,ip,user>"
                        " (default: none)",
                        metavar="option",
                        action=AuthOptionsAction,
                        default={"option" : None})

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

    if not args.tlsOptions:
        raise RuntimeError("ZFP connections require TLS parameters")

    if args.zfpPort == 8194:
        args.remote = blpapi.ZfpUtil.REMOTE_8194
    elif args.zfpPort == 8196:
        args.remote = blpapi.ZfpUtil.REMOTE_8196
    else:
        raise RuntimeError("Invalid ZFP port: " + args.zfpPort)

    return args

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

def prepareZfpSessionOptions(args):
    """Prepare SessionOptions for ZFP session"""

    print("Creating a ZFP connection for leased lines.")
    sessionOptions = blpapi.ZfpUtil.getZfpOptionsForLeasedLines(
        args.remote,
        args.tlsOptions)
    return sessionOptions

def main():
    """Main function"""

    args = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = prepareZfpSessionOptions(args)
    sessionOptions.setAuthenticationOptions(args.auth['option'])
    sessionOptions.setAutoRestartOnDisconnection(True)

    numHosts = sessionOptions.numServerAddresses()
    for i in range(0, numHosts):
        (host, port) = sessionOptions.getServerAddress(i)
        print("Connecting to port %d on %s" % (port, host))

    session = blpapi.Session(sessionOptions)

    if not session.start():
        print("Failed to start session.")
        while True:
            event = session.tryNextEvent()
            if not event:
                break

            for msg in event:
                print(msg)
        return

    print("Session started successfully.")

    # Note: ZFP solution requires authorization, which should be done here
    # before any subscriptions or requests can be made. For examples of
    # how to authorize or get data, please refer to the specific examples.

if __name__ == "__main__":
    print("ZfpOverLeasedLinesSessionExample")
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl+C pressed. Stopping...")

__copyright__ = """
Copyright 2019. Bloomberg Finance L.P.

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
