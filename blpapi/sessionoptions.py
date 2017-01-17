# sessionoptions.py

"""A common interface shared between publish and consumer sessions.

This file defines a 'SessionOptions' class which is used to specify various
options during session creation.

Usage
-----

The following snippet shows how to use the SessionOptions when creating a
'Session'.

    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost(options.host)
    sessionOptions.setServerPort(options.port)
    session = blpapi.Session(sessionOptions)
    if not session.start():
        raise Exception("Can't start session.")

"""

from __future__ import absolute_import
from .exception import _ExceptionUtil
from . import internals
from . import utils
from .compat import with_metaclass


@with_metaclass(utils.MetaClassForClassesWithEnums)
class SessionOptions(object):
    """Options which the user can specify when creating a session.

    To use non-default options on a Session, create a SessionOptions instance
    and set the required options and then supply it when creating a Session.

    The possible options for how to connect to the API:

        AUTO - Automatic (desktop if available otherwise server)
        DAPI - Always connect to the desktop API
        SAPI - Always connect to the server API

    """

    AUTO = internals.CLIENTMODE_AUTO
    """Automatic (desktop if available otherwise server)"""
    DAPI = internals.CLIENTMODE_DAPI
    """Always connect to the desktop API"""
    SAPI = internals.CLIENTMODE_SAPI
    """Always connect to the server API"""

    def __init__(self):
        """Create a SessionOptions with all options set to the defaults"""
        self.__handle = internals.blpapi_SessionOptions_create()

    def __del__(self):
        try:
            self.destroy()
        except (NameError, AttributeError):
            pass

    def destroy(self):
        """Destroy this SessionOptions."""
        if self.__handle:
            internals.blpapi_SessionOptions_destroy(self.__handle)
            self.__handle = None

    def setServerHost(self, serverHost):
        """Set the API server host to connect to when using the server API.

        Set the API server host to connect to when using the server API to the
        specified 'host'. A hostname or an IPv4 address (that is, a.b.c.d).
        The default is "127.0.0.1".

        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setServerHost(self.__handle,
                                                          serverHost))

    def setServerPort(self, serverPort):
        """Set the port to connect to when using the server API.

        Set the port to connect to when using the server API to the specified
        'port'. The default is "8194".

        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setServerPort(self.__handle,
                                                          serverPort))

    def setServerAddress(self, serverHost, serverPort, index):
        """Set the server address at the specified 'index'.

        Set the server address at the specified 'index' using the specified
        'serverHost' and 'serverPort'.
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setServerAddress(self.__handle,
                                                             serverHost,
                                                             serverPort,
                                                             index))

    def removeServerAddress(self, index):
        """Remove the server address at the specified 'index'."""

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_removeServerAddress(self.__handle,
                                                                index))

    def setConnectTimeout(self, timeoutMilliSeconds):
        """Set the connection timeout in milliseconds.

        Set the connection timeout in milliseconds when connecting to the API.
        The default is 5000 milliseconds. Behavior is not defined unless the
        specified 'timeoutMilliSeconds' is in range of [1 .. 120000]
        milliseconds.

        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setConnectTimeout(
                self.__handle,
                timeoutMilliSeconds))

    def setDefaultServices(self, defaultServices):
        """Set the default service for the session.

        DEPRECATED
        Set the default service for the session. This function is deprecated;
        see 'setDefaultSubscriptionService'.

        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setDefaultServices(
                self.__handle,
                defaultServices))

    def setDefaultSubscriptionService(self, defaultSubscriptionService):
        """Set the default service for subscriptions.

        Set the default service for subscriptions which do not specify a
        subscription server to the specified 'defaultSubscriptionService'. The
        behavior is undefined unless 'defaultSubscriptionService' matches the
        regular expression '^//[-_.a-zA-Z0-9]+/[-_.a-zA-Z0-9]+$'. The default
        is "//blp/mktdata".  For more information on when this will be used see
        'QUALIFYING SUBSCRIPTION STRINGS' section in 'blpapi_subscriptionlist'.

        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setDefaultSubscriptionService(
                self.__handle,
                defaultSubscriptionService))

    def setDefaultTopicPrefix(self, prefix):
        """Set the default topic prefix.

        Set the default topic prefix to be used when a subscription does not
        specify a prefix to the specified 'prefix'. The default is "/ticker/".
        For more information on when this will be used see 'QUALIFYING
        SUBSCRIPTION STRINGS' section in 'blpapi_subscriptionlist'.

        """

        internals.blpapi_SessionOptions_setDefaultTopicPrefix(
            self.__handle,
            prefix)

    def setAllowMultipleCorrelatorsPerMsg(self,
                                          allowMultipleCorrelatorsPerMsg):
        """Associate more than one CorrelationId with a Message.

        Set whether the Session is allowed to associate more than one
        CorrelationId with a Message to the specified
        'allowMultipleCorrelatorsPerMsg'. The default is False. This means that
        if you have multiple subscriptions which overlap (that is a particular
        Message is relevant to all of them) you will be presented with the same
        message multiple times when you use the MessageIterator, each time with
        a different CorrelationId. If you specify True for this then a Message
        may be presented with multiple CorrelationId's.

        """

        internals.blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg(
            self.__handle,
            allowMultipleCorrelatorsPerMsg)

    def setClientMode(self, clientMode):
        """Set how to connect to the API. The default is AUTO.

        Set how to connect to the API. The default is AUTO which will try to
        connect to the desktop API but fall back to the server API if the
        desktop is not available. DAPI always connects to the desktop API and
        will fail if it is not available. SAPI always connects to the server
        API and will fail if it is not available.

        """

        internals.blpapi_SessionOptions_setClientMode(self.__handle,
                                                      clientMode)

    def setMaxPendingRequests(self, maxPendingRequests):
        """Set the maximum number of requests which can be pending.

        Set the maximum number of requests which can be pending to
        the specified 'maxPendingRequests'. The default is 1024.

        """

        internals.blpapi_SessionOptions_setMaxPendingRequests(
            self.__handle,
            maxPendingRequests)

    def setAuthenticationOptions(self, authOptions):
        """Set the specified 'authOptions' as authentication option."""
        internals.blpapi_SessionOptions_setAuthenticationOptions(
            self.__handle,
            authOptions)

    def setNumStartAttempts(self, numStartAttempts):
        """Set the maximum number of attempts to start a session.
        
        Set the maximum number of attempts to start a session by connecting a
        server.
        """
        internals.blpapi_SessionOptions_setNumStartAttempts(self.__handle,
                                                            numStartAttempts)

    def setAutoRestartOnDisconnection(self, autoRestart):
        """Set whether automatically restarting connection if disconnected."""
        internals.blpapi_SessionOptions_setAutoRestartOnDisconnection(
            self.__handle,
            autoRestart)

    def setSlowConsumerWarningHiWaterMark(self, hiWaterMark):
        """Set the point at which "slow consumer" events will be generated,
        using the specified 'highWaterMark' as a fraction of
        'maxEventQueueSize'; the default value is 0.75.  A warning event will
        be generated when the number of outstanding undelivered events passes
        above 'hiWaterMark * maxEventQueueSize'.  The behavior of the function
        is undefined unless '0.0 < hiWaterMark <= 1.0'.  Further, at the time
        that 'Session.start()' is called, it must be the case that
        'slowConsumerWarningLoWaterMark() * maxEventQueueSize()' <
        'slowConsumerWarningHiWaterMark() * maxEventQueueSize()'."""
        err = internals.blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark(
                self.__handle, hiWaterMark)
        _ExceptionUtil.raiseOnError(err)

    def setSlowConsumerWarningLoWaterMark(self, loWaterMark):
        """Set the point at which "slow consumer cleared" events will be
        generated, using the specified 'loWaterMark' as a fraction of
        'maxEventQueueSize'; the default value is 0.5.  A warning cleared event
        will be generated when the number of outstanding undelivered events
        drops below 'loWaterMark * maxEventQueueSize'.  The behavior of the
        function is undefined unless '0.0 <= loWaterMark < 1.0'.  Further, at
        the time that 'Session.start()' is called, it must be the case that
        'slowConsumerWarningLoWaterMark() * maxEventQueueSize()' <
        'slowConsumerWarningHiWaterMark() * maxEventQueueSize()'."""
        err = internals.blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark(
                                         self.__handle, loWaterMark)
        _ExceptionUtil.raiseOnError(err)

    def setMaxEventQueueSize(self, eventQueueSize):
        """Set the maximum number of outstanding undelivered events per session
        to the specified 'eventQueueSize'.  All subsequent events delivered
        over the network will be dropped by the session if the number of
        outstanding undelivered events is 'eventQueueSize', the specified
        threshold.  The default value is 10000."""
        internals.blpapi_SessionOptions_setMaxEventQueueSize(self.__handle,
                eventQueueSize)

    def setKeepAliveEnabled(self, isEnabled):
        """If the specified 'isEnabled' is False, then disable all keep-alive
        mechanisms, both from the client to the server and from the server to
        the client; otherwise enable keep-alive pings both from the client to
        the server (as configured by 'setDefaultKeepAliveInactivityTime' and
        'setDefaultKeepAliveResponseTimeout' if the connection supports
        ping-based keep-alives), and from the server to the client as specified
        by the server configuration."""
        keepAliveValue = 1 if isEnabled else 0
        err = internals.blpapi_SessionOptions_setKeepAliveEnabled(
                self.__handle, keepAliveValue)
        _ExceptionUtil.raiseOnError(err)

    def setDefaultKeepAliveInactivityTime(self, inactivityMsecs):
        """ Set to the specified 'inactivityMsecs' the amount of time that no
        traffic can be received on a connection before the ping-based
        keep-alive mechanism is triggered; if no traffic is received for this
        duration then a keep-alive ping is sent to the remote end to solicit a
        response.  If 'inactivityMsecs == 0', then no keep-alive pings will be
        sent.  The behavior of this function is undefined unless
        'inactivityMsecs' is a non-negative value.  The default value is 20,000
        milliseconds.  Note that not all back-end connections provide
        ping-based keep-alives; this option is ignored by such connections."""
        err = internals.blpapi_SessionOptions_setDefaultKeepAliveInactivityTime(
                self.__handle, inactivityMsecs)
        _ExceptionUtil.raiseOnError(err)

    def setDefaultKeepAliveResponseTimeout(self, timeoutMsecs):
        """ When a keep-alive ping is sent, wait for the specified
        'timeoutMsecs' to receive traffic (of any kind) before terminating the
        connection due to inactivity.  If 'timeoutMsecs == 0', then connections
        are never terminated due to the absence of traffic after a keep-alive
        ping.  The behavior of this function is undefined unless 'timeoutMsecs'
        is a non-negative value.  The default value is 5,000 milliseconds.
        Note that not all back-end connections provide support for ping-based
        keep-alives; this option is ignored by such connections."""
        err = internals.blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout(
                self.__handle, timeoutMsecs)
        _ExceptionUtil.raiseOnError(err)

    def setRecordSubscriptionDataReceiveTimes(self, shouldRecord):
        """Set whether the receipt time (accessed via
        'blpapi.Message.timeReceived') should be recorded for subscription data
        messages. By default, the receipt time for these messages is not
        recorded."""
        internals.blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes(
                self.__handle, shouldRecord)

    def serverHost(self):
        """Return the server host option in this SessionOptions instance."""

        return internals.blpapi_SessionOptions_serverHost(self.__handle)

    def serverPort(self):
        """Return the server port that this session connects to."""

        return internals.blpapi_SessionOptions_serverPort(self.__handle)

    def numServerAddresses(self):
        """Return the number of server addresses."""

        return internals.blpapi_SessionOptions_numServerAddresses(
            self.__handle)

    def getServerAddress(self, index):
        """Return tuple of the server name and port indexed by 'index'."""

        errorCode, host, port = \
            internals.blpapi_SessionOptions_getServerAddress(self.__handle,
                                                             index)

        _ExceptionUtil.raiseOnError(errorCode)

        return host, port

    def serverAddresses(self):
        """Return an iterator over server addresses for this SessionOptions.
        """

        return utils.Iterator(self,
                              SessionOptions.numServerAddresses,
                              SessionOptions.getServerAddress)

    def connectTimeout(self):
        """Return the value of the connection timeout option.

        Return the value of the connection timeout option in this
        SessionOptions instance in milliseconds.

        """

        return internals.blpapi_SessionOptions_connectTimeout(self.__handle)

    def defaultServices(self):
        """Return all default services in one string."""
        return internals.blpapi_SessionOptions_defaultServices(self.__handle)

    def defaultSubscriptionService(self):
        """Return the default subscription service.

        Return the value of the default subscription service option in this
        SessionOptions instance.

        """

        return internals.blpapi_SessionOptions_defaultSubscriptionService(
            self.__handle)

    def defaultTopicPrefix(self):
        """Return the default topic prefix.

        Return the value of the default topic prefix option in this
        SessionOptions instance.

        """

        return internals.blpapi_SessionOptions_defaultTopicPrefix(
            self.__handle)

    def allowMultipleCorrelatorsPerMsg(self):
        """Return the value of the allow multiple correlators per message.

        Return the value of the allow multiple correlators per message option
        in this SessionOptions instance.

        """

        return internals.blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg(
            self.__handle) != 0

    def clientMode(self):
        """Return the value of the client mode option.

        Return the value of the client mode option in this SessionOptions
        instance.

        """

        return internals.blpapi_SessionOptions_clientMode(self.__handle)

    def maxPendingRequests(self):
        """Return the value of the maximum pending request option.

        Return the value of the maximum pending request option in this
        SessionOptions instance.

        """

        return internals.blpapi_SessionOptions_maxPendingRequests(
            self.__handle)

    def autoRestartOnDisconnection(self):
        """Return whether automatically restart connection if disconnected."""
        return internals.blpapi_SessionOptions_autoRestartOnDisconnection(
            self.__handle) != 0

    def authenticationOptions(self):
        """Return authentication options in a string."""
        return internals.blpapi_SessionOptions_authenticationOptions(
            self.__handle)

    def numStartAttempts(self):
        """Return the maximum number of attempts to start a session.  Return
        the maximum number of attempts to start a session by connecting a
        server.  """
        return internals.blpapi_SessionOptions_numStartAttempts(self.__handle)

    def recordSubscriptionDataReceiveTimes(self):
        """Return whether the receipt time (accessed via
        'blpapi.Message.timeReceived') should be recorded for subscription data
        messages."""
        return internals.blpapi_SessionOptions_recordSubscriptionDataReceiveTimes(
                self.__handle)

    def slowConsumerWarningHiWaterMark(self):
        """Return the fraction of maxEventQueueSize at which "slow consumer"
        event will be generated."""
        return internals.blpapi_SessionOptions_slowConsumerWarningHiWaterMark(
                self.__handle)

    def slowConsumerWarningLoWaterMark(self):
        """Return the fraction of maxEventQueueSize at which "slow consumer
        cleared" event will be generated."""
        return internals.blpapi_SessionOptions_slowConsumerWarningLoWaterMark(
                self.__handle)

    def maxEventQueueSize(self):
        """Return the value of maximum outstanding undelivered events that the
        session is configured with."""
        return internals.blpapi_SessionOptions_maxEventQueueSize(self.__handle)

    def defaultKeepAliveInactivityTime(self):
        """Return the interval (in milliseconds) a connection has to remain
        inactive (receive no data) before a keep alive probe will be sent."""
        return internals.blpapi_SessionOptions_defaultKeepAliveInactivityTime(
                self.__handle)

    def defaultKeepAliveResponseTimeout(self):
        """Return the time (in milliseconds) the library will wait for response
        to a keep alive probe before declaring it lost."""
        return internals.blpapi_SessionOptions_defaultKeepAliveResponseTimeout(
                self.__handle)

    def keepAliveEnabled(self):
        """Return True if the keep-alive mechanism is enabled; otherwise
        return False."""
        return internals.blpapi_SessionOptions_keepAliveEnabled(self.__handle)

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle


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
