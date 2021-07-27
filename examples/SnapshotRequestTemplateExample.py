"""SnapshotRequestTemplateExample.py"""
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
    """parse cli arguments"""
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

    (opts, _) = parser.parse_args()

    if not opts.hosts:
        opts.hosts = ["localhost"]

    if not opts.topics:
        opts.topics = ["/ticker/IBM US Equity"]

    return opts


def main():
    """main entry point"""
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    for idx, host in enumerate(options.hosts):
        sessionOptions.setServerAddress(host, options.port, idx)
    sessionOptions.setSessionIdentityOptions(options.auth['option'])
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

    session = blpapi.Session(sessionOptions)

    if not session.start():
        print("Failed to start session.")
        return

    fieldStr = "?fields=" + ",".join(options.fields)

    snapshots = []
    nextCorrelationId = 0
    for i, topic in enumerate(options.topics):
        subscriptionString = options.service + topic + fieldStr
        snapshots.append(session.createSnapshotRequestTemplate(
            subscriptionString,
            blpapi.CorrelationId(i)))
        nextCorrelationId += 1

    requestTemplateAvailable = blpapi.Name('RequestTemplateAvailable')
    eventCount = 0
    try:
        while True:
            # Specify timeout to give a chance for Ctrl-C
            event = session.nextEvent(1000)
            for msg in event:
                if event.eventType() == blpapi.Event.ADMIN and  \
                        msg.messageType() == requestTemplateAvailable:

                    for requestTemplate in snapshots:
                        try:
                            session.sendRequestTemplate(
                                requestTemplate,
                                blpapi.CorrelationId(nextCorrelationId))
                        except blpapi.Exception as err:
                            print("Failed to send due to: ", err)
                            snapshots.remove(requestTemplate)
                        nextCorrelationId += 1

                elif event.eventType() == blpapi.Event.RESPONSE or \
                        event.eventType() == blpapi.Event.PARTIAL_RESPONSE:

                    cid = msg.correlationIds()[0].value()
                    print("%s - %s" % (cid, msg))
                else:
                    print(msg)
            if event.eventType() == blpapi.Event.RESPONSE:
                eventCount += 1
                if eventCount >= options.maxEvents:
                    print("%d events processed, terminating." % eventCount)
                    break
            elif event.eventType() == blpapi.Event.TIMEOUT:
                for requestTemplate in snapshots:
                    try:
                        session.sendRequestTemplate(
                            requestTemplate,
                            blpapi.CorrelationId(nextCorrelationId))
                    except blpapi.Exception as err:
                        print("Failed to send due to: ", err)
                        snapshots.remove(requestTemplate)
                    nextCorrelationId += 1

    finally:
        session.stop()

if __name__ == "__main__":
    print("SnapshotRequestTemplateExample")
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl+C pressed. Stopping...")

__copyright__ = """
Copyright 2018. Bloomberg Finance L.P.

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
