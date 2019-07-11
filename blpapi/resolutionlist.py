# resolutionlist.py

"""Provide a representation of a list of topics.

This component implements a list of topics that require resolution.
"""

from .element import Element
from .exception import _ExceptionUtil
from .message import Message
from .name import Name
from . import internals
from . import utils
from .utils import get_handle
from .internals import CorrelationId
from .compat import with_metaclass

# pylint: disable=useless-object-inheritance

@with_metaclass(utils.MetaClassForClassesWithEnums)
class ResolutionList(object):
    """Contains a list of topics that require resolution.

    Created from topic strings or from ``SUBSCRIPTION_STARTED`` messages. This
    is passed to a :meth:`~ProviderSession.resolve()` call or
    :meth:`ProviderSession.resolveAsync()` call on a :class:`ProviderSession`.
    It is updated and returned by the :meth:`~ProviderSession.resolve()` call.

    The class attributes represent the states in which entries of a
    :class:`ResolutionList` can be.
    """

    UNRESOLVED = internals.RESOLUTIONLIST_UNRESOLVED
    RESOLVED = internals.RESOLUTIONLIST_RESOLVED
    RESOLUTION_FAILURE_BAD_SERVICE = \
        internals.RESOLUTIONLIST_RESOLUTION_FAILURE_BAD_SERVICE
    RESOLUTION_FAILURE_SERVICE_AUTHORIZATION_FAILED = \
        internals. \
        RESOLUTIONLIST_RESOLUTION_FAILURE_SERVICE_AUTHORIZATION_FAILED
    RESOLUTION_FAILURE_BAD_TOPIC = \
        internals.RESOLUTIONLIST_RESOLUTION_FAILURE_BAD_TOPIC
    RESOLUTION_FAILURE_TOPIC_AUTHORIZATION_FAILED = \
        internals.RESOLUTIONLIST_RESOLUTION_FAILURE_TOPIC_AUTHORIZATION_FAILED

    @staticmethod
    def extractAttributeFromResolutionSuccess(message, attribute):
        """Return the value of the value in the specified ``message``.

        Args:
            message (Message): Message to extract the attribute from
            attribute (Name): Attribute to extract

        Returns:
            Element: Value of the value in the specified ``message`` which
            represents the specified ``attribute``. If the ``attribute`` is not
            present an empty :class:`Element` is returned.

        The ``message`` must be a message of type ``RESOLUTION_SUCCESS``. The
        ``attribute`` should be an attribute that was requested using
        :meth:`addAttribute()` on the :class:`ResolutionList` passed to the
        :meth:`~ProviderSession.resolve()` or
        :meth:`~ProviderSession.resolveAsync()` that caused this
        ``RESOLUTION_SUCCESS`` message.
        """
        i = internals  # to fit next line in 79 chars
        res = i.blpapi_ResolutionList_extractAttributeFromResolutionSuccess(
            get_handle(message), get_handle(attribute))
        return Element(res, message)

    def __init__(self):
        """Create an empty :class:`ResolutionList`."""
        self.__handle = internals.blpapi_ResolutionList_create(None)
        self.__sessions = set()

    def __del__(self):
        """Destroy this :class:`ResolutionList`."""
        try:
            self.destroy()
        except (NameError, AttributeError):
            pass

    def destroy(self):
        """Destroy resolutionlist"""
        if self.__handle:
            internals.blpapi_ResolutionList_destroy(self.__handle)
            self.__handle = None

    def add(self, topicOrMessage, correlationId=None):
        """Add the specified topic or topic from message to this list.

        Args:
            topicOrMessage (str or Message): Topic or message to add
            correlationId (CorrelationId): CorrelationId to associate with this
                operation

        Returns:
            int: ``0`` on success, negative number on failure

        Raises:
            TypeError: If ``correlationId`` is not an instance of
                :class:`CorrelationId`

        If ``topicOrMessage`` is of string type, add the specified
        ``topicOrMessage`` to this list, optionally specifying a
        ``correlationId``.  After a successful call to :meth:`add()` the status
        for this entry is ``UNRESOLVED_TOPIC``.

        If ``topicOrMessage`` is of :class:`Message` type, add the topic
        contained in the specified ``topicOrMessage`` to this list, optionally
        specifying a ``correlationId``.  After a successful call to
        :meth:`add()` the status for this entry is ``UNRESOLVED_TOPIC``.
        """
        if correlationId is None:
            correlationId = CorrelationId()
        if not isinstance(correlationId, CorrelationId):
            raise TypeError(
                "correlationId should be an instance of 'CorrelationId'")
        if isinstance(topicOrMessage, Message):
            return internals.blpapi_ResolutionList_addFromMessage(
                self.__handle,
                get_handle(topicOrMessage),
                get_handle(correlationId))
        return internals.blpapi_ResolutionList_add(
            self.__handle,
            topicOrMessage,
            get_handle(correlationId))

    def addAttribute(self, attribute):
        """Add the specified ``attribute`` to the list of attributes.

        Args:
            attribute (str): Attribute to add

        Returns:
            int: ``0`` on success, negative number on failure.
        """
        attribute = Name(attribute)
        return internals.blpapi_ResolutionList_addAttribute(
            self.__handle, get_handle(attribute))

    def correlationIdAt(self, index):
        """
        Args:
            index (int): Index of the correlation id

        Returns:
            CorrelationId: CorrelationId at the specified ``index``.

        Raises:
            IndexOutOfRangeException: If ``index >= size()``.
        """
        errorCode, cid = internals.blpapi_ResolutionList_correlationIdAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return cid

    def topicString(self, correlationId):
        """Return the topic of the entry identified by ``correlationId``.

        Args:
            correlationId (CorrelationId): Correlation id that identifies the
                topic

        Returns:
            str: Topic string of the entry identified by ``correlationId``.

        Raises:
            Exception: If ``correlationId`` does not identify an entry in this
                :class:`ResolutionList`.
        """
        errorCode, topic = internals.blpapi_ResolutionList_topicString(
            self.__handle,
            get_handle(correlationId))
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def topicStringAt(self, index):
        """
        Args:
            index (int): Index of the topic string

        Returns:
            str: Topic string at the specified ``index``.

        Raises:
            IndexOutOfRangeException: If ``index >= size()``.
        """
        errorCode, topic = internals.blpapi_ResolutionList_topicStringAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def status(self, correlationId):
        """
        Args:
            correlationId (CorrelationId): Correlation id that identifies the
                entry

        Returns:
            int: status of the entry in this :class:`ResolutionList`.

        Raises:
            Exception: If the ``correlationId`` does not identify an entry in
                this :class:`ResolutionList`.

        The possible statuses are represented by the class attributes of
        :class:`ResolutionList`.
        """
        errorCode, status = internals.blpapi_ResolutionList_status(
            self.__handle,
            get_handle(correlationId))
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def statusAt(self, index):
        """
        Args:
            correlationId (CorrelationId): Correlation id that identifies the
                entry

        Returns:
            int: status of the entry in this :class:`ResolutionList`.

        Raises:
            IndexOutOfRangeException: If ``index >= size()``.

        The possible statuses are represented by the class attributes of
        :class:`ResolutionList`.
        """
        errorCode, status = internals.blpapi_ResolutionList_statusAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def attribute(self, attribute, correlationId):
        """
        Args:
            attribute (str): Attribute of the entry
            correlationId (CorrelationId): Correlation id identifying an entry
                in this list

        Returns:
            Element: Value for the specified ``attribute`` of this list entry.

        Raises:
            Exception: If ``correlationId`` does not identify an entry in this
                :class:`ResolutionList` or if the status of the entry
                identified by ``correlationId`` is not ``RESOLVED``.

        The :class:`Element` returned may be empty if the resolution service
        cannot provide the attribute.
        """
        attribute = Name(attribute)
        errorCode, element = internals.blpapi_ResolutionList_attribute(
            self.__handle,
            get_handle(attribute),
            get_handle(correlationId))

        _ExceptionUtil.raiseOnError(errorCode)

        return Element(element, self)

    def attributeAt(self, attribute, index):
        """
        Args:
            attribute (str): Attribute of the entry
            index (int): Index of the entry

        Returns:
            Element: Value for the specified ``attribute`` of this list entry.

        Raises:
            Exception: If ``index >= size()`` or if the status of the
                ``index``\ th entry identified by ``correlationId`` is not
                ``RESOLVED``.
        """
        attribute = Name(attribute)
        errorCode, element = internals.blpapi_ResolutionList_attributeAt(
            self.__handle,
            get_handle(attribute),
            index)

        _ExceptionUtil.raiseOnError(errorCode)

        return Element(element, self)

    def message(self, correlationId):
        """
        Args:
            correlationId (CorrelationId): Correlation id that identifies an
                entry in this list

        Returns:
            Message: Message received during resolution of the topic
            identified by the specified ``correlationId``.

        Raises:
            Exception: If ``correlationId`` does not identify an entry in this
                :class:`ResolutionList` or if the status of the entry identify
                by ``correlationId`` is not ``RESOLVED`` an exception is
                raised.

        Note:
            The :class:`Message` returned can be used when creating an instance
            of :class:`Topic`.
        """
        errorCode, message = internals.blpapi_ResolutionList_message(
            self.__handle,
            get_handle(correlationId))
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self.__sessions)

    def messageAt(self, index):
        """
        Args:
            index (int): Index of an entry in this list

        Returns:
            Message: Message received during resolution of the topic
            specified ``index``\ th entry in this :class:`ResolutionList`.

        Raises:
            Exception: If ``index >= size()`` or if the status of the
                ``index``\ th entry is not ``RESOLVED`` an exception is raised.

        Note:
            The :class:`Message` returned can be used when creating an instance
            of :class:`Topic`.
        """
        errorCode, message = internals.blpapi_ResolutionList_messageAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self.__sessions)

    def size(self):
        """
        Returns:
            int: Number of entries in this :class:`ResolutionList`.
        """
        return internals.blpapi_ResolutionList_size(self.__handle)

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle

    def _sessions(self):
        """Return session(s) that this 'ResolutionList' is related to.

        For internal use."""
        return self.__sessions

    def _addSession(self, session):
        """Add a new session to this 'ResolutionList'.

        For internal use."""
        self.__sessions.add(session)

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
