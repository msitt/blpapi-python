# message.py

"""Defines a message containing elements.

This file defines a class 'Message' which represents an individual message
inside an event and containing elements.

"""


from __future__ import absolute_import
import sys
import weakref
import datetime
from typing import Set, Optional, Any, List
from blpapi.datetime import _DatetimeUtil, UTC
from . import typehints # pylint: disable=unused-import
from .typehints import BlpapiNameOrStr, BlpapiNameOrStrOrIndex
from .typehints import BlpapiMessageHandle, AnyPythonDatetime
from .typehints import SupportedElementTypes
from typing import Iterator as IteratorType
from .element import Element
from .exception import _ExceptionUtil
from .name import Name
from . import internals
from .utils import deprecated, MetaClassForClassesWithEnums
from .chandle import CHandle

# Handling a circular dependency between modules:
#   service->event->message->service
service = sys.modules.get('blpapi.service')
if service is None:
    from . import service


# pylint: disable=protected-access
class Message(CHandle, metaclass=MetaClassForClassesWithEnums):
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

    FRAGMENT_NONE = internals.MESSAGE_FRAGMENT_NONE # type: ignore
    """Unfragmented message"""
    FRAGMENT_START = internals.MESSAGE_FRAGMENT_START # type: ignore
    """Start of a fragmented message"""
    FRAGMENT_INTERMEDIATE = internals.MESSAGE_FRAGMENT_INTERMEDIATE # type: ignore
    """Intermediate fragment"""
    FRAGMENT_END = internals.MESSAGE_FRAGMENT_END # type: ignore
    """Final part of a fragmented message"""

    RECAPTYPE_NONE = internals.MESSAGE_RECAPTYPE_NONE # type: ignore
    """Normal data tick"""
    RECAPTYPE_SOLICITED = internals.MESSAGE_RECAPTYPE_SOLICITED # type: ignore
    """Generated on request by subscriber"""
    RECAPTYPE_UNSOLICITED = internals.MESSAGE_RECAPTYPE_UNSOLICITED # type: ignore
    """Generated by the service"""

    def __init__(self,
                 handle : BlpapiMessageHandle,
                 event : Optional["typehints.Event"] = None,
                 sessions : Optional[Set["typehints.AbstractSession"]] = None
                 ) -> None:
        """
        Args:
            handle: Handle to the internal implementation
            event: Event that this message belongs to
            sessions: Sessions that this object is associated with
        """
        internals.blpapi_Message_addRef(handle)
        super(Message, self).__init__(handle, internals.blpapi_Message_release)
        self.__handle = handle
        self.__sessions: Set["typehints.AbstractSession"] = set()
        if event is None:
            if sessions is not None:
                self.__sessions = sessions
        else:
            self.__sessions = event._sessions()

        self.__element = None

    def __str__(self) -> str:
        """x.__str__() <==> str(x)

        Return a string representation of this Message. Call of str(message)
        is equivalent to message.toString() called with default parameters.

        """

        return self.toString()

    def __getitem__(self, name : BlpapiNameOrStrOrIndex) -> Any:
        """Equivalent to
        :meth:`asElement().__getitem__()<Element.__getitem__()>`.
        """
        return self.asElement()[name]

    def __iter__(self) -> IteratorType:
        """Equivalent to
        :meth:`asElement().__iter__()<Element.__iter__()>`.
        """
        return self.asElement().__iter__()

    def __contains__(self, item: SupportedElementTypes) -> bool:
        """Equivalent to
        :meth:`asElement().__contains__()<Element.__contains__()>`.
        """
        return self.asElement().__contains__(item)

    def __len__(self) -> int:
        """Equivalent to
        :meth:`asElement().__len__()<Element.__len__()>`.
        """
        return self.asElement().__len__()

    def messageType(self) -> Name:
        """
        Returns:
            Type of this message.
        """
        return Name._createInternally(
            internals.blpapi_Message_messageType(self.__handle))

    def fragmentType(self) -> int:
        """
        Returns:
            Fragment type of this message.

        Fragment types are listed in the class docstring.
        """
        return internals.blpapi_Message_fragmentType(self.__handle)

    def recapType(self) -> int:
        """
        Returns:
            Recap type of this message.

        Recap types are listed in the class docstring.
        """
        return internals.blpapi_Message_recapType(self.__handle)


    @deprecated
    def topicName(self) -> str:
        """
        Returns:
            Topic string of this message. If there is no topic associated
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
            Service that this :class:`Message` is associated with.
        """
        serviceHandle = internals.blpapi_Message_service(self.__handle)
        return None if serviceHandle is None \
            else service.Service(serviceHandle, self.__sessions)


    def correlationId(self) -> Optional["typehints.CorrelationId"]:
        """
        Returns:
            The single correlation id or the first correlation
            id associated with the message, or None if the message is not
            associated with any correlation ids.

        Note:
            See :meth:`correlationIds` for more details.

            If ``allowMultipleCorrelatorsPerMsg`` is enabled,
            :meth:`correlationIds` should be used.
        """
        numCorrelations = internals.blpapi_Message_numCorrelationIds(
            self.__handle)
        if numCorrelations == 0:
            return None

        return internals.blpapi_Message_correlationId(self.__handle, 0)


    def correlationIds(self) -> List["typehints.CorrelationId"]:
        """
        Returns:
            Correlation ids associated with this message.

        Note:
            A subscription data :class:`Message` has exactly one
            :class:`CorrelationId` unless the
            ``allowMultipleCorrelatorsPerMsg`` option is enabled for the
            :class:`Session`.

            When ``allowMultipleCorrelatorsPerMsg`` is disabled (the default),
            multiple active subscriptions of the same topic result in the same
            :class:`Message` being delivered multiple times (without making
            physical copies), with a single :class:`CorrelationId` from each
            active subscription.

            Otherwise, only one :class:`Message` is delivered with all the
            :class:`CorrelationId`\s from the active subscriptions.
        """

        res = []
        for i in range(
                internals.blpapi_Message_numCorrelationIds(self.__handle)):
            res.append(
                internals.blpapi_Message_correlationId(self.__handle, i))
        return res

    def hasElement(self,
                   name: BlpapiNameOrStr,
                   excludeNullElements: bool=False) -> bool:
        """Equivalent to asElement().hasElement(name, excludeNullElements)."""
        return self.asElement().hasElement(name, excludeNullElements)

    def numElements(self) -> int:
        """Equivalent to :meth:`asElement().numElements()
        <Element.numElements()>`."""
        return self.asElement().numElements()

    def getElement(self, name: BlpapiNameOrStrOrIndex) -> Element:
        """Equivalent to :meth:`asElement().getElement(name)
        <Element.getElement()>`."""
        return self.asElement().getElement(name)

    def getElementAsBool(self, name: BlpapiNameOrStr) -> bool:
        """Equivalent to :meth:`asElement().getElementAsBool(name)
        <Element.getElementAsBool()>`."""
        return self.asElement().getElementAsBool(name)

    def getElementAsString(self, name: BlpapiNameOrStr) -> str:
        """Equivalent to :meth:`asElement().getElementAsString(name)
        <Element.getElementAsString()>`."""
        return self.asElement().getElementAsString(name)

    def getElementAsInteger(self, name: BlpapiNameOrStr) -> int:
        """Equivalent to :meth:`asElement().getElementAsInteger(name)
        <Element.getElementAsInteger()>`."""
        return self.asElement().getElementAsInteger(name)

    def getElementAsFloat(self, name: BlpapiNameOrStr) -> float:
        """Equivalent to :meth:`asElement().getElementAsFloat(name)
        <Element.getElementAsFloat()>`."""
        return self.asElement().getElementAsFloat(name)

    def getElementAsDatetime(self, name: BlpapiNameOrStr) -> AnyPythonDatetime:
        """Equivalent to :meth:`asElement().getElementAsDatetime(name)
        <Element.getElementAsDatetime()>`."""
        return self.asElement().getElementAsDatetime(name)

    def getRequestId(self) -> Optional[str]:
        """Return the message's request id if one exists, otherwise return
        ``None``.

        When present, the request id can be reported to Bloomberg to
        troubleshoot the cause of failure messages, or issues with the data
        contained in the message.

        Note that request id is not the same as correlation id and should
        not be used for correlation purposes.

        Returns:
            The request id of the message.
        """
        rc, requestId = internals.blpapi_Message_getRequestId(self.__handle)
        _ExceptionUtil.raiseOnError(rc)
        return requestId

    def asElement(self) -> Element:
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
            self.__element = weakref.ref(el) # type: ignore
        return el

    def toString(self, level: int=0, spacesPerLevel: int=4) -> str:
        """Format this :class:`Message` to the string at the specified
        indentation level.

        Args:
            level: Indentation level
            spacesPerLevel: Number of spaces per indentation level for
                this and all nested objects

        Returns:
            This element formatted as a string

        If ``level`` is negative, suppress indentation of the first line. If
        ``spacesPerLevel`` is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by ``level``).
        """
        return internals.blpapi_Message_printHelper(
            self.__handle,
            level,
            spacesPerLevel)

    def toPy(self):
        """Equivalent to :meth:`asElement().toPy()<Element.toPy()>`."""
        return self.asElement().toPy()

    def timeReceived(self, tzinfo: datetime.tzinfo=UTC) -> AnyPythonDatetime:
        """Get the time when the message was received by the SDK.

        Args:
            tzinfo: Timezone info

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
        return native.astimezone(tzinfo) # type: ignore

    def _sessions(self) -> Set["typehints.AbstractSession"]:
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
