# SimpleAsyncSubscription.py
from __future__ import print_function
from __future__ import absolute_import

import time
try:
    import thread
except ImportError:
    import _thread as thread
from optparse import OptionParser, OptionValueError

import os
import platform as plat
import sys
if sys.version_info >= (3, 8) and plat.system().lower() == "windows":
    # pylint: disable=no-member
    with os.add_dll_directory(os.getenv('BLPAPI_LIBDIR')):
        import blpapi
        from blpapi import Event as EventType
else:
    import blpapi
    from blpapi import Event as EventType


SESSION_STARTED = blpapi.Name("SessionStarted")
SESSION_STARTUP_FAILURE = blpapi.Name("SessionStartupFailure")

EVENT_TYPE_NAMES = {
    EventType.ADMIN: "ADMIN",
    EventType.SESSION_STATUS: "SESSION_STATUS",
    EventType.SUBSCRIPTION_STATUS: "SUBSCRIPTION_STATUS",
    EventType.REQUEST_STATUS: "REQUEST_STATUS",
    EventType.RESPONSE: "RESPONSE",
    EventType.PARTIAL_RESPONSE: "PARTIAL_RESPONSE",
    EventType.SUBSCRIPTION_DATA: "SUBSCRIPTION_DATA",
    EventType.SERVICE_STATUS: "SERVICE_STATUS",
    EventType.TIMEOUT: "TIMEOUT",
    EventType.AUTHORIZATION_STATUS: "AUTHORIZATION_STATUS",
    EventType.RESOLUTION_STATUS: "RESOLUTION_STATUS",
    EventType.TOPIC_STATUS: "TOPIC_STATUS",
    EventType.TOKEN_STATUS: "TOKEN_STATUS",
    EventType.REQUEST: "REQUEST"
}


class Error(Exception):
    pass


def topicName(security):
    if security.startswith("//"):
        return security
    else:
        return "//blp/mktdata/" + security


def printMessage(msg, eventType):
    print("#{0} msg received: [{1}] => {2}/{3}".format(
        thread.get_ident(),
        ", ".join(map(str, msg.correlationIds())),
        EVENT_TYPE_NAMES[eventType],
        msg))

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
    parser = OptionParser()
    parser.add_option("-a",
                      "--host",
                      dest="host",
                      help="HOST address to connect to",
                      metavar="HOST",
                      default="localhost")
    parser.add_option("-p",
                      "--port",
                      dest="port",
                      type="int",
                      help="PORT to connect to (%default)",
                      metavar="PORT",
                      default=8194)
    parser.add_option("-s",
                      "--security",
                      dest="securities",
                      help="security to subscribe to "
                      "('IBM US Equity' by default)",
                      metavar="SECURITY",
                      action="append",
                      default=[])
    parser.add_option("-f",
                      "--fields",
                      dest="fields",
                      help="comma "
                      "separated list of FIELDS to subscribe to "
                      "('LAST_PRICE,BID,ASK' by default)",
                      metavar="FIELDS",
                      default="LAST_PRICE,BID,ASK")
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

    poptions,_ = parser.parse_args()

    if not poptions.securities:
        poptions.securities = ["IBM US Equity"]
    return poptions


# Subscribe 'session' for the securities and fields specified in 'options'
def subscribe(session, poptions, identity=None):
    sl = blpapi.SubscriptionList()
    for s in poptions.securities:
        topic = topicName(s)
        cid = blpapi.CorrelationId(s)
        print("Subscribing {0} => {1}".format(cid, topic))
        sl.add(topic, poptions.fields, correlationId=cid)
    session.subscribe(sl, identity)


# Event handler
class MyEventHandler(object):
    def __init__(self, poptions):
        self.options = poptions

    def processEvent(self, event, session):
        try:
            eventType = event.eventType()
            for msg in event:
                # Print all aincoming messages including the SubscriptionData
                printMessage(msg, eventType)

                if eventType == EventType.SESSION_STATUS:
                    if msg.messageType() == SESSION_STARTED:
                        # Session.startAsync completed successfully
                        # Subscribe for the specified securities/fields
                        subscribe(session, self.options)
                    elif msg.messageType() == SESSION_STARTUP_FAILURE:
                        # Session.startAsync failed, raise exception to exit
                        raise Error("Can't start session")
        except Error as ex:
            print("Error in event handler:", ex)
            # Interrupt a "sleep loop" in main thread
            thread.interrupt_main()


def main():
    options = parseCmdLine()

    # Fill SessionOptions
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)
    sessionOptions.setSessionIdentityOptions(options.auth['option'])

    # Create a handler
    handler = MyEventHandler(options)

    # Create an EventDispatcher with 2 processing threads
    dispatcher = blpapi.EventDispatcher(2)

    # Create a Session
    session = blpapi.Session(sessionOptions, handler.processEvent, dispatcher)

    # Start dispatcher to "pump" the received events
    dispatcher.start()

    # Start session asynchronously
    if not session.startAsync():
        raise Exception("Can't initiate session start.")

    # Sleep until application will be interrupted by user (Ctrl+C pressed)
    # or because of the exception in event handler
    try:
        # Note that: 'thread.interrupt_main()' could be used to
        # correctly stop the application from 'processEvent'
        while True:
            time.sleep(1)
    finally:
        session.stop()
        dispatcher.stop()


if __name__ == "__main__":
    print("SimpleAsyncSubscription")
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
