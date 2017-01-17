# providersession.py

"""Provide a session that can be used for providing services.

ProviderSession inherits from AbstractSession. In addition to AbstractSession
functionality, ProviderSession provides functions that are needed to support
publishing like 'registerService', 'createTopics' and 'publish'.
"""


from __future__ import absolute_import

import weakref
import sys
import traceback
import os
import functools
from .abstractsession import AbstractSession
from .event import Event
from . import exception
from .exception import _ExceptionUtil
from . import internals
from .internals import CorrelationId
from .sessionoptions import SessionOptions
from .topic import Topic
from . import utils


class ServiceRegistrationOptions(object):
    """Contains the options which can be specified when registering a service.

    To use non-default options to registerService, create a
    ServiceRegistrationOptions instance and set the required options and then
    supply it when using the registerService interface.
    """

    PRIORITY_LOW = internals.SERVICEREGISTRATIONOPTIONS_PRIORITY_LOW
    PRIORITY_MEDIUM = \
        internals.SERVICEREGISTRATIONOPTIONS_PRIORITY_MEDIUM
    PRIORITY_HIGH = internals.SERVICEREGISTRATIONOPTIONS_PRIORITY_HIGH

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums

    def __init__(self):
        """Create ServiceRegistrationOptions with default options."""
        self.__handle = internals.blpapi_ServiceRegistrationOptions_create()

    def __del__(self):
        """Destroy this ServiceRegistrationOptions."""
        internals.blpapi_ServiceRegistrationOptions_destroy(self.__handle)

    def setGroupId(self, groupId):
        """Set the Group ID for the service to be registered.

        Set the Group ID for the service to be registered to the specified
        'groupId' string. If 'groupId' length is greater than
        MAX_GROUP_ID_SIZE (=64) only the first MAX_GROUP_ID_SIZE chars are
        considered as Group Id.
        """
        internals.blpapi_ServiceRegistrationOptions_setGroupId(
            self.__handle, groupId)

    def setServicePriority(self, priority):
        """Set the priority with which a service will be registered.

        Set the priority with which a service will be registered to the
        non-negative value specified in priority.  This call returns with a
        non-zero value indicating error when a negative priority is specified.
        Any non-negative priority value, other than the one pre-defined in
        ServiceRegistrationPriority can be used.  Default value is
        PRIORITY_HIGH.
        """
        return internals.blpapi_ServiceRegistrationOptions_setServicePriority(
            self.__handle,
            priority)

    def getGroupId(self):
        """Return the value of the service Group Id in this instance."""
        errorCode, groupId = \
            internals.blpapi_ServiceRegistrationOptions_getGroupId(
                self.__handle)
        return groupId

    def getServicePriority(self):
        """Return the value of the service priority in this instance."""
        priority = \
            internals.blpapi_ServiceRegistrationOptions_getServicePriority(
                self.__handle)
        return priority

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle


