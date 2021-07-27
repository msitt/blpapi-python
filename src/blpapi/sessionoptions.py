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
from . import AuthOptions
from . import CorrelationId
from . import internals
from . import utils
from .utils import get_handle
from .compat import with_metaclass
from .chandle import CHandle

# pylint: disable=too-many-public-methods

@with_metaclass(utils.MetaClassForClassesWithEnums)
class SessionOptions(CHandle):
    """Options which the user can specify when creating a session.

    To use non-default options on a :class:`Session`, create a
    :class:`SessionOptions` instance and set the required options and then
    supply it when creating a :class:`Session`.

    The class attributes represent the possible options for how to connect to
    the API.
    """

    AUTO = internals.CLIENTMODE_AUTO
    """Automatic (desktop if available otherwise server)"""
    DAPI = internals.CLIENTMODE_DAPI
    """Always connect to the desktop API"""
    SAPI = internals.CLIENTMODE_SAPI
    """Always connect to the server API"""

    def __init__(self):
        """Create a :class:`SessionOptions` with all options set to the
        defaults"""
        selfhandle = internals.blpapi_SessionOptions_create()
        super(SessionOptions, self).__init__(
            selfhandle,
            internals.blpapi_SessionOptions_destroy)
        self.__handle = selfhandle

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string representation of this SessionOptions. Call of
        'str(options)' is equivalent to 'options.toString()' called with
        default parameters.

        """
        return self.toString()

    def setServerHost(self, serverHost):
        """Set the API server host to connect to when using the server API.

        Args:
            serverHost (str): Server host

        Set the API server host to connect to when using the server API to the
        specified ``serverHost``. The server host is either a hostname or an
        IPv4 address (that is, ``a.b.c.d``).  The default is ``127.0.0.1``.
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setServerHost(self.__handle,
                                                          serverHost))

    def setServerPort(self, serverPort):
        """Set the port to connect to when using the server API.

        Args:
            serverPort (int): Server port

        Set the port to connect to when using the server API to the specified
        ``serverPort``. The default is ``8194``.
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setServerPort(self.__handle,
                                                          serverPort))

    def setServerAddress(self, serverHost, serverPort, index):
        """Set the server address at the specified ``index``.

        Args:
            serverHost (str): Server host
            serverPort (int): Server port
            index (int): Index to set the address at

        Set the server address at the specified ``index`` using the specified
        ``serverHost`` and ``serverPort``.
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setServerAddress(self.__handle,
                                                             serverHost,
                                                             serverPort,
                                                             index))

    def removeServerAddress(self, index):
        """Remove the server address at the specified ``index``.

        Args:
            index (int): Index to remove the address at
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_removeServerAddress(self.__handle,
                                                                index))

    def setConnectTimeout(self, timeoutMilliSeconds):
        """Set the connection timeout in milliseconds.

        Args:
            timeoutMilliSeconds (int): Timeout threshold in milliseconds

        Set the connection timeout in milliseconds when connecting to the API.
        The default is ``5000`` milliseconds. Behavior is not defined unless
        the specified ``timeoutMilliSeconds`` is in range of ``[1 .. 120000]``
        milliseconds.
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setConnectTimeout(
                self.__handle,
                timeoutMilliSeconds))

    def setDefaultServices(self, defaultServices):
        """Set the default service for the session.

        Args:
            defaultServices ([str]): The default services

        **DEPRECATED**

        Set the default service for the session. This function is deprecated;
        see :meth:`setDefaultSubscriptionService()`.
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setDefaultServices(
                self.__handle,
                defaultServices))

    def setDefaultSubscriptionService(self, defaultSubscriptionService):
        """Set the default service for subscriptions.

        Args:
            defaultSubscriptionService (str): Identifier for the service to be
                used as default

        Set the default service for subscriptions which do not specify a
        subscription server to the specified ``defaultSubscriptionService``.
        The behavior is undefined unless ``defaultSubscriptionService`` matches
        the regular expression ``^//[-_.a-zA-Z0-9]+/[-_.a-zA-Z0-9]+$``. The
        default is ``//blp/mktdata``.
        """

        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setDefaultSubscriptionService(
                self.__handle,
                defaultSubscriptionService))

    def setDefaultTopicPrefix(self, prefix):
        """Set the default topic prefix.

        Args:
            prefix (str): The topic prefix to set

        Set the default topic prefix to be used when a subscription does not
        specify a prefix to the specified ``prefix``. The default is
        ``/ticker/``.
        """

        internals.blpapi_SessionOptions_setDefaultTopicPrefix(
            self.__handle,
            prefix)

    def setAllowMultipleCorrelatorsPerMsg(self,
                                          allowMultipleCorrelatorsPerMsg):
        """Associate more than one :class:`CorrelationId` with a
        :class:`Message`.

        Args:
            allowMultipleCorrelatorsPerMsg (bool): Value to set the option to

        Set whether the :class:`Session` is allowed to associate more than one
        :class:`CorrelationId` with a :class:`Message` to the specified
        ``allowMultipleCorrelatorsPerMsg``. The default is ``False``. This
        means that if you have multiple subscriptions which overlap (that is a
        particular :class:`Message` is relevant to all of them) you will be
        presented with the same message multiple times when you use the
        ``MessageIterator``, each time with a different :class:`CorrelationId`.
        If you specify ``True`` for this then a :class:`Message` may be
        presented with multiple :class:`CorrelationId`\ 's.
        """

        internals.blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg(
            self.__handle,
            allowMultipleCorrelatorsPerMsg)

    def setClientMode(self, clientMode):
        """Set how to connect to the API. The default is :attr:`AUTO`.

        Args:
            clientMode (int): The client mode

        Set how to connect to the API. The default is :attr:`AUTO` which will
        try to connect to the desktop API but fall back to the server API if
        the desktop is not available. :attr:`DAPI` always connects to the
        desktop API and will fail if it is not available. :attr:`SAPI` always
        connects to the server API and will fail if it is not available.
        """

        internals.blpapi_SessionOptions_setClientMode(self.__handle,
                                                      clientMode)

    def setMaxPendingRequests(self, maxPendingRequests):
        """Set the maximum number of requests which can be pending.

        Args:
            maxPendingRequests (int): Maximum number of pending requests

        Set the maximum number of requests which can be pending to the
        specified ``maxPendingRequests``. The default is ``1024``.
        """

        internals.blpapi_SessionOptions_setMaxPendingRequests(
            self.__handle,
            maxPendingRequests)

    def setSessionIdentityOptions(self,
                                  authOptions,
                                  correlationId=None):
        """Sets the specified ``authOptions`` as the :class:`AuthOptions` for
        the session identity, enabling automatic authorization of the session
        identity during startup.

        Args:
            authOptions (AuthOptions): the authorization options to use for the
                session identity.
            correlationId (CorrelationId): Optional. Used to identify the
                messages associated with the session identity.

        Returns:
            CorrelationId: The actual :class:`CorrelationId` that identifies
            the messages associated with the session identity.

        The session identity lifetime is tied to the session's lifetime, so it
        is guaranteed that the session identity will remain authorized during
        the entire duration of the session. The identity will be authorized
        before the session starts. The session will terminate if the identity
        fails to authorize or is revoked.

        The session identity is used to send requests and make subscriptions if
        no other identity is provided.

        By default the session identity is not authorized.

        It is possible to pass ``None`` as ``authOptions``, to reset this value
        to its default state.
        """
        if correlationId is None:
            correlationId = CorrelationId()

        if authOptions is None:
            # Use an 'empty' authoptions instance to reset the value
            retcode, authOptions_handle = internals \
                .blpapi_AuthOptions_create_default()
            _ExceptionUtil.raiseOnError(retcode)
            authOptions = AuthOptions(authOptions_handle)

        retcode = internals.blpapi_SessionOptions_setSessionIdentityOptions(
            self._handle(),
            get_handle(authOptions),
            get_handle(correlationId))
        _ExceptionUtil.raiseOnError(retcode)
        return correlationId

    def setAuthenticationOptions(self, authOptions):
        """Set the specified ``authOptions`` as the authentication options.

        Args:
            authOptions (str): The options used during authentication.
        """
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
        """Set whether automatically restarting connection if disconnected.

        Args:
            autoRestart (bool): Whether to automatically restart if
                disconnected
        """
        internals.blpapi_SessionOptions_setAutoRestartOnDisconnection(
            self.__handle,
            autoRestart)

    def setSlowConsumerWarningHiWaterMark(self, hiWaterMark):
        """Set the point at which "slow consumer" events will be generated.

        Args:
            hiWaterMark (float): Fraction of :meth:`maxEventQueueSize()`

        Set the point at which "slow consumer" events will be generated, using
        the specified ``hiWaterMark`` as a fraction of
        :meth:`maxEventQueueSize()`; the default value is ``0.75``.  A warning
        event will be generated when the number of outstanding undelivered
        events passes above ``hiWaterMark * maxEventQueueSize()``.  The
        behavior of the function is undefined unless ``0.0 < hiWaterMark <=
        1.0``.  Further, at the time that :meth:`Session.start()` is called, it
        must be the case that ``slowConsumerWarningLoWaterMark() *
        maxEventQueueSize()`` < ``slowConsumerWarningHiWaterMark() *
        maxEventQueueSize()``.
        """
        err = internals.blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark(
            self.__handle, hiWaterMark)
        _ExceptionUtil.raiseOnError(err)

    def setSlowConsumerWarningLoWaterMark(self, loWaterMark):
        """Set the point at which "slow consumer cleared" events will be
        generated

        Args:
            loWaterMark (float): Fraction of :meth:`maxEventQueueSize()`

        Set the point at which "slow consumer cleared" events will be
        generated, using the specified ``loWaterMark`` as a fraction of
        :meth:`maxEventQueueSize()`; the default value is ``0.5``.  A warning
        cleared event will be generated when the number of outstanding
        undelivered events drops below ``loWaterMark * maxEventQueueSize``.
        The behavior of the function is undefined unless ``0.0 <= loWaterMark <
        1.0``.  Further, at the time that :meth:`Session.start()` is called, it
        must be the case that ``slowConsumerWarningLoWaterMark() *
        maxEventQueueSize()`` < ``slowConsumerWarningHiWaterMark() *
        maxEventQueueSize()``.
        """
        err = internals.blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark(
            self.__handle, loWaterMark)
        _ExceptionUtil.raiseOnError(err)

    def setMaxEventQueueSize(self, eventQueueSize):
        """Set the maximum number of outstanding undelivered events per
        session.

        Args:
            eventQueueSize (int): Maximum number of outstanding undelivered
                events

        Set the maximum number of outstanding undelivered events per session to
        the specified ``eventQueueSize``.  All subsequent events delivered over
        the network will be dropped by the session if the number of outstanding
        undelivered events is ``eventQueueSize``, the specified threshold.  The
        default value is ``10000``.
        """
        internals.blpapi_SessionOptions_setMaxEventQueueSize(
            self.__handle,
            eventQueueSize)

    def setKeepAliveEnabled(self, isEnabled):
        """Set whether to enable keep-alive pings.

        Args:
            isEnabled (bool): Whether to enable keep-alive pings

        If the specified ``isEnabled`` is ``False``, then disable all
        keep-alive mechanisms, both from the client to the server and from the
        server to the client; otherwise enable keep-alive pings both from the
        client to the server (as configured by
        :meth:`setDefaultKeepAliveInactivityTime()` and
        :meth:`setDefaultKeepAliveResponseTimeout()` if the connection supports
        ping-based keep-alives), and from the server to the client as specified
        by the server configuration.
        """
        keepAliveValue = 1 if isEnabled else 0
        err = internals.blpapi_SessionOptions_setKeepAliveEnabled(
            self.__handle, keepAliveValue)
        _ExceptionUtil.raiseOnError(err)

    def setDefaultKeepAliveInactivityTime(self, inactivityMsecs):
        """Set the amount of time that no traffic can be received before the
        keep-alive mechanism is triggered.

        Args:
            inactivityMsecs (int): Amount of time in milliseconds

        Set to the specified ``inactivityMsecs`` the amount of time that no
        traffic can be received on a connection before the ping-based
        keep-alive mechanism is triggered; if no traffic is received for this
        duration then a keep-alive ping is sent to the remote end to solicit a
        response.  If ``inactivityMsecs == 0``, then no keep-alive pings will
        be sent.  The behavior of this function is undefined unless
        ``inactivityMsecs`` is a non-negative value.  The default value is
        ``20,000`` milliseconds.

        Note:
            Not all back-end connections provide ping-based keep-alives;
            this option is ignored by such connections.
        """
        err = internals.blpapi_SessionOptions_setDefaultKeepAliveInactivityTime(
            self.__handle, inactivityMsecs)
        _ExceptionUtil.raiseOnError(err)

    def setDefaultKeepAliveResponseTimeout(self, timeoutMsecs):
        """Set the timeout for terminating the connection due to inactivity.

        Args:
            timeoutMsecs (int): Timeout threshold in milliseconds

        When a keep-alive ping is sent, wait for the specified ``timeoutMsecs``
        to receive traffic (of any kind) before terminating the connection due
        to inactivity.  If ``timeoutMsecs == 0``, then connections are never
        terminated due to the absence of traffic after a keep-alive ping.  The
        behavior of this function is undefined unless ``timeoutMsecs`` is a
        non-negative value.  The default value is ``5,000`` milliseconds.

        Note:
            that not all back-end connections provide support for ping-based
            keep-alives; this option is ignored by such connections.
        """
        err = internals.blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout(
            self.__handle, timeoutMsecs)
        _ExceptionUtil.raiseOnError(err)

    def setFlushPublishedEventsTimeout(self, timeoutMsecs):
        """
        Args:
            timeoutMsecs (int): Timeout threshold in milliseconds

        Set the timeout, in milliseconds, for :class:`ProviderSession` to flush
        published events before stopping. The behavior is not defined unless
        the specified ``timeoutMsecs`` is a positive value. The default value
        is ``2000``.
        """
        internals.blpapi_SessionOptions_setFlushPublishedEventsTimeout(
            self.__handle, timeoutMsecs)

    def setRecordSubscriptionDataReceiveTimes(self, shouldRecord):
        """
        Args:
            shouldRecord (bool): Whether to record the receipt time

        Set whether the receipt time (accessed via
        :meth:`.Message.timeReceived()`) should be recorded for subscription
        data messages. By default, the receipt time for these messages is not
        recorded.
        """
        internals.blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes(
            self.__handle, shouldRecord)

    def setServiceCheckTimeout(self, timeoutMsecs):
        """
        Args:
            timeoutMsecs (int): Timeout threshold in milliseconds

        Set the timeout, in milliseconds, when opening a service for checking
        what version of the schema should be downloaded.  The behavior is not
        defined unless ``timeoutMsecs`` is a positive value.  The default
        timeout is ``60,000`` milliseconds.
        """
        err = internals.blpapi_SessionOptions_setServiceCheckTimeout(
            self.__handle, timeoutMsecs)
        _ExceptionUtil.raiseOnError(err)

    def setServiceDownloadTimeout(self, timeoutMsecs):
        """
        Args:
            timeoutMsecs (int): Timeout threshold in milliseconds

        Set the timeout, in milliseconds, when opening a service for
        downloading the service schema. The behavior is not defined unless the
        specified ``timeoutMsecs`` is a positive value. The default timeout is
        ``120,000`` milliseconds.
        """
        err = internals.blpapi_SessionOptions_setServiceDownloadTimeout(
            self.__handle, timeoutMsecs)
        _ExceptionUtil.raiseOnError(err)

    def setTlsOptions(self, tlsOptions):
        """Set the TLS options

        Args:
            tlsOptions (TlsOptions): The TLS options
        """
        internals.blpapi_SessionOptions_setTlsOptions(
            self.__handle,
            get_handle(tlsOptions))

    def setBandwidthSaveModeDisabled(self, isDisabled):
        """Specify whether to disable bandwidth saving measures.

        Args:
            isDisabled (bool): Whether to disable bandwidth saving measures.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_SessionOptions_setBandwidthSaveModeDisabled(
                self.__handle,
                isDisabled))

    def serverHost(self):
        """
        Returns:
            str: The server host option in this :class:`SessionOptions`
                instance.
        """

        return internals.blpapi_SessionOptions_serverHost(self.__handle)

    def serverPort(self):
        """
        Returns:
            int: The server port that this session connects to.
        """

        return internals.blpapi_SessionOptions_serverPort(self.__handle)

    def numServerAddresses(self):
        """
        Returns:
            int: The number of server addresses.
        """

        return internals.blpapi_SessionOptions_numServerAddresses(
            self.__handle)

    def getServerAddress(self, index):
        """
        Returns:
            (str, int): Server name and port indexed by ``index``.
        """

        errorCode, host, port = \
            internals.blpapi_SessionOptions_getServerAddress(
                self.__handle,
                index)

        _ExceptionUtil.raiseOnError(errorCode)

        return host, port

    def serverAddresses(self):
        """
        Returns:
            Iterator over server addresses for this :class:`SessionOptions`.
        """

        return utils.Iterator(self,
                              SessionOptions.numServerAddresses,
                              SessionOptions.getServerAddress)

    def connectTimeout(self):
        """
        Returns:
            int: The value of the connection timeout option.
        """

        return internals.blpapi_SessionOptions_connectTimeout(self.__handle)

    def defaultServices(self):
        """
        Returns:
            str: All default services in one string.
        """
        return internals.blpapi_SessionOptions_defaultServices(self.__handle)

    def defaultSubscriptionService(self):
        """
        Returns:
            str: The default subscription service.
        """

        return internals.blpapi_SessionOptions_defaultSubscriptionService(
            self.__handle)

    def defaultTopicPrefix(self):
        """
        Returns:
            str: The default topic prefix.
        """

        return internals.blpapi_SessionOptions_defaultTopicPrefix(
            self.__handle)

    def allowMultipleCorrelatorsPerMsg(self):
        """
        Returns:
            bool: The value of the allow multiple correlators per message
            option.
        """

        return internals.blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg(
            self.__handle) != 0

    def clientMode(self):
        """
        Returns:
            int: The value of the client mode option.
        """

        return internals.blpapi_SessionOptions_clientMode(self.__handle)

    def maxPendingRequests(self):
        """
        Returns:
            int: The value of the maximum pending request option.
        """

        return internals.blpapi_SessionOptions_maxPendingRequests(
            self.__handle)

    def autoRestartOnDisconnection(self):
        """
        Returns:
            bool: Whether automatically restart connection if disconnected.
        """
        return internals.blpapi_SessionOptions_autoRestartOnDisconnection(
            self.__handle) != 0

    def authenticationOptions(self):
        """
        Returns:
            str: Authentication options in a string.
        """
        return internals.blpapi_SessionOptions_authenticationOptions(
            self.__handle)

    def numStartAttempts(self):
        """
        Returns:
            int: The maximum number of attempts to start a session.
        """
        return internals.blpapi_SessionOptions_numStartAttempts(self.__handle)

    def recordSubscriptionDataReceiveTimes(self):
        """
        Returns:
            bool: Whether the receipt time (accessed via
            :meth:`Message.timeReceived()`) should be recorded for subscription
            data messages.
        """
        return internals.blpapi_SessionOptions_recordSubscriptionDataReceiveTimes(
            self.__handle)

    def slowConsumerWarningHiWaterMark(self):
        """
        Returns:
            float: The fraction of :meth:`maxEventQueueSize()` at which "slow
            consumer" event will be generated.
        """
        return internals.blpapi_SessionOptions_slowConsumerWarningHiWaterMark(
            self.__handle)

    def slowConsumerWarningLoWaterMark(self):
        """
        Returns:
            float: The fraction of :meth:`maxEventQueueSize()` at which "slow
            consumer cleared" event will be generated.
        """
        return internals.blpapi_SessionOptions_slowConsumerWarningLoWaterMark(
            self.__handle)

    def maxEventQueueSize(self):
        """
        Returns:
            int: The value of maximum outstanding undelivered events that the
            session is configured with.
        """
        return internals.blpapi_SessionOptions_maxEventQueueSize(self.__handle)

    def defaultKeepAliveInactivityTime(self):
        """
        Returns:
            int: The interval (in milliseconds) a connection has to remain
            inactive (receive no data) before a keep alive probe will be sent.
        """
        return internals.blpapi_SessionOptions_defaultKeepAliveInactivityTime(
            self.__handle)

    def defaultKeepAliveResponseTimeout(self):
        """
        Returns:
            int: The time (in milliseconds) the library will wait for response
            to a keep alive probe before declaring it lost.
        """
        return internals.blpapi_SessionOptions_defaultKeepAliveResponseTimeout(
            self.__handle)

    def flushPublishedEventsTimeout(self):
        """
        Returns:
            int: The timeout, in milliseconds, for :class:`ProviderSession` to
            flush published events before stopping. The default value is
            ``2000``.
        """
        return internals.blpapi_SessionOptions_flushPublishedEventsTimeout(
            self.__handle)

    def keepAliveEnabled(self):
        """
        Returns:
            bool: ``True`` if the keep-alive mechanism is enabled; otherwise
            return ``False``.
        """
        return internals.blpapi_SessionOptions_keepAliveEnabled(self.__handle)

    def serviceCheckTimeout(self):
        """
        Returns:
            int: The value of the service check timeout option in this
            :class:`SessionOptions` instance in milliseconds.
        """
        return internals.blpapi_SessionOptions_serviceCheckTimeout(
            self.__handle)

    def serviceDownloadTimeout(self):
        """
        Returns:
            int: The value of the service download timeout option in this
            :class:`SessionOptions` instance in milliseconds.
        """
        return internals.blpapi_SessionOptions_serviceDownloadTimeout(
            self.__handle)

    def bandwidthSaveModeDisabled(self):
        """
        Returns:
            bool: Whether bandwidth saving measures are disabled.
        """
        return bool(internals.blpapi_SessionOptions_bandwidthSaveModeDisabled(
            self.__handle))

    def toString(self, level=0, spacesPerLevel=4):
        """Format this :class:`SessionOptions` to the string.

        Args:
            level (int): Indentation level
            spacesPerLevel (int): Number of spaces per indentation level for
                this and all nested objects

        Returns:
            str: This object formatted as a string

        If ``level`` is negative, suppress indentation of the first line. If
        ``spacesPerLevel`` is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by ``level``).
        """
        return internals.blpapi_SessionOptions_printHelper(
            self.__handle,
            level,
            spacesPerLevel)

