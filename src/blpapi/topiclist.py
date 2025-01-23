# topiclist.py

"""Provide a representation of a list of topics.

This component implements a list of topics which require topic creation.
"""
from typing import Optional, Set, Union

from .exception import _ExceptionUtil
from .message import Message
from .resolutionlist import ResolutionList
from . import internals
from . import utils
from .utils import get_handle
from .correlationid import CorrelationId
from .chandle import CHandle
from . import typehints  # pylint: disable=unused-import


# pylint: disable=protected-access
class TopicList(CHandle, metaclass=utils.MetaClassForClassesWithEnums):
    """A list of topics which require creation.

    Contains a list of topics which require creation.

    Created from topic strings or from ``TOPIC_SUBSCRIBED`` or
    ``RESOLUTION_SUCCESS`` messages.  This is passed to a
    :meth:`~ProviderSession.createTopics()` call or
    :meth:`~ProviderSession.createTopicsAsync()` call on a
    :class:`ProviderSession`. It is updated and returned by the
    :meth:`~ProviderSession.createTopics()` call.
    """

    NOT_CREATED = internals.TOPICLIST_NOT_CREATED
    CREATED = internals.TOPICLIST_CREATED
    FAILURE = internals.TOPICLIST_FAILURE

    def __init__(self, original: Optional[ResolutionList] = None) -> None:
        """Create an empty :class:`TopicList`, or a :class:`TopicList` based on
        ``original`` :class:`ResolutionList`.

        Args:
            ``original``: Original resolution list to use.

        Raises:
            TypeError: If ``original`` is not an instance of
                :class:`ResolutionList`.

        If ``original`` is ``None`` - create empty :class:`TopicList`.
        Otherwise create a :class:`TopicList` from ``original``.
        In this case ``original`` is used by handle, so if the caller
        modifies original resolution list after the call,
        :class:`TopicList` also changes because owns the same handle.
        """
        if isinstance(original, ResolutionList):
            selfhandle = internals.blpapi_TopicList_createFromResolutionList(
                get_handle(original)
            )
            self.__sessions = original._sessions()
        elif original is not None:
            raise TypeError(
                "'original' should be an instance of 'ResolutionList'"
            )
        else:
            selfhandle = internals.blpapi_TopicList_create(None)
            self.__sessions = set()
        super(TopicList, self).__init__(
            selfhandle, internals.blpapi_TopicList_destroy
        )
        self.__handle = selfhandle

    def add(
        self,
        topicOrMessage: Union[str, Message],
        correlationId: Optional[CorrelationId] = None,
    ) -> int:
        """Add the specified topic or topic from message to this
        :class:`TopicList`.

        Args:
            topicOrMessage: Topic string or message to create
                a topic from
            correlationId: CorrelationId to associate with the
                topic

        Returns:
            ``0`` on success or negative number on failure.

        Raises:
            TypeError: If ``correlationId`` is not an instance of
                :class:`CorrelationId`.

        If topic is passed as ``topicOrMessage``, add the topic to this list,
        optionally specifying a ``correlationId``. After a successful call to
        :meth:`add()` the status for this entry is ``NOT_CREATED``.

        If :class:`Message` is passed as ``topicOrMessage``, add the topic
        contained in the specified ``topicSubscribedMessage`` or
        ``resolutionSuccessMessage`` to this list, optionally specifying a
        ``correlationId``. After a successful call to :meth:`add()` the status
        for this entry is ``NOT_CREATED``.
        """
        if correlationId is None:
            correlationId = CorrelationId()
        if not isinstance(correlationId, CorrelationId):
            raise TypeError(
                "correlationId should be an instance of 'CorrelationId'"
            )
        if isinstance(topicOrMessage, Message):
            return internals.blpapi_TopicList_addFromMessage(
                self.__handle, get_handle(topicOrMessage), correlationId
            )
        return internals.blpapi_TopicList_add(
            self.__handle, topicOrMessage, correlationId
        )

    def correlationIdAt(self, index: int) -> CorrelationId:
        r"""
        Args:
            index: Index of the entry in the list

        Returns:
            Correlation id of the ``index``\th entry.

        Raises:
            Exception: If ``index >= size()``.
        """
        errorCode, cid = internals.blpapi_TopicList_correlationIdAt(
            self.__handle, index
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return CorrelationId(cid)

    def topicString(self, correlationId: CorrelationId) -> str:
        """
        Args:
            correlationId: Correlation id associated with the
                topic.

        Returns:
            Topic of the entry identified by 'correlationId'.

        Raises:
            Exception: If the ``correlationId`` does not identify an entry in
                this list.
        """
        errorCode, topic = internals.blpapi_TopicList_topicString(
            self.__handle, correlationId
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def topicStringAt(self, index: int) -> str:
        r"""
        Args:
            index: Index of the entry

        Returns:
            The full topic string of the ``index``\th entry in this list.

        Raises:
            Exception: If ``index >= size()``.
        """
        errorCode, topic = internals.blpapi_TopicList_topicStringAt(
            self.__handle, index
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def status(self, correlationId: CorrelationId) -> int:
        """
        Args:
            correlationId: Correlation id associated with the
                entry

        Returns:
            Status of the entry in this list identified by the
            specified ``correlationId``. This may be :attr:`NOT_CREATED`,
            :attr:`CREATED` and :attr:`FAILURE`.

        Raises:
            Exception: If the ``correlationId`` does not identify an entry in
                this list.
        """
        errorCode, status = internals.blpapi_TopicList_status(
            self.__handle, correlationId
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def statusAt(self, index: int) -> int:
        r"""
        Args:
            index: Index of the entry

        Returns:
            Status of the ``index``\th entry in this list. This may be
            :attr:`NOT_CREATED`, :attr:`CREATED` and :attr:`FAILURE`.

        Raises:
            Exception: If ``index >= size()``.
        """
        errorCode, status = internals.blpapi_TopicList_statusAt(
            self.__handle, index
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def message(self, correlationId: CorrelationId) -> Message:
        """
        Args:
            correlationId: Correlation id associated with the
                message

        Returns:
            Message received during creation of the topic identified
            by the specified ``correlationId``.

        Raises:
            Exception: If ``correlationId`` does not identify an entry in this
                :class:`TopicList`.

        The message returned can be used when creating an instance of
        :class:`Topic`.
        """
        errorCode, message = internals.blpapi_TopicList_message(
            self.__handle, correlationId
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self._sessions())

    def messageAt(self, index: int) -> Message:
        """
        Args:
            index: Index of the entry

        Returns:
            Message received during creation of the entry at
                ``index``.

        Raises:
            Exception: If ``index >= size()``.

        The message returned can be used when creating an instance of
        :class:`Topic`.
        """
        errorCode, message = internals.blpapi_TopicList_messageAt(
            self.__handle, index
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self._sessions())

    def size(self) -> int:
        """Return the number of entries in this :class:`TopicList`."""
        return internals.blpapi_TopicList_size(self.__handle)

    def _sessions(self) -> Set["typehints.AbstractSession"]:
        """Return session(s) that this 'TopicList' is related to.

        For internal use."""
        return self.__sessions

    def _addSession(self, session: "typehints.AbstractSession") -> None:
        """Add a new session to this 'TopicList'.

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