class ProviderSession(AbstractSession):
    """This class provides a session that can be used for providing services.

    It inherits from AbstractSession. In addition to the AbstractSession
    functionality a ProviderSession provides the following functions to
    applications.

    Applications can register to provide Services using either
    registerService() or registerServiceAsync(). Before registering to provide
    a Service an application must have established its identity.

    Applications use the ProviderSession to resolve topics using resolve() or
    resolveAsync(), create the resulting Topic objects using createTopic() and
    then publish(). Another way to start publishing is the call createTopics or
    createTopicsAsync with a list of topics. This call internally resolves and
    creates topics for user.
    Events containing Messages addressed to specific topics.
    """

    AUTO_REGISTER_SERVICES = \
        internals.RESOLVEMODE_AUTO_REGISTER_SERVICES

    DONT_REGISTER_SERVICES = \
        internals.RESOLVEMODE_DONT_REGISTER_SERVICES

    __handle = None
    __handlerProxy = None

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums

    @staticmethod
    def __dispatchEvent(sessionRef, eventHandle):
        try:
            session = sessionRef()
            if session is not None:
                event = Event(eventHandle, session)
                session.__handler(event, session)
        except:
            print >> sys.stderr, "Exception in event handler:"
            traceback.print_exc(file=sys.stderr)
            os._exit(1)

    def __init__(self, options=None, eventHandler=None, eventDispatcher=None):
        """Constructor.

        Construct a Session using the optionally specified 'options', the
        optionally specified 'eventHandler' and the optionally specified
        'eventDispatcher'.

        See the SessionOptions documentation for details on what can be
        specified in the 'options'.

        If 'eventHandler' is not None then this Session will operate in
        asynchronous mode, otherwise the Session will operate in synchronous
        mode.

        If supplied, 'eventHandler' is a callable object that takes two
        arguments: received event and related session.

        If 'eventDispatcher' is None then the Session will create a default
        EventDispatcher for this Session which will use a single thread for
        dispatching events. For more control over event dispatching a specific
        instance of EventDispatcher can be supplied. This can be used to share
        a single EventDispatcher amongst multiple Session objects.

        If an 'eventDispatcher' is supplied which uses more than one thread the
        Session will ensure that events which should be ordered are passed to
        callbacks in a correct order. For example, partial response to
        a request or updates to a single subscription.

        If 'eventHandler' is None and the 'eventDispatcher' is not None an
        exception is raised.

        Each EventDispatcher uses its own thread or pool of threads so if you
        want to ensure that a session which receives very large messages and
        takes a long time to process them does not delay a session that
        receives small messages and processes each one very quickly then give
        each one a separate EventDispatcher.
        """
        AbstractSession.__init__(self)
        if (eventHandler is None) and (eventDispatcher is not None):
            raise exception.InvalidArgumentException(
                "eventDispatcher is specified but eventHandler is None", 0)
        if options is None:
            options = SessionOptions()
        if eventHandler is not None:
            self.__handler = eventHandler
            self.__handlerProxy = functools.partial(
                ProviderSession.__dispatchEvent, weakref.ref(self))
        self.__handle = internals.ProviderSession_createHelper(
            options._handle(),
            self.__handlerProxy,
            None if eventDispatcher is None else eventDispatcher._handle())
        AbstractSession.__init__(
            self,
            internals.blpapi_ProviderSession_getAbstractSession(self.__handle))

    def __del__(self):
        """Destructor."""
        internals.ProviderSession_destroyHelper(
            self.__handle,
            self.__handlerProxy)

    def start(self):
        """Start this session in synchronous mode.

        Attempt to start this Session and blocks until the Session has started
        or failed to start. If the Session is started successfully iTrue is
        returned, otherwise False is returned. Before start() returns a
        SESSION_STATUS Event is generated. If this is an asynchronous Session
        then the SESSION_STATUS may be processed by the registered EventHandler
        before start() has returned. A Session may only be started once.
        """
        return internals.blpapi_ProviderSession_start(self.__handle) == 0

    def startAsync(self):
        """Start this session in asynchronous mode.

        Attempt to begin the process to start this Session and return True if
        successful, otherwise return False. The application must monitor events
        for a SESSION_STATUS Event which will be generated once the Session has
        started or if it fails to start. If this is an asynchronous Session
        then the SESSION_STATUS Event may be processed by the registered
        EventHandler before startAsync() has returned. A Session may only be
        started once.
        """
        return internals.blpapi_ProviderSession_startAsync(self.__handle) == 0

    def stop(self):
        """Stop operation of this session and wait until it stops.

        Stop operation of this session and block until all callbacks to
        EventHandler objects relating to this Session which are currently in
        progress have completed (including the callback to handle
        the SESSION_STATUS Event this call generates). Once this returns no
        further callbacks to EventHandlers will occur. If stop() is called from
        within an EventHandler callback it is silently converted to
        a stopAsync() in order to prevent deadlock. Once a Session has been
        stopped it can only be destroyed.
        """
        return internals.blpapi_ProviderSession_stop(self.__handle) == 0

    def stopAsync(self):
        """Begin the process to stop this Session and return immediately.

        The application must monitor events for a
        SESSION_STATUS Event which will be generated once the
        Session has been stopped. After this SESSION_STATUS Event
        no further callbacks to EventHandlers will occur(). Once a
        Session has been stopped it can only be destroyed.
        """
        return internals.blpapi_ProviderSession_stop(self.__handle) == 0

    def nextEvent(self, timeout=0):
        """Return the next available Event for this session.

        If there is no event available this will block for up to the specified
        'timeoutMillis' milliseconds for an Event to arrive. A value of 0 for
        'timeoutMillis' (the default) indicates nextEvent() should not timeout
        and will not return until the next Event is available.

        If nextEvent() returns due to a timeout it will return an event of type
        'EventType.TIMEOUT'.

        If this is invoked on a Session which was created in asynchronous mode
        an InvalidStateException is raised.
        """
        retCode, event = internals.blpapi_ProviderSession_nextEvent(
            self.__handle,
            timeout)

        _ExceptionUtil.raiseOnError(retCode)

        return Event(event, self)

    def tryNextEvent(self):
        """Return the next Event for this session if it is available.

        If there are Events available for the session, return the next Event
        If there is no event available for the session, return None. This
        method never blocks.
        """
        retCode, event = internals.blpapi_ProviderSession_tryNextEvent(
            self.__handle)
        if retCode:
            return None
        else:
            return Event(event, self)

    def registerService(self, uri, identity=None, options=None):
        """Attempt to register the service and block until it is done.

        Attempt to register the service identified by the specified 'uri' and
        block until the service is either registered successfully or has failed
        to be registered. The optionally specified 'identity' is used to verify
        permissions to provide the service being registered. The optionally
        specified 'options' is used to specify the group ID and service
        priority of the service being registered.  Return 'True' if the service
        is registered successfully and 'False' if the service cannot be
        registered successfully.

        The 'uri' must begin with a full qualified service name. That is it
        must begin with "//<namespace>/<service-name>[/]". Any portion of the
        'uri' after the service name is ignored.

        Before registerService() returns a SERVICE_STATUS Event is generated.
        If this is an asynchronous ProviderSession then this Event may be
        processed by the registered Event before registerService() has
        returned.
        """
        if identity is None:
            identity = Identity()
        if options is None:
            options = ServiceRegistrationOptions()
        if internals.blpapi_ProviderSession_registerService(
                self.__handle, uri,
                identity._handle(), options._handle()) == 0:
            return True
        return False

    def registerServiceAsync(self, uri, identity=None, correlationId=None,
                             options=None):
        """Begin the process of registering the service immediately.

        Begin the process of registering the service identified by the
        specified 'uri' and return immediately. The optionally specified
        'identity' is used to verify permissions to provide the service being
        registered. The optionally specified 'correlationId' is used to track
        Events generated as a result of this call. The actual correlationId
        that will identify Events generated as a result of this call is
        returned. The optionally specified 'options' is used to specify the
        group ID and service priority of the service being registered.

        The 'uri' must begin with a full qualified service name. That is it
        must begin with "//<namespace>/<service-name>[/]". Any portion of the
        'uri' after the service name is ignored.

        The application must monitor events for a SERVICE_STATUS Event which
        will be generated once the service has been successfully registered or
        registration has failed.
        """
        if identity is None:
            identity = Identity()
        if correlationId is None:
            correlationId = CorrelationId()
        if options is None:
            options = ServiceRegistrationOptions()

        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_registerServiceAsync(
                self.__handle,
                uri,
                identity._handle(),
                correlationId._handle(),
                options._handle()
            ))

        return correlationId

    def resolve(self, resolutionList, resolveMode=DONT_REGISTER_SERVICES,
                identity=None):
        """Resolve the topics in the specified 'resolutionList'.

        Resolve the topics in the specified 'resolutionList', which must be an
        object of type 'ResolutionList', and update the 'resolutionList' with
        the results of the resolution process. If the specified 'resolveMode'
        is DONT_REGISTER_SERVICES (the default) then all the services
        referenced in the topics in the 'resolutionList' must already have been
        registered using registerService(). If 'resolveMode' is
        AUTO_REGISTER_SERVICES then the specified 'identity' should be supplied
        and ProviderSession will automatically attempt to register any services
        reference in the topics in the 'resolutionList' that have not already
        been registered. Once resolve() returns each entry in the
        'resolutionList' will have been updated with a new status.

        Before resolve() returns one or more RESOLUTION_STATUS events and, if
        'resolveMode' is AUTO_REGISTER_SERVICES, zero or more SERVICE_STATUS
        events are generated. If this is an asynchronous ProviderSession then
        these Events may be processed by the registered EventHandler before
        resolve() has returned.
        """
        resolutionList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_resolve(
                self.__handle,
                resolutionList._handle(),
                resolveMode,
                None if identity is None else identity._handle()))

    def resolveAsync(self, resolutionList, resolveMode=DONT_REGISTER_SERVICES,
                     identity=None):
        """Begin the resolution of the topics in the specified list.

        Begin the resolution of the topics in the specified 'resolutionList',
        which must be an object of type 'ResolutionList'. If the specified
        'resolveMode' is DONT_REGISTER_SERVICES (the default) then all the
        services referenced in the topics in the 'resolutionList' must already
        have been registered using registerService(). If 'resolveMode' is
        AUTO_REGISTER_SERVICES then the specified 'identity' should be supplied
        and ProviderSession will automatically attempt to register any services
        reference in the topics in the 'resolutionList' that have not already
        been registered.

        One or more RESOLUTION_STATUS events will be delivered with the results
        of the resolution. These events may be generated before or after
        resolveAsync() returns. If AUTO_REGISTER_SERVICES is specified
        SERVICE_STATUS events may also be generated before or after
        resolveAsync() returns.
        """
        resolutionList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_resolveAsync(
                self.__handle,
                resolutionList._handle(),
                resolveMode,
                None if identity is None else identity._handle()))

    def getTopic(self, message):
        """Find a previously created Topic object based on the 'message'.

        Find a previously created Topic object based on the specified
        'message'. The 'message' must be one of the following
        types: TopicCreated, TopicActivated, TopicDeactivated,
        TopicSubscribed, TopicUnsubscribed, TopicRecap.
        If the 'message' is not valid then invoking isValid() on the
        returned Topic will return False.
        """
        errorCode, topic = internals.blpapi_ProviderSession_getTopic(
            self.__handle,
            message._handle())
        _ExceptionUtil.raiseOnError(errorCode)
        return Topic(topic)

    def createServiceStatusTopic(self, service):
        """Create a Service Status Topic.

        Create a Service Status Topic which is to be used to provide
        service status. On success invoking isValid() on the returned Topic
        will return False.
        """
        errorCode, topic = \
            internals.blpapi_ProviderSession_createServiceStatusTopic(
                self.__handle,
                service._handle()
            )
        _ExceptionUtil.raiseOnError(errorCode)
        return Topic(topic)

    def publish(self, event):
        """Publish the specified 'event'."""
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_publish(
                self.__handle,
                event._handle()))

    def sendResponse(self, event, isPartialResponse=False):
        """Send the response event for previously received request."""
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_sendResponse(
                self.__handle,
                event._handle(),
                isPartialResponse))

    def createTopics(self, topicList,
                     resolveMode=DONT_REGISTER_SERVICES,
                     identity=None):
        """Create the topics in the specified 'topicList'.

        Create the topics in the specified 'topicList', which must be an object
        of type 'TopicList', and update 'topicList' with the results of the
        creation process. If service needs to be registered, 'identity' should
        be supplied.  Once a call to this function returns, each entry in the
        'topicList' will have been updated with a new topic creation status.

        Before createTopics() returns one or more RESOLUTION_STATUS events,
        zero or more SERVICE_STATUS events and one or more TOPIC_STATUS events
        are generated.  If this is an asynchronous ProviderSession then these
        Events may be processed by the registered EventHandler before
        createTopics() has returned.
        """
        topicList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_createTopics(
                self.__handle,
                topicList._handle(),
                resolveMode,
                None if identity is None else identity._handle()))

    def createTopicsAsync(self, topicList,
                          resolveMode=DONT_REGISTER_SERVICES,
                          identity=None):
        """Create the topics in the specified 'topicList'.

        Create the topics in the specified 'topicList', which must be an object
        of type 'TopicList', and update the 'topicList' with the results of the
        creation process. If service needs to be registered, 'providerIdentity'
        should be supplied.

        One or more RESOLUTION_STATUS events, zero or more SERVICE_STATUS
        events and one or more TOPIC_STATUS events are generated.  If this is
        an asynchronous ProviderSession then these Events may be processed by
        the registered EventHandler before createTopics() has returned.
        """
        topicList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_createTopicsAsync(
                self.__handle,
                topicList._handle(),
                resolveMode,
                None if identity is None else identity._handle()))

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
