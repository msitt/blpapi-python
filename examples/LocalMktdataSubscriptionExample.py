# LocalMktdataSubscriptionExample.py
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

SUBSCRIPTION_FAILURE = blpapi.Name("SubscriptionFailure")
SUBSCRIPTION_TERMINATED = blpapi.Name("SubscriptionTerminated")
SESSION_STARTUP_FAILURE = blpapi.Name("SessionStartupFailure")
SESSION_TERMINATED = blpapi.Name("SessionTerminated")
SERVICE_OPEN_FAILURE = blpapi.Name("ServiceOpenFailure")

def authOptionCallback(option, opt, value, parser):
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
    """Parse command line arguments"""

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
                           "user|none|app=<app>|userapp=<app>|dir=<property>"
                           "|manual=<app,ip,user>"
                           " (default: none)\n"
                           "'none' is applicable to Desktop API product "
                           "that requires Bloomberg Professional service "
                           "to be installed locally.",
                      metavar="option",
                      action="callback",
                      callback=authOptionCallback,
                      type="string",
                      default={"option" : None})

    # TLS Options
    parser.add_option("--tls-client-credentials",
                      dest="tls_client_credentials",
                      help="name a PKCS#12 file to use as a source of "
                           "client credentials",
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
                      help="name a PKCS#7 file to use as a source of "
                           "trusted certificates",
                      metavar="option",
                      type="string")
    parser.add_option("--read-certificate-files",
                      dest="read_certificate_files",
                      help="(optional) read the TLS files and pass the blobs",
                      metavar="option",
                      action="store_true")

    # ZFP Options
    parser.add_option("--zfp-over-leased-line",
                      dest="zfpPort",
                      help="enable ZFP connections over leased lines on the "
                           "specified port (8194 or 8196)"
                           " (When this option is enabled, '-ip' and '-p'"
                           " arguments will be ignored.)",
                      metavar="port",
                      type="int")

    (options, args) = parser.parse_args()

    if not options.hosts:
        options.hosts = ["localhost"]

    if not options.topics:
        options.topics = ["/ticker/IBM Equity"]

    options.tlsOptions = getTlsOptions(options)

    options.remote = None
    if options.zfpPort:
        if not options.tlsOptions:
            raise RuntimeError("ZFP connections require TLS parameters")

        if options.zfpPort == 8194:
            options.remote = blpapi.ZfpUtil.REMOTE_8194
        elif options.zfpPort == 8196:
            options.remote = blpapi.ZfpUtil.REMOTE_8196
        else:
            raise RuntimeError("Invalid ZFP port: {}".format(options.zfpPort))

    return options

def getTlsOptions(options):
    """Parse TlsOptions from user input"""

    if (options.tls_client_credentials is None or
            options.tls_trust_material is None):
        return None

    print("TlsOptions enabled")
    if options.read_certificate_files:
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

    return blpapi.TlsOptions.createFromFiles(
        options.tls_client_credentials,
        options.tls_client_credentials_password,
        options.tls_trust_material)

def prepareStandardSessionOptions(options):
    """Prepares SessionOptions for connections other than ZFP Leased Line connections."""

    sessionOptions = blpapi.SessionOptions()
    for idx, host in enumerate(options.hosts):
        sessionOptions.setServerAddress(host, options.port, idx)

    print("Connecting to port {} on {}".format(options.port, ", ".join(options.hosts) ))

    if options.tlsOptions:
        sessionOptions.setTlsOptions(options.tlsOptions)

    return sessionOptions

def prepareZfpSessionOptions(options):
    """Prepares SessionOptions for ZFP Leased Line connections."""

    print("Creating a ZFP connection for leased lines.")
    sessionOptions = blpapi.ZfpUtil.getZfpOptionsForLeasedLines(
        options.remote,
        options.tlsOptions)
    return sessionOptions

