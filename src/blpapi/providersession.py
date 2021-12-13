# providersession.py

"""Provide a session that can be used for providing services.

ProviderSession inherits from AbstractSession. In addition to AbstractSession
functionality, ProviderSession provides functions that are needed to support
publishing like 'registerService', 'createTopics' and 'publish'.

Topic Life Cycle
----------------
A provider wishing to publish subscription data must explicitly open each topic
on which they publish using 'ProviderSession.createTopics' (or
'ProviderSession.createTopicsAsync'). Creating a topic prepares the
distribution and caching infrastructure for new data associated with the
topic's resolved identifier. (Note that several different topics could resolve
to the same ID.) Independent of a topic's creation status is its subscription
status, i.e. whether there are subscribers ready to receive the data published.
A topic that is both created and subscribed is *activated*.

There are two models for managing topic creation: broadcast and interactive.
Broadcast publishers proactively call 'ProviderSession.createTopic*' for each
topic on which they intend to publish, while interactive publishers wait to
receive a 'TopicSubscribed' message (within an 'Event' of type
'Event.TOPIC_STATUS') before calling 'ProviderSession.createTopic*' in
response. Topics are resolved before they are created---it is possible that
multiple different topic strings will map to the same underlying topic. See
below for the behavior of the SDK when the same topic is created multiple
times.

After 'ProviderSession.createTopic*' is called, the publisher will receive a
'TopicCreated' message (within an 'Event.TOPIC_STATUS' event), and when there
is at least one subscriber to the topic the publisher will then receive a
'TopicActivated' message (also within an 'Event.TOPIC_STATUS' event). As
subscribers come and go, additional 'TopicSubscribed', 'TopicActivated',
'TopicUnsubscribed', and 'TopicDeactivated' messages may be received by the
publisher. A 'Topic' object can be retrieved from each of these messages using
the 'ProviderSession.getTopic' method, and this object can be used for
subsequent calls to 'EventFormatter.appendMessage' and
'ProviderSession.deleteTopic'. In the case that the same resolved topic is
created multiple times by a publisher using different names, it is unspecified
which of those names will be returned by 'Message.topicName' for these (or
other) messages.

If a publisher no longer intends to publish data on a topic, it can call
'ProviderSession.deleteTopic*' to free the internal caching and distribution
resources associated with the topic. When a resolved topic has been deleted the
same number of times that it has been created, a 'TopicDeleted' message will be
delivered, preceded by 'TopicUnsubscribed' and 'TopicDeactivated' messages if
the topic was still subscribed (and activated). No further messages can be
published on a deleted topic.

Deregistering a service deletes all topics associated with that service.

Note that 'TopicActivated' and 'TopicDeactivated' messages are entirely
redundant with 'TopicCreated', 'TopicSubscribed', 'TopicDeleted', and
'TopicUnsubscribed' messages, and are provided only for the convenience of
publishers that do not maintain per-topic state.
"""

from __future__ import print_function
from __future__ import absolute_import
import weakref
import sys
import traceback
import os
import functools
import atexit
from .abstractsession import AbstractSession
from .event import Event
from . import exception
from .exception import _ExceptionUtil
from . import internals
from .internals import CorrelationId
from .sessionoptions import SessionOptions
from .topic import Topic
from . import utils
from .utils import get_handle
from .compat import with_metaclass
from .chandle import CHandle

# pylint: disable=line-too-long,too-many-lines
# pylint: disable=protected-access,too-many-public-methods,bare-except,too-many-function-args

