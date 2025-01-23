from blpapi_import_helper import blpapi
from argparse import Action
from collections import namedtuple


_SESSION_IDENTITY_AUTH_OPTIONS = "sessionIdentityAuthOptions"


class AuthOptionsAction(Action):
    """The action that parses authorization options from user input"""

    def __call__(self, parser, args, values, option_string=None):
        vals = values.split("=", 1)

        authOptions = None

        auth_type = vals[0]
        if auth_type == "user":
            authUser = blpapi.AuthUser.createWithLogonName()
            authOptions = blpapi.AuthOptions.createWithUser(authUser)
        elif auth_type == "none":
            authOptions = None
        else:
            if len(vals) != 2:
                parser.error(f"Invalid auth option '{values}'")

            if auth_type == "app":
                appName = vals[1]
                authOptions = blpapi.AuthOptions.createWithApp(appName)
            elif auth_type == "userapp":
                appName = vals[1]
                authUser = blpapi.AuthUser.createWithLogonName()
                authOptions = blpapi.AuthOptions.createWithUserAndApp(
                    authUser, appName
                )
            elif auth_type == "dir":
                dirProperty = vals[1]
                authUser = blpapi.AuthUser.createWithActiveDirectoryProperty(
                    dirProperty
                )
                authOptions = blpapi.AuthOptions.createWithUser(authUser)
            elif auth_type == "manual":
                parts = vals[1].split(",")
                if len(parts) != 3:
                    parser.error(f"Invalid auth option '{values}'")

                appName, ip, userId = parts
                authUser = blpapi.AuthUser.createWithManualOptions(userId, ip)
                authOptions = blpapi.AuthOptions.createWithUserAndApp(
                    authUser, appName
                )
            else:
                parser.error(f"Invalid auth option '{values}'")

        setattr(args, self.dest, authOptions)


class AppAuthAction(Action):
    """The action that parses app authorization options from user input"""

    def __call__(self, parser, args, values, option_string=None):
        vals = values.split("=", 1)
        if len(vals) != 2:
            parser.error(f"Invalid auth option '{values}'")

        authType, appName = vals
        if authType != "app":
            parser.error(f"Invalid auth option '{values}'")

        setattr(args, self.dest, appName)
        authOptions = blpapi.AuthOptions.createWithApp(appName)
        setattr(args, _SESSION_IDENTITY_AUTH_OPTIONS, authOptions)


HostPort = namedtuple("HostPort", ["host", "port"])
ServerAddress = namedtuple("ServerAddress", ["endpoint", "socks5"])


class HostAction(Action):
    """The action that parses host options from user input"""

    @staticmethod
    def _parseHostPort(parser, value):
        vals = value.split(":", 1)
        if len(vals) != 2:
            parser.error(f"Invalid host option '{value}'")

        maxPortValue = 65535
        if int(vals[1]) <= 0 or int(vals[1]) > maxPortValue:
            parser.error(
                f"Invalid port '{value}', value must be 1 through {maxPortValue}"
            )
        return HostPort(vals[0], vals[1])

    def __call__(self, parser, args, values, option_string=None):
        endpointSocks5 = values.split("/", 1)
        if len(endpointSocks5) == 0 or len(endpointSocks5) > 2:
            parser.error(f"Invalid host option '{values}'")

        endpoint = HostAction._parseHostPort(parser, endpointSocks5[0])
        socks5 = None
        if len(endpointSocks5) == 2:
            socks5 = HostAction._parseHostPort(parser, endpointSocks5[1])

        hosts = getattr(args, self.dest)
        hosts.append(ServerAddress(endpoint, socks5))


class UserIdIpAction(Action):
    """The action that parses userId and IP authorization options from user
    input
    """

    def __call__(self, parser, args, values, option_string=None):
        vals = values.split(":")
        if len(vals) != 2:
            parser.error(f"Invalid auth option '{values}'")

        userId, ip = vals
        getattr(args, self.dest).append((userId, ip))


def addConnectionAndAuthOptions(parser, forClientServerSetup=False):
    """
    Helper function that adds the options for connection and authorization to
    the argument parser.
    """
    # Server options
    server_group = parser.add_argument_group("Connections")
    server_group.add_argument(
        "-H",
        "--host",
        dest="hosts",
        help="Endpoint host:port and optional SOCKS5 host:port to use to connect"
        " (default: localhost:8194). Can be specified multiple times.",
        metavar="host:port[/socks5Host:socks5Port]",
        action=HostAction,
        default=[],
    )

    # Auth options
    if forClientServerSetup:
        _addArgGroupsAuthAndEntitlementsClientServerSetup(parser)
    else:
        _addArgGroupAuth(parser)

    # TLS Options
    tls_group = parser.add_argument_group("TLS (specify all or none)")
    tls_group.add_argument(
        "--tls-client-credentials",
        dest="tls_client_credentials",
        help="name a PKCS#12 file to use as a source of " "client credentials",
        metavar="file",
    )
    tls_group.add_argument(
        "--tls-client-credentials-password",
        dest="tls_client_credentials_password",
        help="specify password for accessing client credentials",
        metavar="password",
        default="",
    )
    tls_group.add_argument(
        "--tls-trust-material",
        dest="tls_trust_material",
        help="name a PKCS#7 file to use as a source of "
        "trusted certificates",
        metavar="file",
    )
    tls_group.add_argument(
        "--read-certificate-files",
        dest="read_certificate_files",
        help="Enable reading the TLS files and pass the blobs",
        action="store_true",
    )

    # ZFP Options
    zfp_group = parser.add_argument_group(
        "ZFP connections over leased lines (requires TLS)"
    )
    zfp_group.add_argument(
        "-z",
        "--zfp-over-leased-line",
        dest="remote",
        help="enable ZFP connections over leased lines on the "
        "specified port (8194 or 8196)"
        "\n(When this option is enabled, option -H/--host is ignored.)",
        metavar="port",
        type=int,
    )