class TlsOptions(CHandle):
    """SSL configuration options

    :class:`TlsOptions` instances maintain client credentials and trust
    material used by a session to establish secure mutually authenticated
    connections to endpoints.

    The client credentials comprise an encrypted private key with a client
    certificate. The trust material comprises one or more certificates.

    :class:`TlsOptions` objects are created using :meth:`createFromFiles()` or
    :meth:`createFromBlobs()` accepting the DER encoded client credentials in
    PKCS#12 format and the DER encoded trusted material in PKCS#7 format.
    """

    def __init__(self, handle):
        super(TlsOptions, self).__init__(
            handle, internals.blpapi_TlsOptions_destroy)
        self.__handle = handle

    def setTlsHandshakeTimeoutMs(self, timeoutMs):
        """
        Args:
            timeoutMs (int): Timeout threshold in milliseconds

        Set the TLS handshake timeout to the specified ``timeoutMs``. The
        default is ``10,000`` milliseconds.  The TLS handshake timeout will be
        set to the default if the specified ``timeoutMs`` is not positive.
        """
        internals.blpapi_TlsOptions_setTlsHandshakeTimeoutMs(self.__handle,
                                                             timeoutMs)
    def setCrlFetchTimeoutMs(self, timeoutMs):
        """
        Args:
            timeoutMs (int): Timeout threshold in milliseconds

        Set the CRL fetch timeout to the specified ``timeoutMs``. The default
        is ``20,000`` milliseconds.  The TLS handshake timeout will be set to
        the default if the specified ``timeoutMs`` is not positive.
        """
        internals.blpapi_TlsOptions_setCrlFetchTimeoutMs(
            self.__handle, timeoutMs)

    @staticmethod
    def createFromFiles(clientCredentialsFilename,
                        clientCredentialsPassword,
                        trustedCertificatesFilename):
        """
        Args:
            clientCredentialsFilename (str): Path to the file with the client
                credentials
            clientCredentialsPassword (str): Password for the credentials
            trustedCertificatesFilename (str): Path to the file with the
                trusted certificates

        Creates a :class:`TlsOptions` using a DER encoded client credentials in
        PKCS#12 format and DER encoded trust material in PKCS#7 format from the
        specified files.
        """
        handle = internals.blpapi_TlsOptions_createFromFiles(
            clientCredentialsFilename,
            clientCredentialsPassword,
            trustedCertificatesFilename)
        return TlsOptions(handle)

    @staticmethod
    def createFromBlobs(clientCredentials,
                        clientCredentialsPassword,
                        trustedCertificates):
        """
        Args:
            clientCredentials (bytes or bytearray): Blob with the client
                credentials
            clientCredentialsPassword (str): Password for the credentials
            trustedCertificates (bytes or bytearray): Blob with the trusted
                certificates

        Creates a :class:`TlsOptions` using a DER encoded client credentials in
        PKCS#12 format and DER encoded trust material in PKCS#7 format from the
        given raw data.
        """
        credentials = bytearray(clientCredentials)
        certs = bytearray(trustedCertificates)
        handle = internals.blpapi_TlsOptions_createFromBlobs(
            credentials,
            clientCredentialsPassword,
            certs)
        return TlsOptions(handle)

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