@with_metaclass(utils.MetaClassForClassesWithEnums)
class ServiceRegistrationOptions(CHandle):
    """Contains the options which can be specified when registering a service.

    To use non-default options to :meth:`~ProviderSession.registerService()`,
    create a :class:`ServiceRegistrationOptions` instance and set the required
    options and then supply it when using the
    :meth:`~ProviderSession.registerService()` interface.

    The following attributes represent service registration priorities:

    - :attr:`PRIORITY_LOW`
    - :attr:`PRIORITY_MEDIUM`
    - :attr:`PRIORITY_HIGH`

    The following attributes represent the registration parts:

    - :attr:`PART_PUBLISHING`
    - :attr:`PART_OPERATIONS`
    - :attr:`PART_SUBSCRIBER_RESOLUTION`
    - :attr:`PART_PUBLISHER_RESOLUTION`
    - :attr:`PART_DEFAULT`
    """

    PRIORITY_LOW = internals.SERVICEREGISTRATIONOPTIONS_PRIORITY_LOW
    PRIORITY_MEDIUM = \
        internals.SERVICEREGISTRATIONOPTIONS_PRIORITY_MEDIUM
    PRIORITY_HIGH = internals.SERVICEREGISTRATIONOPTIONS_PRIORITY_HIGH

    # Constants for specifying which part(s) of a service should be registered:

    PART_PUBLISHING = internals.REGISTRATIONPARTS_PUBLISHING
    """Register to receive subscribe and unsubscribe messages"""

    PART_OPERATIONS = internals.REGISTRATIONPARTS_OPERATIONS
    """Register to receive the request types corresponding to each "operation"
    defined in the service metadata"""

    PART_SUBSCRIBER_RESOLUTION \
        = internals.REGISTRATIONPARTS_SUBSCRIBER_RESOLUTION
    """Register to receive resolution requests (with message type
    ``PermissionRequest``) from subscribers"""

    PART_PUBLISHER_RESOLUTION \
        = internals.REGISTRATIONPARTS_PUBLISHER_RESOLUTION
    """Register to receive resolution requests (with message type
    ``PermissionRequest``) from publishers (via
    :meth:`ProviderSession.createTopics()`)"""

    PART_DEFAULT = internals.REGISTRATIONPARTS_DEFAULT
    """Register the parts of the service implied by options specified in the
    service metadata"""

    def __init__(self):
        """Create :class:`ServiceRegistrationOptions` with default options."""
        selfhandle = internals.blpapi_ServiceRegistrationOptions_create()
        super(ServiceRegistrationOptions, self).__init__(
            selfhandle,
            internals.blpapi_ServiceRegistrationOptions_destroy)
        self.__handle = selfhandle

    def setGroupId(self, groupId):
        """Set the Group ID for the service to be registered.

        Args:
            groupId (str): The group ID for the service to be registered

        Set the Group ID for the service to be registered to the specified
        ``groupId`` string. If ``groupId`` length is greater than
        ``MAX_GROUP_ID_SIZE`` (=64) only the first ``MAX_GROUP_ID_SIZE`` chars
        are considered as Group Id.
        """
        internals.blpapi_ServiceRegistrationOptions_setGroupId(
            self.__handle, groupId)

    def setServicePriority(self, priority):
        """Set the priority with which a subscription service will be
        registered.

        Args:
            priority (int): The service priority

        Set the priority with which a subscription service will be registered
        to the specified ``priority``, where numerically greater values of
        ``priority`` indicate higher priorities. The behavior is undefined
        unless ``priority`` is non-negative. Note that while the values
        pre-defined in ``ServiceRegistrationOptions`` are suitable for use
        here, any non-negative ``priority`` is acceptable.

        By default, a service will be registered with priority
        :attr:`PRIORITY_HIGH`.

        Note this has no effect for resolution services.
        """
        return internals.blpapi_ServiceRegistrationOptions_setServicePriority(
            self.__handle,
            priority)

    def getGroupId(self):
        """
        Returns:
            str: The value of the service Group Id in this instance.
        """
        _, groupId = \
            internals.blpapi_ServiceRegistrationOptions_getGroupId(
                self.__handle)
        return groupId

    def getServicePriority(self):
        """
        Returns:
            int: The value of the priority for subscription services in this
                 instance.
        """
        priority = \
            internals.blpapi_ServiceRegistrationOptions_getServicePriority(
                self.__handle)
        return priority

    def addActiveSubServiceCodeRange(self, begin, end, priority):
        """
        Args:
            begin (int): Start of sub-service code range
            end (int): End of sub-service code range
            priority (int): Priority with which to receive subscriptions

        Advertise the service to be registered to receive, with the
        specified ``priority``, subscriptions that the resolver has mapped to a
        service code between the specified ``begin`` and the specified ``end``
        values, inclusive. Numerically greater values of ``priority`` indicate
        higher priorities.

        Note:
            The behavior of this function is undefined unless ``0 <= begin <=
            end < (1 << 24)``, and ``priority`` is non-negative.
        """
        err = internals.blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange(
                self.__handle, begin, end, priority)
        _ExceptionUtil.raiseOnError(err)

    def removeAllActiveSubServiceCodeRanges(self):
        """Remove all previously added sub-service code ranges."""
        internals.blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges(
                self.__handle)

    def setPartsToRegister(self, parts):
        """Set the parts of the service to be registered.

        Args:
            int: Parts of the service to be registered.

        Set the parts of the service to be registered to the specified
        ``parts``, which must be a bitwise-or of the options provided in
        "registration parts" options (enumerated in the class docstring). This
        option defaults to :attr:`PART_DEFAULT`.
        """
        internals.blpapi_ServiceRegistrationOptions_setPartsToRegister(
                self.__handle, parts)

    def getPartsToRegister(self):
        """
        Returns:
            int: The parts of the service to be registered.

        Registration parts are enumerated in the class docstring.
        """
        return internals.blpapi_ServiceRegistrationOptions_getPartsToRegister(
                self.__handle)


