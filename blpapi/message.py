# message.py

"""Defines a message containing elements.

This file defines a class 'Message' which represents an individual message
inside an event and containing elements.

"""


from __future__ import absolute_import
import sys
import weakref
from blpapi.datetime import _DatetimeUtil, UTC
from .element import Element
from .exception import _ExceptionUtil
from .name import Name
from . import internals
from .utils import deprecated, MetaClassForClassesWithEnums
from .compat import with_metaclass

# pylint: disable=useless-object-inheritance,protected-access

# Handling a circular dependancy between modules:
#   service->event->message->service
service = sys.modules.get('blpapi.service')
if service is None:
    from . import service


@with_metaclass(MetaClassForClassesWithEnums)
class Message(object):
    """A handle to a single message.

    :class:`Message` objects are obtained by iterating an :class:`Event`. Each
    :class:`Message` is associated with a :class:`Service` and with one or more
    :class:`CorrelationId` values.  The :class:`Message` contents are
    represented as an :class:`Element` and all :class:`Element`\ 's accessors
    could be used to access the data.

    The possible fragment types are:

    - :attr:`FRAGMENT_NONE`
    - :attr:`FRAGMENT_START`
    - :attr:`FRAGMENT_INTERMEDIATE`
    - :attr:`FRAGMENT_END`

    The possible recap types are:

    - :attr:`RECAPTYPE_NONE`
    - :attr:`RECAPTYPE_SOLICITED`
    - :attr:`RECAPTYPE_UNSOLICITED`

    :class:`Message` objects are always created by the API, never directly by
    the application.
    """

    __handle = None

    FRAGMENT_NONE = internals.MESSAGE_FRAGMENT_NONE
    """Unfragmented message"""
    FRAGMENT_START = internals.MESSAGE_FRAGMENT_START
    """Start of a fragmented message"""
    FRAGMENT_INTERMEDIATE = internals.MESSAGE_FRAGMENT_INTERMEDIATE
    """Intermediate fragment"""
    FRAGMENT_END = internals.MESSAGE_FRAGMENT_END
    """Final part of a fragmented message"""

    RECAPTYPE_NONE = internals.MESSAGE_RECAPTYPE_NONE
    """Normal data tick"""
    RECAPTYPE_SOLICITED = internals.MESSAGE_RECAPTYPE_SOLICITED
    """Generated on request by subscriber"""
    RECAPTYPE_UNSOLICITED = internals.MESSAGE_RECAPTYPE_UNSOLICITED
    """Generated by the service"""

    def __init__(self, handle, event=None, sessions=None):
        """
        Args:
            handle: Handle to the internal implementation
            event: Event that this message belongs to
            sessions: Sessions that this object is associated with
        """
        internals.blpapi_Message_addRef(handle)
        self.__handle = handle
        if event is None:
            if sessions is None:
                self.__sessions = set()
            else:
                self.__sessions = sessions
        else:
            self.__sessions = event._sessions()

        self.__element = None

    def __del__(self):
        try:
            self.destroy()
        except (NameError, AttributeError):
            pass

    def destroy(self):
        if self.__handle is not None:
            internals.blpapi_Message_release(self.__handle)
            self.__handle = None

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string representation of this Message. Call of str(message)
        is equivalent to message.toString() called with default parameters.

        """

        return self.toString()

    def messageType(self):
        """
        Returns:
            Name: Type of this message.
        """
        return Name._createInternally(
            internals.blpapi_Message_messageType(self.__handle))

    def fragmentType(self):
        """
        Returns:
            int: Fragment type of this message.

        Fragment types are listed in the class docstring.
        """
        return internals.blpapi_Message_fragmentType(self.__handle)

    def recapType(self):
        """
        Returns:
            int: Recap type of this message.

        Recap types are listed in the class docstring.
        """
        return internals.blpapi_Message_recapType(self.__handle)


    @deprecated
    def topicName(self):
        """
        Returns:
            str: Topic string of this message. If there is no topic associated
            with the message, empty string is returned.

        **DEPRECATED**

        This function has been deprecated because messages could contain
        multiple payloads with different correlation ids, and each of these
        correlation ids may map to different topic strings.

        In such a scenario, it would be incorrect to choose one out of the
        multiple topics (for the various correlation id's in the message) as
        the topic name for the message. Trying to make this correct would
        result in extra look up costs.

        For correctness, users are encouraged to maintain a data structure in
        their application to help retrieve the topic name associated with the
        cid's present in the delivered message.
        """
        return internals.blpapi_Message_topicName(self.__handle)

    def service(self):
        """
        Returns:
            Service: Service that this :class:`Message` is associated with.
        """
        serviceHandle = internals.blpapi_Message_service(self.__handle)
        return None if serviceHandle is None \
            else service.Service(serviceHandle, self.__sessions)

    def correlationIds(self):
        """
        Returns:
            [CorrelationId]: Correlation ids associated with this message.

        Note:
            A :class:`Message` will have exactly one :class:`CorrelationId`
            unless ``allowMultipleCorrelatorsPerMsg`` option was enabled for
            the :class:`Session` this :class:`Message` belongs to. When
            ``allowMultipleCorrelatorsPerMsg`` is disabled (the default), and
            more than one active subscription would result in the same
            :class:`Message`, the :class:`Message` is delivered multiple times
            (without making physical copies). Each :class:`Message` is
            accompanied by a single :class:`CorrelationId`. When
            ``allowMultipleCorrelatorsPerMsg`` is enabled and more than one
            active subscription would result in the same :class:`Message` the
            :class:`Message` is delivered once with a list of corresponding
            :class:`CorrelationId` values.
        """

        res = []
        for i in range(
                internals.blpapi_Message_numCorrelationIds(self.__handle)):
            res.append(
                internals.blpapi_Message_correlationId(self.__handle, i))
        return res

    def hasElement(self, name, excludeNullElements=False):
        """Equivalent to asElement().hasElement(name, excludeNullElements)."""
        return self.asElement().hasElement(name, excludeNullElements)

    def numElements(self):
        """Equivalent to :meth:`asElement().numElements()
        <Element.numElements()>`."""
        return self.asElement().numElements()

    def getElement(self, name):
        """Equivalent to :meth:`asElement().getElement(name)
        <Element.getElement()>`."""
        return self.asElement().getElement(name)

    def getElementAsBool(self, name):
        """Equivalent to :meth:`asElement().getElementAsBool(name)
        <Element.getElementAsBool()>`."""
        return self.asElement().getElementAsBool(name)

    def getElementAsString(self, name):
        """Equivalent to :meth:`asElement().getElementAsString(name)
        <Element.getElementAsString()>`."""
        return self.asElement().getElementAsString(name)

    def getElementAsInteger(self, name):
        """Equivalent to :meth:`asElement().getElementAsInteger(name)
        <Element.getElementAsInteger()>`."""
        return self.asElement().getElementAsInteger(name)

    def getElementAsFloat(self, name):
        """Equivalent to :meth:`asElement().getElementAsFloat(name)
        <Element.getElementAsFloat()>`."""
        return self.asElement().getElementAsFloat(name)

    def getElementAsDatetime(self, name):
        """Equivalent to :meth:`asElement().getElementAsDatetime(name)
        <Element.getElementAsDatetime()>`."""
        return self.asElement().getElementAsDatetime(name)

    def getRequestId(self):
        """Return the message's request id if one exists, otherwise return
        ``None``.

        When present, the request id can be reported to Bloomberg to
        troubleshoot the cause of failure messages, or issues with the data
        contained in the message.

        Note that request id is not the same as correlation id and should
        not be used for correlation purposes.

        Returns:
            str: The request id of the message.
        """
        rc, requestId = internals.blpapi_Message_getRequestId(self.__handle)
        _ExceptionUtil.raiseOnError(rc)
        return requestId

    def asElement(self):
        """
        Returns:
            Element: The content of this :class:`Message` as an
            :class:`Element`.
        """
        el = None
        if self.__element:
            el = self.__element()
        if el is None:
            el = Element(internals.blpapi_Message_elements(self.__handle),
                         self)
            self.__element = weakref.ref(el)
        return el

    def toString(self, level=0, spacesPerLevel=4):
        """Format this :class:`Message` to the string at the specified
        indentation level.

        Args:
            level (int): Indentation level
            spacesPerLevel (int): Number of spaces per indentation level for
                this and all nested objects

        Returns:
            str: This element formatted as a string

        If ``level`` is negative, suppress indentation of the first line. If
        ``spacesPerLevel`` is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by ``level``).
        """
        return internals.blpapi_Message_printHelper(
            self.__handle,
            level,
            spacesPerLevel)

    def timeReceived(self, tzinfo=UTC):
        """Get the time when the message was received by the SDK.

        Args:
            tzinfo (~datetime.tzinfo): Timezone info

        Returns:
            datetime.datetime or datetime.date or datetime.time: Time when the
            message was received by the SDK.

        Raises:
            ValueError: If this information was not recorded for this message.
                See :meth:`SessionOptions.recordSubscriptionDataReceiveTimes`
                for information on configuring this recording.

        The resulting datetime will be represented using the specified
        ``tzinfo`` value, and will be measured using a high-resolution clock
        internal to the SDK.
        """
        err_code, time_point = internals.blpapi_Message_timeReceived(
            self.__handle)
        if err_code != 0:
            raise ValueError("Message has no timestamp")
        original = internals.blpapi_HighPrecisionDatetime_fromTimePoint_wrapper(
            time_point)

        native = _DatetimeUtil.convertToNative(original)
        return native.astimezone(tzinfo)

    def _handle(self):
        return self.__handle

    def _sessions(self):
        """Return session(s) this Message related to. For internal use."""
        return self.__sessions

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
