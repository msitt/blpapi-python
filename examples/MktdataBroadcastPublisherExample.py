# MktdataBroadcastPublisherExample.py
from __future__ import print_function
from __future__ import absolute_import

import time
from optparse import OptionParser, OptionValueError
from threading import Event
import os
import platform as plat
import sys
if sys.version_info >= (3, 8) and plat.system().lower() == "windows":
    # pylint: disable=no-member
    with os.add_dll_directory(os.getenv('BLPAPI_LIBDIR')):
        import blpapi
else:
    import blpapi

SESSION_TERMINATED = blpapi.Name("SessionTerminated")


class MyStream(object):
    def __init__(self, sid=""):
        self.id = sid


class MyEventHandler(object):
    def __init__(self, stop):
        self.stop = stop

    def processEvent(self, event, _session):
        for msg in event:
            print(msg)
            if event.eventType() == blpapi.Event.SESSION_STATUS:
                if msg.messageType() == SESSION_TERMINATED:
                    self.stop.set()
                continue


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
    parser = OptionParser(description="Publish market data.")
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
    parser.add_option("-f",
                      dest="fields",
                      help="fields (default: LAST_PRICE)",
                      metavar="field",
                      action="append",
                      default=[])
    parser.add_option("-m",
                      dest="messageType",
                      help="type of published event (default: %default)",
                      metavar="messageType",
                      default="MarketDataEvents")
    parser.add_option("-t",
                      dest="topic",
                      help="topic (default: %default)",
                      metavar="topic",
                      default="IBM Equity")
    parser.add_option("-g",
                      dest="groupId",
                      help="publisher groupId (defaults to unique value)")
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

    if not options.hosts:
        options.hosts = ["localhost"]

    if not options.fields:
        options.fields = ["BID", "ASK"]

    return options


def main():
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

    stop = Event()
    myEventHandler = MyEventHandler(stop)

    # Create a Session
    session = blpapi.ProviderSession(sessionOptions,
                                     myEventHandler.processEvent)

    # Start a Session
    if not session.start():
        print("Failed to start session.")
        return

    if options.groupId is not None:
        # NOTE: will perform explicit service registration here, instead
        # of letting createTopics do it, as the latter approach doesn't
        # allow for custom ServiceRegistrationOptions.
        serviceOptions = blpapi.ServiceRegistrationOptions()
        serviceOptions.setGroupId(options.groupId)
        if not session.registerService(options.service,
                                       session.getAuthorizedIdentity(),
                                       serviceOptions):
            print("Failed to register %s" % options.service)
            session.stop()
            return

    topicList = blpapi.TopicList()
    topicList.add(options.service + "/ticker/" + options.topic,
                  blpapi.CorrelationId(MyStream(options.topic)))

    # Create topics
    session.createTopics(topicList,
                         blpapi.ProviderSession.AUTO_REGISTER_SERVICES)
    # createTopics() is synchronous, topicList will be updated
    # with the results of topic creation (resolution will happen
    # under the covers)

    streams = []
    for i in range(topicList.size()):
        stream = topicList.correlationIdAt(i).value()
        status = topicList.statusAt(i)
        topicString = topicList.topicStringAt(i)

        if (status == blpapi.TopicList.CREATED):
            print("Start publishing on topic: %s" % topicString)
            stream.topic = session.getTopic(topicList.messageAt(i))
            streams.append(stream)
        else:
            print("Stream '%s': topic not created, status = %d" % (
                stream.id, status))

    service = session.getService(options.service)
    PUBLISH_MESSAGE_TYPE = blpapi.Name(options.messageType)

    try:
        # Now we will start publishing
        tickCount = 1
        while streams and not stop.is_set():
            event = service.createPublishEvent()
            eventFormatter = blpapi.EventFormatter(event)

            for stream in streams:
                topic = stream.topic
                if not topic.isActive():
                    print("[WARN] Publishing on an inactive topic.")
                eventFormatter.appendMessage(PUBLISH_MESSAGE_TYPE, topic)

                for i, f in enumerate(options.fields):
                    eventFormatter.setElement(f, tickCount + i + 1.0)

                tickCount += 1

            for msg in event:
                print(msg)

            session.publish(event)
            time.sleep(10)
    finally:
        # Stop the session
        session.stop()

if __name__ == "__main__":
    print("MktdataBroadcastPublisherExample")
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
