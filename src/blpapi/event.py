# event.py

"""A module which defines events related operations.

This file defines an 'Event'. One or more 'Event's are generated as a result of
a subscription or a request. 'Event's contain 'Message' objects which can be
accessed using a 'MessageIterator'. This file also defines a 'EventQueue' for
handling replies synchronously.

Usage
-----
The following code snippet shows how a 'EventQueue' is used with a
'generateToken' request. For any established session 'session' pass an
'EventQueue' object 'tokenEventQueue' when calling 'generateToken'. All
'Event's in responses to 'generateToken' request will be returned in
'tokenEventQueue'.

    tokenEventQueue = EventQueue()
    session.generateToken(eventQueue=tokenEventQueue)

Synchronously read the response 'event' and parse over messages using 'token'

    ev = tokenEventStatus.nextEvent()
    token = None
    if ev.eventType() == blpapi.Event.TOKEN_STATUS:
        for msg in ev:
           if msg.messageType() == TOKEN_SUCCESS:
               token = msg.getElementAsString(TOKEN)
           elif msg.messageType() == TOKEN_FAILURE:
               break
    if not token:
        raise Exception("Failed to get token")

"""

from .message import Message
from . import internals
from . import utils
from .utils import get_handle
from .compat import with_metaclass
from .chandle import CHandle

class MessageIterator(CHandle):
    """An iterator over the :class:`Message` objects within an :class:`Event`.

    Few clients will ever make direct use of :class:`MessageIterator` objects;
    Python ``for`` loops allow clients to operate directly in terms of
    :class:`Event` and :class:`Message` objects.
    """

    def __init__(self, event):
        selfhandle = internals.blpapi_MessageIterator_create(get_handle(event))
        super(MessageIterator, self).__init__(
            selfhandle,
            internals.blpapi_MessageIterator_destroy)
        self.__handle = selfhandle
        self.__event = event

    def __iter__(self):
        return self

    def __next__(self):
        retCode, message = internals.blpapi_MessageIterator_next(self.__handle)
        if retCode:
            raise StopIteration()
        else:
            return Message(message, self.__event)

    next = __next__


@with_metaclass(utils.MetaClassForClassesWithEnums)
class Event(CHandle):
    """A single event resulting from a subscription or a request.

    :class:`Event` objects are created by the API and passed to the application
    either through a registered ``eventHandler`` or :class:`EventQueue` or
    returned either from the ``nextEvent()`` or ``tryNextEvent()`` methods.
    :class:`Event` objects contain :class:`Message` objects which can be
    accessed using an iteration over :class:`Event`::

        for message in event:
            ...

    The :class:`Event` object is a handle to an event. The event is the basic
    unit of work provided to applications. Each :class:`Event` object consists
    of an ``eventType`` attribute and zero or more :class:`Message` objects.

    :class:`Event` objects are always created by the API, never directly by the
    application.

    The class attributes represent the possible types of event.
    """

    ADMIN = internals.EVENTTYPE_ADMIN
    """Admin event"""
    SESSION_STATUS = internals.EVENTTYPE_SESSION_STATUS
    """Status updates for a session"""
    SUBSCRIPTION_STATUS = internals.EVENTTYPE_SUBSCRIPTION_STATUS
    """Status updates for a subscription"""
    REQUEST_STATUS = internals.EVENTTYPE_REQUEST_STATUS
    """Status updates for a request"""
    RESPONSE = internals.EVENTTYPE_RESPONSE
    """The final (possibly only) response to a request"""
    PARTIAL_RESPONSE = internals.EVENTTYPE_PARTIAL_RESPONSE
    """A partial response to a request"""
    SUBSCRIPTION_DATA = internals.EVENTTYPE_SUBSCRIPTION_DATA
    """Data updates resulting from a subscription"""
    SERVICE_STATUS = internals.EVENTTYPE_SERVICE_STATUS
    """Status updates for a service"""
    TIMEOUT = internals.EVENTTYPE_TIMEOUT
    """An Event returned from nextEvent() if it timed out"""
    AUTHORIZATION_STATUS = internals.EVENTTYPE_AUTHORIZATION_STATUS
    """Status updates for user authorization"""
    RESOLUTION_STATUS = internals.EVENTTYPE_RESOLUTION_STATUS
    """Status updates for a resolution operation"""
    TOPIC_STATUS = internals.EVENTTYPE_TOPIC_STATUS
    """Status updates about topics for service providers"""
    TOKEN_STATUS = internals.EVENTTYPE_TOKEN_STATUS
    """Status updates for a generate token request"""
    REQUEST = internals.EVENTTYPE_REQUEST
    """Request event"""
    UNKNOWN = -1
    """Unknown event"""

    def __init__(self, handle, sessions):
        super(Event, self).__init__(handle, internals.blpapi_Event_release)
        self.__handle = handle
        self.__sessions = sessions

    def eventType(self):
        """
        Returns:
            int: Type of messages contained by this :class:`Event`.
        """
        return internals.blpapi_Event_eventType(self.__handle)

    def __iter__(self):
        """
        Returns:
            Iterator over messages contained in this :class:`Event`.
        """
        return MessageIterator(self)

    def _sessions(self):
        """Return session(s) that this 'Event' is related to.

        For internal use."""
        return self.__sessions

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:


class EventQueue(CHandle):
    """A construct used to handle replies to request synchronously.

    When a request is submitted an application can either handle the responses
    asynchronously as they arrive or use an :class:`EventQueue` to handle all
    responses for a given request or requests synchronously. The
    :class:`EventQueue` will only deliver responses to the request(s) it is
    associated with.
    """
    def __init__(self):
        """
        Construct an empty :class:`EventQueue` which can be passed to
        :meth:`~Session.sendRequest()` and
        :meth:`~Session.sendAuthorizationRequest()` methods.
        """
        selfhandle = internals.blpapi_EventQueue_create()
        super(EventQueue, self).__init__(
            selfhandle,
            internals.blpapi_EventQueue_destroy)
        self.__handle = selfhandle
        self.__sessions = set()

    def nextEvent(self, timeout=0):
        """
        Args:
            timeout (int): Timeout threshold in milliseconds.

        Returns:
            Event: The next :class:`Event` available from the
            :class:`EventQueue`.

        If the specified ``timeout`` is zero this method will wait forever for
        the next event. If the specified ``timeout`` is non zero then if no
        :class:`Event` is available within the specified ``timeout`` an
        :class:`Event` with type of :attr:`~Event.TIMEOUT` will be returned.
        """
        res = internals.blpapi_EventQueue_nextEvent(self.__handle, timeout)
        return Event(res, self._getSessions())

    def tryNextEvent(self):
        """
        Returns:
            Event: If the :class:`EventQueue` is non-empty, the next
            :class:`Event` available, otherwise ``None``.
        """
        res = internals.blpapi_EventQueue_tryNextEvent(self.__handle)
        if res[0]:
            return None
        return Event(res[1], self._getSessions())

    def purge(self):
        """Purge any :class:`Event` objects in this :class:`EventQueue`.

        Purges any :class:`Event` objects in this :class:`EventQueue` which
        have not been processed and cancel any pending requests linked to this
        :class:`EventQueue`.  The :class:`EventQueue` can subsequently be
        re-used for a subsequent request.
        """
        internals.blpapi_EventQueue_purge(self.__handle)
        self.__sessions.clear()

    def _registerSession(self, session):
        """Add a new session to this 'EventQueue'. For internal use."""
        self.__sessions.add(session)

    def _getSessions(self):
        """Get a list of sessions this EventQueue related to.

        For internal use.
        """
        sessions = list(self.__sessions)
        return sessions

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
