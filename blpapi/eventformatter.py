# eventformatter.py

"""Add messages to an Event for publishing

This component adds messages to an Event which can be later published.
"""

from __future__ import absolute_import

from .exception import _ExceptionUtil
from .datetime import _DatetimeUtil
from .message import Message
from .name import Name, getNamePair
from . import internals
from .internals import CorrelationId


class EventFormatter(object):
    """EventFormatter is used to create Events for publishing.

    An EventFormatter is created from an Event obtained from
    createPublishEvent() on Service. Once the Message or Messages have been
    appended to the Event using the EventFormatter the Event can be published
    using publish() on the ProviderSession.

    EventFormatter objects cannot be copied or assigned so as to ensure there
    is no ambiguity about what happens if two EventFormatters are both
    formatting the same Event.

    The EventFormatter supports write once only to each field. It is an error
    to call setElement() or pushElement() for the same name more than once at
    a particular level of the schema when creating a message.

    """

    __boolTraits = (
        internals.blpapi_EventFormatter_setValueBool,
        internals.blpapi_EventFormatter_appendValueBool,
        None)

    __datetimeTraits = (
        internals.blpapi_EventFormatter_setValueDatetime,
        internals.blpapi_EventFormatter_appendValueDatetime,
        _DatetimeUtil.convertToBlpapi)

    __int32Traits = (
        internals.blpapi_EventFormatter_setValueInt32,
        internals.blpapi_EventFormatter_appendValueInt32,
        None)

    __int64Traits = (
        internals.blpapi_EventFormatter_setValueInt64,
        internals.blpapi_EventFormatter_appendValueInt64,
        None)

    __floatTraits = (
        internals.blpapi_EventFormatter_setValueFloat,
        internals.blpapi_EventFormatter_appendValueFloat,
        None)

    __nameTraits = (
        internals.blpapi_EventFormatter_setValueFromName,
        internals.blpapi_EventFormatter_appendValueFromName,
        Name._handle)

    __stringTraits = (
        internals.blpapi_EventFormatter_setValueString,
        internals.blpapi_EventFormatter_appendValueString,
        None)

    __defaultTraits = (
        internals.blpapi_EventFormatter_setValueString,
        internals.blpapi_EventFormatter_appendValueString,
        str)

    @staticmethod
    def __getTraits(value):
        if isinstance(value, str):
            return EventFormatter.__stringTraits
        elif isinstance(value, bool):
            return EventFormatter.__boolTraits
        elif isinstance(value, (int, long)):
            if value >= -(2 ** 31) and value <= (2 ** 31 - 1):
                return EventFormatter.__int32Traits
            elif value >= -(2 ** 63) and value <= (2 ** 63 - 1):
                return EventFormatter.__int64Traits
            else:
                raise ValueError("value is out of supported range")
        elif isinstance(value, float):
            return EventFormatter.__floatTraits
        elif _DatetimeUtil.isDatetime(value):
            return EventFormatter.__datetimeTraits
        elif isinstance(value, Name):
            return EventFormatter.__nameTraits
        else:
            return EventFormatter.__defaultTraits

    def __init__(self, event):
        """Create an EventFormatter to create Messages in the specified 'event'

        Create an EventFormatter to create Messages in the specified 'event'.
        An Event may only be reference by one EventFormatter at any time.
        Attempting to create a second EventFormatter referencing the same
        Event will result in an exception being raised.
        """

        self.__handle = internals.blpapi_EventFormatter_create(event._handle())

    def __del__(self):
        """Destroy this EventFormatter object."""
        internals.blpapi_EventFormatter_destroy(self.__handle)

    def appendMessage(self, messageType, topic, sequenceNumber=None):
        """Append an (empty) message of the specified 'messageType'.

        Append an (empty) message of the specified 'messageType'
        that will be published under the specified 'topic' with the
        specified 'sequenceNumber' to the Event referenced by this
        EventFormatter. It is expected that 'sequenceNumber' is
        greater (unless the value wrapped or None is specified) than the last
        value used in any previous message on this 'topic', otherwise the
        behavior is undefined.
        After a message has been appended its elements
        can be set using the various setElement() methods.
        """
        name = getNamePair(messageType)

        if sequenceNumber is None:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendMessage(
                    self.__handle,
                    name[0],
                    name[1],
                    topic._handle()))
        else:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendMessageSeq(
                    self.__handle,
                    name[0],
                    name[1],
                    topic._handle(),
                    sequenceNumber,
                    0))

    def appendResponse(self, opType):
        """Append an (empty) response message of the specified 'opType'.

        Append an (empty) response message of the specified 'opType'
        that will be sent in response to previously received
        operation request. After a message has been appended its
        elements can be set using the various setElement() methods.
        Only one response can be appended.
        """
        name = getNamePair(opType)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_appendResponse(
                self.__handle,
                name[0],
                name[1]))

    def appendRecapMessage(self, topic, correlationId=None,
                           sequenceNumber=None):
        """Append a (empty) recap message that will be published.

        Append a (empty) recap message that will be published under the
        specified 'topic' with the specified 'sequenceNumber' to the Publish
        Event referenced by this EventFormatter. Specify the optional
        'correlationId' if this recap message is added in
        response to a TOPIC_RECAP message. It is expected that
        'sequenceNumber' is greater (unless the value wrapped or None is
        specified) than the last value used in any previous message on this
        'topic', otherwise the behavior is undefined.
        After a message has been appended its elements can be set using
        the various setElement() methods. It is an error to create append
        a recap message to an Admin event.
        """
        cIdHandle = None if correlationId is None else correlationId._handle()

        if sequenceNumber is None:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendRecapMessage(
                    self.__handle,
                    topic._handle(),
                    cIdHandle))
        else:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendRecapMessageSeq(
                    self.__handle,
                    topic._handle(),
                    cIdHandle,
                    sequenceNumber,
                    0))

    def setElement(self, name, value):
        """Set the element with the specified 'name' to the specified 'value'.

        Set the element with the specified 'name' to the specified
        'value' in the current message in the Event referenced by
        this EventFormatter. If the 'name' is invalid for the
        current message, if appendMessage() has never been called
        or if the element identified by 'name' has already been set
        an exception is raised.
        """
        traits = EventFormatter.__getTraits(value)
        name = getNamePair(name)
        if traits[2] is not None:
            value = traits[2](value)
        _ExceptionUtil.raiseOnError(
            traits[0](self.__handle, name[0], name[1], value))

    def pushElement(self, name):
        """Change the level at which this EventFormatter is operating.

        Change the level at which this EventFormatter is operating
        to the specified element 'name'. The element 'name' must
        identify either a choice, a sequence or an array at the
        current level of the schema or the behavior is
        undefined. After this returns the context of the
        EventFormatter is set to the element 'name' in the schema
        and any calls to setElement() or pushElement() are applied
        at that level. If 'name' represents an array of scalars
        then appendValue() must be used to add values. If 'name'
        represents an array of complex types then appendElement()
        creates the first entry and set the context of the
        EventFormatter to that element. Calling appendElement()
        again will create another entry.
        """
        name = getNamePair(name)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_pushElement(
                self.__handle,
                name[0],
                name[1]))

    def popElement(self):
        """Undo the most recent call to pushLevel() on this EventFormatter.

        Undo the most recent call to pushLevel() on this
        EventFormatter and returns the context of the
        EventFormatter to where it was before the call to
        pushElement(). Once popElement() has been called it is
        invalid to attempt to re-visit the same context.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_popElement(self.__handle))

    def appendValue(self, value):
        traits = EventFormatter.__getTraits(value)
        if traits[2] is not None:
            value = traits[2](value)
        _ExceptionUtil.raiseOnError(traits[1](self.__handle, value))

    def appendElement(self):
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_appendElement(self.__handle))

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
