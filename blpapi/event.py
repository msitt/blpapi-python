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

from __future__ import absolute_import

from .message import Message
from . import internals
from . import utils

import sys

#sys.modules[__name__] = utils._Constants()


class MessageIterator(object):
    """An iterator over the 'Message' objects within an Event.

    Few clients will ever make direct use of 'MessageIterator' objects; Python
    'for' loops allow clients to operate directly in terms of 'Event' and
    'Message' objects'. (See the usage example above.)
    """

    def __init__(self, event):
        self.__handle = \
            internals.blpapi_MessageIterator_create(event._handle())
        self.__event = event

    def __del__(self):
        internals.blpapi_MessageIterator_destroy(self.__handle)

    def __iter__(self):
        return self

    def next(self):
        retCode, message = internals.blpapi_MessageIterator_next(self.__handle)
        if retCode:
            raise StopIteration()
        else:
            return Message(message, self.__event)


class Event(object):
    """A single event resulting from a subscription or a request.

    'Event' objects are created by the API and passed to the application either
    through a registered 'EventHandler' or 'EventQueue' or returned either from
    the 'Session.nextEvent()' or 'Session.tryNextEvent()' methods. 'Event'
    objects contain 'Message' objects which can be accessed using an iteration
    over 'Event':

        for message in event:
            ...

    The 'Event' object is a handle to an event. The event is the basic unit of
    work provided to applications. Each 'Event' object consists of an
    'EventType' attribute and zero or more 'Message' objects.

    Event objects are always created by the API, never directly by the
    application.

    Class attributes:
        The possible types of event:
        ADMIN                 Admin event
        SESSION_STATUS        Status updates for a session
        SUBSCRIPTION_STATUS   Status updates for a subscription
        REQUEST_STATUS        Status updates for a request
        RESPONSE              The final (possibly only) response to a request
        PARTIAL_RESPONSE      A partial response to a request
        SUBSCRIPTION_DATA     Data updates resulting from a subscription
        SERVICE_STATUS        Status updates for a service
        TIMEOUT               An Event returned from nextEvent() if it
                              timed out
        AUTHORIZATION_STATUS  Status updates for user authorization
        RESOLUTION_STATUS     Status updates for a resolution operation
        TOPIC_STATUS          Status updates about topics for service providers
        ROKEN_STATUS          Status updates for a generate token request
        REQUEST               Request event
        UNKNOWN               Unknown event
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
        self.__handle = handle
        self.__sessions = sessions

    def __del__(self):
        internals.blpapi_Event_release(self.__handle)

    def eventType(self):
        """Return the type of messages contained by this 'Event'."""
        return internals.blpapi_Event_eventType(self.__handle)

    def __iter__(self):
        """Return the iterator over messages contained in this 'Event'."""
        return MessageIterator(self)

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle

    def _sessions(self):
        """Return session(s) that this 'Event' is related to.

        For internal use."""
        return self.__sessions

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums


class EventQueue(object):
    """A construct used to handle replies to request synchronously.

    'EventQueue()' construct an empty 'EventQueue' which can be passed to
    'Session.sendRequest()' and 'Session.sendAuthorizationRequest()' methods.

    When a request is submitted an application can either handle the responses
    asynchronously as they arrive or use an 'EventQueue' to handle all
    responses for a given request or requests synchronously. The 'EventQueue'
    will only deliver responses to the request(s) it is associated with.
    """
    def __init__(self):
        self.__handle = internals.blpapi_EventQueue_create()
        self.__sessions = set()

    def __del__(self):
        internals.blpapi_EventQueue_destroy(self.__handle)

    def nextEvent(self, timeout=0):
        """Return the next Event available from the 'EventQueue'.

        If the specified 'timeout' is zero this method will wait forever for
        the next event. If the specified 'timeout' is non zero then if no
        'Event' is available within the specified 'timeout' an 'Event' with
        type of 'TIMEOUT' will be returned.

        The 'timeout' is specified in milliseconds.
        """
        res = internals.blpapi_EventQueue_nextEvent(self.__handle, timeout)
        return Event(res, self._getSessions())

    def tryNextEvent(self):
        """If the 'EventQueue' is non-empty, return the next Event available.

        If the 'EventQueue' is non-empty, return the next 'Event' available. If
        the 'EventQueue' is empty, return None with no effect the state of
        'EventQueue'.
        """
        res = internals.blpapi_EventQueue_tryNextEvent(self.__handle)
        if res[0]:
            return None
        else:
            return Event(res[1], self._getSessions())

    def purge(self):
        """Purge any 'Event' objects in this 'EventQueue'.

        Purges any 'Event' objects in this 'EventQueue' which have not been
        processed and cancel any pending requests linked to this 'EventQueue'.
        The 'EventQueue' can subsequently be re-used for a subsequent request.
        """
        internals.blpapi_EventQueue_purge(self.__handle)
        self.__sessions.clear()

    def _handle(self):
        """Return the internal implementation. For internal use."""
        return self.__handle

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