@with_metaclass(utils.MetaClassForClassesWithEnums)
class ProviderSession(AbstractSession):
    """This class provides a session that can be used for providing services.

    It inherits from :class:`AbstractSession`. In addition to the
    :class:`AbstractSession` functionality a :class:`ProviderSession` provides
    the following functions to applications.

    A provider can register to provide services using
    :meth:`registerService()`. Before registering to provide a
    service the provider must have established its identity. Then the provider
    can create topics and publish events on topics. It also can get requests
    from the event queue and send back responses.

    After users have registered a service they will start receiving
    subscription requests (``TopicSubscribed`` message in
    :attr:`~Event.TOPIC_STATUS`) for topics which belong to the service. If the
    resolver has specified ``subServiceCode`` for topics in
    ``PermissionResponse``, then only providers who have activated the
    ``subServiceCode`` will get the subscription request.  Where multiple
    providers have registered the same service and sub-service code (if any),
    the provider that registered the highest priority for the sub-service code
    will receive subscription requests; if multiple providers have registered
    the same sub-service code with the same priority (or the resolver did not
    set a sub-service code for the subscription), the subscription request will
    be routed to one of the providers with the highest service priority.
    """

    AUTO_REGISTER_SERVICES = \
        internals.RESOLVEMODE_AUTO_REGISTER_SERVICES

    DONT_REGISTER_SERVICES = \
        internals.RESOLVEMODE_DONT_REGISTER_SERVICES

    __handle = None  # pylint: disable=unused-private-member
    __handlerProxy = None  # pylint: disable=unused-private-member

    @staticmethod
    def __dispatchEvent(sessionRef, eventHandle): # pragma: no cover
        """Use sessions ref to dispatch an event"""
        try:
            session = sessionRef()
            if session is not None:
                event = Event(eventHandle, session)
                session.__handler(event, session)
        except:
            print("Exception in event handler:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            os._exit(1)

    def __init__(self, options=None, eventHandler=None, eventDispatcher=None):
        """Constructor.

        Args:
            options (SessionOptions): Options used to construct the sessions
            eventHandler (~collections.abc.Callable): Handler for the events
                generated by this session
            eventDispatcher (EventDispatcher): Dispatcher for the events
                generated by this session

        Raises:
            InvalidArgumentException: If ``eventHandler`` is ``None`` and the
                ``eventDispatcher`` is not ``None``

        Construct a Session using the optionally specified 'options', the
        optionally specified 'eventHandler' and the optionally specified
        'eventDispatcher'.

        See :class:`SessionOptions` for details on what can be specified in
        the ``options``.

        If ``eventHandler`` is not ``None`` then this Session will operate in
        asynchronous mode, otherwise the Session will operate in synchronous
        mode.

        If supplied, ``eventHandler`` is a callable object that takes two
        arguments: received event and related session.

        If ``eventDispatcher`` is ``None`` then the Session will create a
        default :class:`EventDispatcher` for this Session which will use a
        single thread for dispatching events. For more control over event
        dispatching a specific instance of :class:`EventDispatcher` can be
        supplied. This can be used to share a single :class:`EventDispatcher`
        amongst multiple Session objects.

        If an ``eventDispatcher`` is supplied which uses more than one thread
        the Session will ensure that events which should be ordered are passed
        to callbacks in a correct order. For example, partial response to a
        request or updates to a single subscription.

        Each :class:`EventDispatcher` uses its own thread or pool of threads so
        if you want to ensure that a session which receives very large messages
        and takes a long time to process them does not delay a session that
        receives small messages and processes each one very quickly then give
        each one a separate :class:`EventDispatcher`.
        """
        AbstractSession.__init__(self)
        if (eventHandler is None) and (eventDispatcher is not None):
            raise exception.InvalidArgumentException(
                "eventDispatcher is specified but eventHandler is None", 0)
        if options is None:
            options = SessionOptions()
        if eventHandler is not None:
            self.__handler = eventHandler # pylint: disable=unused-private-member
            self.__handlerProxy = functools.partial(
                ProviderSession.__dispatchEvent, weakref.ref(self))
        self.__handle = internals.ProviderSession_createHelper(
            get_handle(options),
            self.__handlerProxy,
            get_handle(eventDispatcher))

        _destroy = internals.ProviderSession_destroyHelper
        # note: AbstractSession destroy passes AbstractSession handle
        _dtor = lambda hndl: _destroy(self.__handle, self.__handlerProxy)

        atexit.register(self.stop) # we must stop session before shutdown
        AbstractSession.__init__(
            self,
            internals.blpapi_ProviderSession_getAbstractSession(self.__handle),
            _dtor)

    def start(self):
        """Start this :class:`Session` in synchronous mode.

        Returns:
            bool: ``True`` if the :class:`Session` started successfully,
            ``False`` otherwise.

        Attempt to start this :class:`Session` and block until the
        :class:`Session` has started or failed to start.  Before
        :meth:`start()` returns a :attr:`~Event.SESSION_STATUS` :class:`Event`
        is generated. A :class:`Session` may only be started once.
        """
        return internals.blpapi_ProviderSession_start(self.__handle) == 0

    def startAsync(self):
        """Start this :class:`Session` in asynchronous mode.

        Returns:
            bool: ``True`` if the process to start a :class:`Session` began
            successfully, ``False`` otherwise.

        Attempt to begin the process to start this :class:`Session`. The
        application must monitor events for a :attr:`~Event.SESSION_STATUS`
        :class:`Event` which will be generated once the :class:`Session` has
        started or if it fails to start. The :attr:`~Event.SESSION_STATUS`
        :class:`Event` may be processed by the registered ``eventHandler``
        before :meth:`startAsync()` has returned. A :class:`Session` may only
        be started once.
        """
        return internals.blpapi_ProviderSession_startAsync(self.__handle) == 0

    def flushPublishedEvents(self, timeoutMsecs):
        """Wait at most ``timeoutMsecs`` milliseconds for all the published
        events to be sent through the underlying channel.

        Args:
            timeoutMsecs (int): Timeout threshold in milliseconds

        Returns:
            bool: ``True`` if all the published events have been sent,
            ``False`` otherwise

        The method returns either as soon as all the published events have been
        sent out or when it has waited ``timeoutMsecs`` milliseconds. The behavior
        is undefined unless the specified ``timeoutMsecs`` is a non-negative
        value. When ``timeoutMsecs`` is ``0``, the method checks if all the published
        events have been sent and returns without waiting.
        """

        err_code, allFlushed = internals.blpapi_ProviderSession_flushPublishedEvents(self.__handle, timeoutMsecs)
        if err_code != 0:
            raise RuntimeError("Flush published events failed")

        return allFlushed != 0

    def stop(self):
        """Stop operation of this :class:`Session` and wait until it stops.

        Returns:
            bool: ``True`` if the :class:`Session` stopped successfully,
            ``False`` otherwise.

        Stop operation of this :class:`Session` and block until all callbacks
        to ``eventHandler`` objects relating to this :class:`Session` which are
        currently in progress have completed (including the callback to handle
        the :class:`~Event.SESSION_STATUS` :class:`Event` this call generates).
        Once this returns no further callbacks to ``eventHandlers`` will occur.
        If :meth:`stop()` is called from within an ``eventHandler`` callback it
        is silently converted to a :meth:`stopAsync()` in order to prevent
        deadlock. Once a :class:`Session` has been stopped it can only be
        destroyed.
        """
        if sys.version_info >= (3, 6):
            atexit.unregister(self.stop)
        return internals.blpapi_ProviderSession_stop(self.__handle) == 0

    def stopAsync(self):
        """Begin the process to stop this Session and return immediately.

        Returns:
            bool: ``True`` if the process to stop a :class:`Session` began
            successfully, ``False`` otherwise.

        The application must monitor events for a :attr:`~Event.SESSION_STATUS`
        :class:`Event` which will be generated once the :class:`Session` has
        been stopped. After this :attr:`~Event.SESSION_STATUS` :class:`Event`
        no further callbacks to ``eventHandlers`` will occur. Once a
        :class:`Session` has been stopped it can only be destroyed.
        """
        return internals.blpapi_ProviderSession_stopAsync(self.__handle) == 0

    def nextEvent(self, timeout=0):
        """
        Args:
            timeout (int): Timeout threshold in milliseconds

        Returns:
            Event: Next available event for this session

        Raises:
            InvalidStateException: If invoked on a session created in
                asynchronous mode

        If there is no :class:`Event` available this will block for up to the
        specified ``timeout`` milliseconds for an :class:`Event` to arrive. A
        value of ``0`` for ``timeout`` (the default) indicates
        :meth:`nextEvent()` should not timeout and will not return until the
        next :class:`Event` is available.

        If :meth:`nextEvent()` returns due to a timeout it will return an event
        of type :attr:`~Event.TIMEOUT`.
        """
        retCode, event = internals.blpapi_ProviderSession_nextEvent(
            self.__handle,
            timeout)

        _ExceptionUtil.raiseOnError(retCode)

        return Event(event, self)

    def tryNextEvent(self):
        """
        Returns:
            Event: Next available event for this session

        If there are :class:`Event`\ s available for the session, return the
        next :class:`Event` If there is no event available for the
        :class:`Session`, return ``None``. This method never blocks.
        """
        retCode, event = internals.blpapi_ProviderSession_tryNextEvent(
            self.__handle)
        if retCode:
            return None
        return Event(event, self)

    def registerService(self, uri, identity=None, options=None):
        """Attempt to register the service and block until it is done.

        Args:
            uri (str): Name of the service
            identity (Identity): Identity used to verify permissions to provide
                the service being registered
            options (ServiceRegistrationOptions): Options used to register the
                service

        Returns:
            bool: ``True`` if the service registered successfully, ``False``
            otherwise

        Attempt to register the service identified by the specified ``uri`` and
        block until the service is either registered successfully or has failed
        to be registered. The optionally specified ``identity`` is used to verify
        permissions to provide the service being registered. The optionally
        specified ``options`` is used to specify the group ID and service
        priority of the service being registered.

        The ``uri`` must begin with a full qualified service name. That is it
        must begin with ``//<namespace>/<service-name>[/]``. Any portion of the
        ``uri`` after the service name is ignored.

        Before :meth:`registerService()` returns a
        :attr:`~Event.SERVICE_STATUS` :class:`Event` is generated.  If this is
        an asynchronous :class:`ProviderSession` then this :class:`Event` may
        be processed by the registered :class:`Event` before
        :meth:`registerService()` has returned.

        When ``identity`` is not provided, the session identity will be used if
        it has been authorized.
        """
        if options is None:
            options = ServiceRegistrationOptions()
        if internals.blpapi_ProviderSession_registerService(
                self.__handle, uri,
                get_handle(identity),
                get_handle(options)) == 0:
            return True
        return False

    def registerServiceAsync(self, uri, identity=None, correlationId=None,
                             options=None):
        """Begin the process of registering the service immediately.

        Args:
            uri (str): Name of the service
            identity (Identity): Identity used to verify permissions to provide
                the service being registered
            correlationId (CorrelationId): Correlation id to associate with
                this operation
            options (ServiceRegistrationOptions): Options used to register the
                service

        Returns:
            CorrelationId: Correlation id associated with events generated by
            this operation

        Begin the process of registering the service identified by the
        specified ``uri`` and return immediately. The optionally specified
        ``identity`` is used to verify permissions to provide the service being
        registered. The optionally specified ``correlationId`` is used to track
        :class:`Event`\ s generated as a result of this call. The actual ``correlationId``
        that will identify :class:`Event`\ s generated as a result of this call is
        returned. The optionally specified ``options`` is used to specify the
        group ID and service priority of the service being registered.

        The ``uri`` must begin with a full qualified service name. That is it
        must begin with ``//<namespace>/<service-name>[/]``. Any portion of the
        ``uri`` after the service name is ignored.

        The application must monitor events for a
        :class:`~Event.SERVICE_STATUS` :class:`Event` which will be generated
        once the service has been successfully registered or registration has
        failed.

        When ``identity`` is not provided, the session identity will be used if
        it has been authorized.
        """
        if correlationId is None:
            correlationId = CorrelationId()
        if options is None:
            options = ServiceRegistrationOptions()

        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_registerServiceAsync(
                self.__handle,
                uri,
                get_handle(identity),
                get_handle(correlationId),
                get_handle(options)
            ))

        return correlationId

    def resolve(self, resolutionList, resolveMode=DONT_REGISTER_SERVICES,
                identity=None):
        """Resolve the topics in the specified ``resolutionList``.

        Args:
            resolutionList (ResolutionList): List of topics to resolve
            resolveMode (int): Mode to resolve in
            identity (Identity): Identity used for authorization

        Resolve the topics in the specified ``resolutionList``, which must be
        an object of type :class:`ResolutionList`, and update the
        ``resolutionList`` with the results of the resolution process. If the
        specified ``resolveMode`` is :attr:`DONT_REGISTER_SERVICES` (the
        default) then all the services referenced in the topics in the
        ``resolutionList`` must already have been registered using
        :meth:`registerService()`. If ``resolveMode`` is
        :attr:`AUTO_REGISTER_SERVICES` then the specified ``identity`` should
        be supplied and :class:`ProviderSession` will automatically attempt to
        register any services reference in the topics in the ``resolutionList``
        that have not already been registered. Once :meth:`resolve()` returns
        each entry in the ``resolutionList`` will have been updated with a new
        status.

        Before :meth:`resolve()` returns one or more
        :attr:`~Event.RESOLUTION_STATUS` events and, if ``resolveMode`` is
        :attr:`AUTO_REGISTER_SERVICES`, zero or more
        :attr:`~Event.SERVICE_STATUS` events are generated. If this is an
        asynchronous :class:`ProviderSession` then these :class:`Event`\ s may
        be processed by the registered ``eventHandler`` before
        :meth:`resolve()` has returned.

        When ``identity`` is not provided, the session identity will be used if
        it has been authorized.
        """
        resolutionList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_resolve(
                self.__handle,
                get_handle(resolutionList),
                resolveMode,
                get_handle(identity)))

    def resolveAsync(self, resolutionList, resolveMode=DONT_REGISTER_SERVICES,
                     identity=None):
        """Begin the resolution of the topics in the specified list.

        Args:
            resolutionList (ResolutionList): List of topics to resolve
            resolveMode (int): Mode to resolve in
            identity (Identity): Identity used for authorization

        Begin the resolution of the topics in the specified ``resolutionList``,
        which must be an object of type :class:`ResolutionList`. If the
        specified ``resolveMode`` is :attr:`DONT_REGISTER_SERVICES` (the
        default) then all the services referenced in the topics in the
        ``resolutionList`` must already have been registered using
        :meth:`registerService()`. If ``resolveMode`` is
        :attr:`AUTO_REGISTER_SERVICES` then the specified ``identity`` should
        be supplied and :class:`ProviderSession` will automatically attempt to
        register any services reference in the topics in the ``resolutionList``
        that have not already been registered.

        One or more :attr:`~Event.RESOLUTION_STATUS` events will be delivered
        with the results of the resolution. These events may be generated
        before or after :meth:`resolveAsync()` returns. If
        :attr:`AUTO_REGISTER_SERVICES` is specified :attr:`~Event.SERVICE_STATUS`
        events may also be generated before or after :meth:`resolveAsync()`
        returns.

        When ``identity`` is not provided, the session identity will be used if
        it has been authorized.
        """
        resolutionList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_resolveAsync(
                self.__handle,
                get_handle(resolutionList),
                resolveMode,
                get_handle(identity)))

    def getTopic(self, message):
        """Find a previously created :class:`Topic` based on the ``message``.

        Args:
            message (Message): Message to get the topic from

        Returns:
            Topic: The topic the message was published on

        The ``message`` must be one of the following types: ``TopicCreated``,
        ``TopicActivated``, ``TopicDeactivated``, ``TopicSubscribed``,
        ``TopicUnsubscribed``, ``TopicRecap``.  If the ``message`` is not valid
        then invoking :meth:`~Topic.isValid()` on the returned :class:`Topic`
        will return ``False``.
        """
        errorCode, topic = internals.blpapi_ProviderSession_getTopic(
            self.__handle,
            get_handle(message))
        _ExceptionUtil.raiseOnError(errorCode)
        return Topic(topic, sessions=(self,))

    def createServiceStatusTopic(self, service):
        """Create a :class:`Service` Status :class:`Topic` which is to be used
        to provide service status.

        Args:
            service (Service): Service for which to create the topic

        Returns:
            Topic: A service status topic

        On success invoking :meth:`~Topic.isValid()` on the returned
        :class:`Topic` will return ``False``.
        """
        errorCode, topic = \
            internals.blpapi_ProviderSession_createServiceStatusTopic(
                self.__handle,
                get_handle(service))
        _ExceptionUtil.raiseOnError(errorCode)
        return Topic(topic)

    def publish(self, event):
        """Publish the specified ``event``.

        Args:
            event (Event): Event to publish
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_publish(
                self.__handle,
                get_handle(event)))

    def sendResponse(self, event, isPartialResponse=False):
        """Send the response event for previously received request.

        Args:
            event (Event): Response event to send
            isPartialResponse (bool): Whether the response is partial or not
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_sendResponse(
                self.__handle,
                get_handle(event),
                isPartialResponse))

    def createTopics(self, topicList,
                     resolveMode=DONT_REGISTER_SERVICES,
                     identity=None):
        """Create the topics in the specified ``topicList``.

        Args:
            topicList (TopicList): List of topics to create
            resolveMode (int): Mode to use for topic resolution
            identity (Identity): Identity to use for authorization

        Create the topics in the specified ``topicList``, which must be an object
        of type :class:`TopicList`, and update ``topicList`` with the results of the
        creation process. If service needs to be registered, ``identity`` should
        be supplied.  Once a call to this function returns, each entry in the
        ``topicList`` will have been updated with a new topic creation status.

        Before :meth:`createTopics()` returns one or more
        :attr:`~Event.RESOLUTION_STATUS` events, zero or more
        :attr:`~Event.SERVICE_STATUS` events and one or more
        :attr:`~Event.TOPIC_STATUS` events are generated.  If this is an
        asynchronous :class:`ProviderSession` then these :class:`Event`\ s may
        be processed by the registered ``eventHandler`` before
        :meth:`createTopics()` has returned.

        When ``identity`` is not provided, the session identity will be used if
        it has been authorized.
        """
        topicList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_createTopics(
                self.__handle,
                get_handle(topicList),
                resolveMode,
                get_handle(identity)))

    def createTopicsAsync(self, topicList,
                          resolveMode=DONT_REGISTER_SERVICES,
                          identity=None):
        """Create the topics in the specified ``topicList``.

        Args:
            topicList (TopicList): List of topics to create
            resolveMode (int): Mode to use for topic resolution
            identity (Identity): Identity to use for authorization

        Create the topics in the specified ``topicList``, which must be an object
        of type :class:`TopicList`, and update ``topicList`` with the results of the
        creation process. If service needs to be registered, ``identity`` should
        be supplied.  Once a call to this function returns, each entry in the
        ``topicList`` will have been updated with a new topic creation status.

        Before :meth:`createTopics()` returns one or more
        :attr:`~Event.RESOLUTION_STATUS` events, zero or more
        :attr:`~Event.SERVICE_STATUS` events and one or more
        :attr:`~Event.TOPIC_STATUS` events are generated.  If this is an
        asynchronous :class:`ProviderSession` then these :class:`Event`\ s may
        be processed by the registered ``eventHandler`` before
        :meth:`createTopics()` has returned.

        When ``identity`` is not provided, the session identity will be used if
        it has been authorized.
        """
        topicList._addSession(self)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_ProviderSession_createTopicsAsync(
                self.__handle,
                get_handle(topicList),
                resolveMode,
                get_handle(identity)))

    def activateSubServiceCodeRange(self, serviceName, begin, end, priority):
        """
        Args:
            serviceName (str): Name of the service
            begin (int): Start of sub-service code range
            end (int): End of sub-service code range
            priority (int): Priority with which to receive subscriptions

        Register to receive, with the specified ``priority``, subscriptions for
        the specified ``service`` that the resolver has mapped to a service
        code between the specified ``begin`` and the specified ``end`` values,
        inclusive. Numerically greater values of ``priority`` indicate higher
        priorities.

        Note:
            The behavior of this function is undefined unless ``service`` has
            already been successfully registered, ``0 <= begin <= end < (1 <<
            24)``, and ``priority`` is non-negative.
        """
        err = internals.blpapi_ProviderSession_activateSubServiceCodeRange(
                self.__handle, serviceName, begin, end, priority)
        _ExceptionUtil.raiseOnError(err)

    def deactivateSubServiceCodeRange(self, serviceName, begin, end):
        """
        Args:
            serviceName (str): Name of the service
            begin (int): Start of sub-service code range
            end (int): End of sub-service code range

        De-register to receive subscriptions for the specified ``service``
        that the resolver has mapped to a service code between the specified
        ``begin`` and the specified ``end`` values, inclusive.

        Note:
            The behavior of this function is undefined unless ``service`` has
            already been successfully registered and ``0 <= begin <= end < (1 <<
            24)``.
        """
        err = internals.blpapi_ProviderSession_deactivateSubServiceCodeRange(
                self.__handle, serviceName, begin, end)
        _ExceptionUtil.raiseOnError(err)

    def deregisterService(self, serviceName):
        """De-register the service, including all registered parts.

        Args:
            serviceName (str): Service to de-register

        Returns:
            bool: ``False`` if the service is not registered nor in pending
            registration, ``True`` otherwise.

        The identity in the service registration is reused to verify
        permissions for deregistration.  If the service is in pending
        registration, cancel the pending registration. If the service is
        registered, send a deregistration request; generate
        :class:`~Event.TOPIC_STATUS` events containing a ``TopicUnsubscribed``
        message for each subscribed topic, a ``TopicDeactivated`` message for
        each active topic and a ``TopicDeleted`` for each created topic;
        generate ``~Event.REQUEST_STATUS`` events containing a
        ``RequestFailure`` message for each pending incoming request; and
        generate a :class:`~Event.SERVICE_STATUS` event containing a
        ``ServiceDeregistered`` message. All published events on topics created
        on this service will be ignored after this method returns.
        """
        res = internals.blpapi_ProviderSession_deregisterService(
                self.__handle, serviceName)
        return res == 0

    def terminateSubscriptionsOnTopic(self, topic, message=None):
        """Delete the specified ``topic`` (See :meth:`deleteTopic()` for
        additional details).

        Args:
            topic (Topic): Topic to delete
            message (Message): Message to convey additional information to
                subscribers regarding the termination

        Furthermore, proactively terminate all current subscriptions on
        ``topic``.  The optionally specified ``message`` can be used to convey
        additional information to subscribers regarding the termination. This
        message is contained in the ``description`` of ``reason`` in a
        ``SubscriptionTerminated`` message.
        """
        if not topic:
            return
        _ExceptionUtil.raiseOnError(
                internals.ProviderSession_terminateSubscriptionsOnTopic(
                                    self.__handle, get_handle(topic), message))

    def terminateSubscriptionsOnTopics(self, topics, message=None):
        """Terminate subscriptions on the specified ``topics``.

        Args:
            topics ([Topic]): Topics to delete
            message (Message): Message to convey additional information to
                subscribers regarding the termination

        See :meth:`terminateSubscriptionsOnTopic()` for additional details.
        """
        if not topics:
            return
        topicsCArraySize = len(topics)
        topicsCArray = internals.new_topicPtrArray(topicsCArraySize)
        try:
            for i, topic in enumerate(topics):
                internals.topicPtrArray_setitem(topicsCArray,
                                                i,
                                                get_handle(topic))
            _ExceptionUtil.raiseOnError(
                internals.blpapi_ProviderSession_terminateSubscriptionsOnTopics(
                    self.__handle,
                    topicsCArray,
                    topicsCArraySize,
                    message))
        finally:
            internals.delete_topicPtrArray(topicsCArray)

    def deleteTopic(self, topic):
        """Remove one reference from the specified 'topic'.

        Args:
            topic (Topic): Topic to remove the reference from

        If this function has been called the same number of times that
        ``topic`` was created by ``createTopics``, then ``topic`` is deleted: a
        ``TopicDeleted`` message is delivered, preceded by
        ``TopicUnsubscribed`` and ``TopicDeactivated`` if ``topic`` was
        subscribed.

        Note:
            The behavior of this function is undefined if ``topic`` has already
            been deleted the same number of times that it has been created.
            Further, the behavior is undefined if a provider attempts to
            publish a message on a deleted topic.
        """
        self.deleteTopics((topic,))

    def deleteTopics(self, topics):
        """Delete each topic in the specified ``topics`` container.

        Args:
            deleteTopics([Topic]): Topics to delete

        See :meth:`deleteTopic()` above for additional details."""
        if not topics:
            return
        topicsCArraySize = len(topics)
        topicsCArray = internals.new_topicPtrArray(topicsCArraySize)
        try:
            for i, topic in enumerate(topics):
                internals.topicPtrArray_setitem(topicsCArray,
                                                i,
                                                get_handle(topic))
            _ExceptionUtil.raiseOnError(
                internals.blpapi_ProviderSession_deleteTopics(
                    self.__handle,
                    topicsCArray,
                    topicsCArraySize))
        finally:
            internals.delete_topicPtrArray(topicsCArray)

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