def _addArgGroupAuth(parser):
    auth_group = parser.add_argument_group("Authorization")
    auth_group.add_argument(
        "-a",
        "--auth",
        dest=_SESSION_IDENTITY_AUTH_OPTIONS,
        help="""authorization option (default: none)
none                  applicable to Desktop API product that requires
                          Bloomberg Professional service to be installed locally
user                  as a user using OS logon information
dir=<property>        as a user using directory services
app=<app>             as the specified application
userapp=<app>         as user and application using logon information for the user
manual=<app,ip,user>  as user and application, with manually provided
                          IP address and EMRS user""",
        metavar="option",
        action=AuthOptionsAction,
    )


def _addArgGroupsAuthAndEntitlementsClientServerSetup(parser):
    """Adds the auth and entitlements options for the entitlement examples to
    the argument parser.
    """
    auth_group = parser.add_argument_group("Authorization")
    auth_group.add_argument(
        "-a",
        "--auth",
        dest="authAppName",
        required=True,
        help="authorize this application using the specified application",
        metavar="app=<app>",
        action=AppAuthAction,
    )

    entitlements_group = parser.add_argument_group(
        "User Authorization/Entitlements"
    )
    entitlements_group.add_argument(
        "-u",
        "--userid-ip",
        dest="userIdAndIps",
        help="authorize a user using userId and IP separated by ':'. Can be specified multiple times.",
        metavar="userId:IP",
        action=UserIdIpAction,
        default=[],
    )

    entitlements_group.add_argument(
        "-T",
        "--token",
        dest="tokens",
        help="authorize a user using the specified token. Can be specified multiple times.\n"
        "If the token starts with '-', use "
        "either -T<token> or --token=<token>.",
        metavar="token",
        action="append",
        default=[],
    )


def _getTlsOptions(options):
    """Parse TlsOptions from user input"""

    if (
        options.tls_client_credentials is None
        or options.tls_trust_material is None
    ):
        return None

    print("TlsOptions enabled")
    if options.read_certificate_files:
        with open(options.tls_client_credentials, "rb") as credentialfile:
            credential_blob = credentialfile.read()
        with open(options.tls_trust_material, "rb") as trustfile:
            trust_blob = trustfile.read()
        return blpapi.TlsOptions.createFromBlobs(
            credential_blob,
            options.tls_client_credentials_password,
            trust_blob,
        )

    return blpapi.TlsOptions.createFromFiles(
        options.tls_client_credentials,
        options.tls_client_credentials_password,
        options.tls_trust_material,
    )


def createClientServerSetupAuthOptions(options):
    """Creates a dictionary whose keys are the identifier representing a user,
    either userId:IP or token, and whose values are the AuthOptions, either
    manual option (userId + IP + App) or token.
    """
    authOptionsByIdentifier = {}
    for userId, ip in options.userIdAndIps:
        authUser = blpapi.AuthUser.createWithManualOptions(userId, ip)
        authOptions = blpapi.AuthOptions.createWithUserAndApp(
            authUser, options.authAppName
        )
        authOptionsByIdentifier[f"{userId}:{ip}"] = authOptions

    for i, token in enumerate(options.tokens):
        authOptions = blpapi.AuthOptions.createWithToken(token)
        authOptionsByIdentifier[f"token #{i + 1}"] = authOptions

    return authOptionsByIdentifier


def createSessionOptions(options):
    """
    Creates SessionOptions from the following command line arguments:
    - connections where servers, TLS and ZFP over Leased lines are specified.
    - TLS options
    - authorization options that are used as session identity options.
    """

    tlsOptions = _getTlsOptions(options)
    if options.remote:
        if tlsOptions is None:
            raise RuntimeError("ZFP connections require TLS parameters")

        print("Creating a ZFP connection for leased lines.")
        sessionOptions = blpapi.ZfpUtil.getZfpOptionsForLeasedLines(
            options.remote, tlsOptions
        )
    else:
        sessionOptions = blpapi.SessionOptions()
        for idx, serverAddress in enumerate(options.hosts):
            socks5Config = (
                blpapi.Socks5Config(
                    serverAddress.socks5.host, int(serverAddress.socks5.port)
                )
                if serverAddress.socks5
                else None
            )
            sessionOptions.setServerAddress(
                serverAddress.endpoint.host,
                int(serverAddress.endpoint.port),
                idx,
                socks5Config,
            )

        if tlsOptions:
            sessionOptions.setTlsOptions(tlsOptions)

    sessionOptions.setSessionIdentityOptions(
        options.sessionIdentityAuthOptions
    )

    def serverAddressToString(server: ServerAddress):
        tostr = ":".join(server.endpoint)
        if server.socks5:
            tostr = f"{tostr}/{':'.join(server.socks5)}"
        return tostr

    print(
        f"Connecting to "
        f"{', '.join([serverAddressToString(h) for h in options.hosts])}"
    )

    return sessionOptions


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