def checkFailures(session):
    """Checks failure events published by the session."""

    # Note that the loop uses 'session.tryNextEvent' as all events have
    # been produced before calling this function, but there could be no events
    # at all in the queue if the OS fails to allocate resources.
    while True:
        event = session.tryNextEvent()
        if event is None:
            return

        eventType = event.eventType()
        for msg in event:
            print(msg)
            if processGenericMessage(eventType, msg):
                return

def processSubscriptionEvents(session, maxEvents):
    eventCount = 0
    while True:
        # Specify timeout to give a chance for Ctrl-C
        event = session.nextEvent(1000)
        eventType = event.eventType()
        for msg in event:
            print(msg)
            messageType = msg.messageType()
            if eventType == blpapi.Event.SUBSCRIPTION_STATUS:
                if messageType == SUBSCRIPTION_FAILURE \
                        or messageType == SUBSCRIPTION_TERMINATED:
                    errorDescription = msg.getElement("reason") \
                        .getElementAsString("description")
                    print("Subscription failed: {}".format(errorDescription))
                    printContactSupportMessage(msg)
            elif eventType == blpapi.Event.SUBSCRIPTION_DATA:
                if msg.recapType() == blpapi.Message.RECAPTYPE_SOLICITED:
                    if msg.getRequestId() is not None:
                        # An init paint tick can have an associated
                        # RequestId that is used to identify the
                        # source of the data and can be used when
                        # contacting support
                        print("Received init paint with RequestId {}".format(msg.getRequestId()))
            else:

                # SESSION_STATUS events can happen at any time and
                # should be handled as the session can be terminated,
                # e.g. session identity can be revoked at a later
                # time, which terminates the session.
                if processGenericMessage(eventType, msg):
                    return

        if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
            eventCount += 1
            if eventCount >= maxEvents:
                break

def processGenericMessage(eventType, message):
    """Prints error information if the 'message' is a failure message."""

    messageType = message.messageType()

    # When using a session identity, i.e.
    # 'SessionOptions.setSessionIdentityOptions(AuthOptions)', token
    # generation failure, authorization failure or revocation terminates the
    # session, in which case, applications only need to check session status
    # messages. Applications don't need to handle token or authorization messages
    if eventType == blpapi.Event.SESSION_STATUS:
        if messageType == SESSION_TERMINATED or \
        messageType == SESSION_STARTUP_FAILURE:
            error = message.getElement("reason").getElementAsString("description")
            print("Session failed to start or terminated: {}".format(error))
            printContactSupportMessage(message)
            # Session failed to start/terminated
            return True
    elif eventType == blpapi.Event.SERVICE_STATUS:
        if messageType == SERVICE_OPEN_FAILURE:
            serviceName = message.getElementAsString("serviceName")
            error = message.getElement("reason").getElementAsString("description")
            print("Failed to open {}: {}".format(serviceName, error))
            printContactSupportMessage(message)

    # Session OK
    return False

def printContactSupportMessage(msg):
    """Prints contact support message."""

    # Messages can have associated RequestIds which
    # identify operations (related to them) through the network.
    requestId = msg.getRequestId()
    if requestId is not None:
        print("When contacting support, please provide RequestId {}".format(requestId))

def main():
    """Main function"""

    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = prepareZfpSessionOptions(options) \
        if options.remote \
        else prepareStandardSessionOptions(options)
    sessionOptions.setSessionIdentityOptions(options.auth['option'])

    session = blpapi.Session(sessionOptions)
    try:
        if not session.start():
            checkFailures(session)
            print("Failed to start session.")
            return

        if not session.openService(options.service):
            checkFailures(session)
            return

        subscriptions = blpapi.SubscriptionList()
        for t in options.topics:
            topic = options.service + t
            subscriptions.add(topic,
                              options.fields,
                              options.options,
                              blpapi.CorrelationId(topic))
        session.subscribe(subscriptions)

        processSubscriptionEvents(session, options.maxEvents)
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
