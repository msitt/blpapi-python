# LocalMktdataSubscriptionExample.py
from __future__ import print_function
from __future__ import absolute_import

import blpapi
import datetime
from optparse import OptionParser, OptionValueError

TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")
AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
TOKEN = blpapi.Name("token")

def authOptionCallback(option, opt, value, parser):
    vals = value.split('=', 1)

    if value == "user":
        parser.values.auth = { 'option' : "AuthenticationType=OS_LOGON" }
    elif value == "none":
        parser.values.auth = { 'option' : None }
    elif vals[0] == "app" and len(vals) == 2:
        parser.values.auth = { 'option' : "AuthenticationMode=APPLICATION_ONLY;"\
            "ApplicationAuthenticationType=APPNAME_AND_KEY;"\
            "ApplicationName=" + vals[1] }
    elif vals[0] == "userapp" and len(vals) == 2:
        parser.values.auth = { 'option' : "AuthenticationMode=USER_AND_APPLICATION;"\
            "AuthenticationType=OS_LOGON;"\
            "ApplicationAuthenticationType=APPNAME_AND_KEY;"\
            "ApplicationName=" + vals[1] }
    elif vals[0] == "dir" and len(vals) == 2:
        parser.values.auth = { 'option' : "AuthenticationType=DIRECTORY_SERVICE;"\
            "DirSvcPropertyName=" + vals[1] }
    elif vals[0] == "manual":
        parts = []
        if len(vals) == 2:
            parts = vals[1].split(',')

        # TODO: Add support for user+ip only
        if len(parts) != 3:
            raise OptionValueError("Invalid auth option '%s'" % value)

        option = "AuthenticationMode=USER_AND_APPLICATION;" + \
                 "AuthenticationType=MANUAL;" + \
                 "ApplicationAuthenticationType=APPNAME_AND_KEY;" + \
                 "ApplicationName=" + parts[0]

        parser.values.auth = { 'option' : option,
                               'manual'  : { 'ip'   : parts[1],
                                             'user' : parts[2] } }
    else:
        raise OptionValueError("Invalid auth option '%s'" % value)

def parseCmdLine():
    parser = OptionParser(description="Retrieve realtime data.")
    parser.add_option("-a",
                      "--ip",
                      dest="hosts",
                      help="server name or IP (default: localhost)",
                      metavar="ipAddress",
                      action="append",
                      default=[])
    parser.add_option("-p",
                      dest="port",
                      type="int",
                      help="server port (default: %default)",
                      metavar="tcpPort",
                      default=8194)
    parser.add_option("-s",
                      dest="service",
                      help="service name (default: %default)",
                      metavar="service",
                      default="//viper/mktdata")
    parser.add_option("-t",
                      dest="topics",
                      help="topic name (default: /ticker/IBM Equity)",
                      metavar="topic",
                      action="append",
                      default=[])
    parser.add_option("-f",
                      dest="fields",
                      help="field to subscribe to (default: empty)",
                      metavar="field",
                      action="append",
                      default=[])
    parser.add_option("-o",
                      dest="options",
                      help="subscription options (default: empty)",
                      metavar="option",
                      action="append",
                      default=[])
    parser.add_option("--me",
                      dest="maxEvents",
                      type="int",
                      help="stop after this many events (default: %default)",
                      metavar="maxEvents",
                      default=1000000)
    parser.add_option("--auth",
                      dest="auth",
                      help="authentication option: "
                      "user|none|app=<app>|userapp=<app>|dir=<property>|manual=<app,ip,user>"
                      " (default: %default)",
                      metavar="option",
                      action="callback",
                      callback=authOptionCallback,
                      type="string",
                      default={ "option" : None })

    # TLS Options
    parser.add_option("--tls-client-credentials",
                      dest="tls_client_credentials",
                      help="name a PKCS#12 file to use as a source of client credentials",
                      metavar="option",
                      type="string")
    parser.add_option("--tls-client-credentials-password",
                      dest="tls_client_credentials_password",
                      help="specify password for accessing client credentials",
                      metavar="option",
                      type="string",
                      default="")
    parser.add_option("--tls-trust-material",
                      dest="tls_trust_material",
                      help="name a PKCS#7 file to use as a source of trusted certificates",
                      metavar="option",
                      type="string")
    parser.add_option("--read-certificate-files",
                      dest="read_certificate_files",
                      help="(optional) read the TLS files and pass the blobs",
                      metavar="option",
                      action="store_true")

    (options, args) = parser.parse_args()

    if not options.hosts:
        options.hosts = ["localhost"]

    if not options.topics:
        options.topics = ["/ticker/IBM Equity"]

    return options


def authorize(authService, identity, session, cid, manual_options = None):
    tokenEventQueue = blpapi.EventQueue()

    if manual_options:
        session.generateToken(authId=manual_options['user'],
                              ipAddress=manual_options['ip'],
                              eventQueue=tokenEventQueue)
    else:
        session.generateToken(eventQueue=tokenEventQueue)

    # Process related response
    ev = tokenEventQueue.nextEvent()
    token = None
    if ev.eventType() == blpapi.Event.TOKEN_STATUS or \
            ev.eventType() == blpapi.Event.REQUEST_STATUS:
        for msg in ev:
            print(msg)
            if msg.messageType() == TOKEN_SUCCESS:
                token = msg.getElementAsString(TOKEN)
            elif msg.messageType() == TOKEN_FAILURE:
                break

    if not token:
        print("Failed to get token")
        return False

    # Create and fill the authorization request
    authRequest = authService.createAuthorizationRequest()
    authRequest.set(TOKEN, token)

    # Send authorization request to "fill" the Identity
    session.sendAuthorizationRequest(authRequest, identity, cid)

    # Process related responses
    startTime = datetime.datetime.today()
    WAIT_TIME_SECONDS = 10
    while True:
        event = session.nextEvent(WAIT_TIME_SECONDS * 1000)
        if event.eventType() == blpapi.Event.RESPONSE or \
            event.eventType() == blpapi.Event.REQUEST_STATUS or \
                event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
            for msg in event:
                print(msg)
                if msg.messageType() == AUTHORIZATION_SUCCESS:
                    return True
                print("Authorization failed")
                return False

        endTime = datetime.datetime.today()
        if endTime - startTime > datetime.timedelta(seconds=WAIT_TIME_SECONDS):
            return False

def getTlsOptions(options):
    if (options.tls_client_credentials is None or
            options.tls_trust_material is None):
        return None

    print("TlsOptions enabled")
    if (options.read_certificate_files):
        credential_blob = None
        trust_blob = None
        with open(options.tls_client_credentials, 'rb') as credentialfile:
            credential_blob = credentialfile.read()
        with open(options.tls_trust_material, 'rb') as trustfile:
            trust_blob = trustfile.read()
        return blpapi.TlsOptions.createFromBlobs(
                credential_blob,
                options.tls_client_credentials_password,
                trust_blob)
    else:
        return blpapi.TlsOptions.createFromFiles(
                options.tls_client_credentials,
                options.tls_client_credentials_password,
                options.tls_trust_material)

def main():
    global options
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    for idx, host in enumerate(options.hosts):
        sessionOptions.setServerAddress(host, options.port, idx)
    sessionOptions.setAuthenticationOptions(options.auth['option'])
    sessionOptions.setAutoRestartOnDisconnection(True)

    # NOTE: If running without a backup server, make many attempts to
    # connect/reconnect to give that host a chance to come back up (the
    # larger the number, the longer it will take for SessionStartupFailure
    # to come on startup, or SessionTerminated due to inability to fail
    # over).  We don't have to do that in a redundant configuration - it's
    # expected at least one server is up and reachable at any given time,
    # so only try to connect to each server once.
    sessionOptions.setNumStartAttempts(1 if len(options.hosts) > 1 else 1000)

    print("Connecting to port %d on %s" % (
        options.port, ", ".join(options.hosts)))

    tlsOptions = getTlsOptions(options)
    if tlsOptions is not None:
        sessionOptions.setTlsOptions(tlsOptions)

    session = blpapi.Session(sessionOptions)

    if not session.start():
        print("Failed to start session.")
        return

    subscriptionIdentity = session.createIdentity()

    if options.auth['option']:
        isAuthorized = False
        authServiceName = "//blp/apiauth"
        if session.openService(authServiceName):
            authService = session.getService(authServiceName)
            isAuthorized = authorize(
                authService, subscriptionIdentity, session,
                blpapi.CorrelationId("auth"),
                options.auth.get('manual'))
        if not isAuthorized:
            print("No authorization")
            return

    subscriptions = blpapi.SubscriptionList()
    for t in options.topics:
        topic = options.service + t
        subscriptions.add(topic,
                          options.fields,
                          options.options,
                          blpapi.CorrelationId(topic))

    session.subscribe(subscriptions, subscriptionIdentity)

    try:
        eventCount = 0
        while True:
            # Specify timeout to give a chance for Ctrl-C
            event = session.nextEvent(1000)
            for msg in event:
                if event.eventType() == blpapi.Event.SUBSCRIPTION_STATUS or \
                        event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                    print("%s - %s" % (msg.correlationIds()[0].value(), msg))
                else:
                    print(msg)
            if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                eventCount += 1
                if eventCount >= options.maxEvents:
                    break
    finally:
        session.stop()


if __name__ == "__main__":
    print("LocalMktdataSubscriptionExample")
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
