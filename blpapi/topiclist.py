# topiclist.py

"""Provide a representation of a list of topics.

This component implements a list of topics which require topic creation.
"""

from __future__ import absolute_import

from .exception import _ExceptionUtil
from .message import Message
from .resolutionlist import ResolutionList
from . import internals
from . import utils
from .internals import CorrelationId


class TopicList(object):
    """A list of topics which require creation.

    Contains a list of topics which require creation.

    Created from topic strings or from TOPIC_SUBSCRIBED or RESOLUTION_SUCCESS
    messages.
    This is passed to a createTopics() call or createTopicsAsync() call on a
    ProviderSession. It is updated and returned by the createTopics() call.
    """

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums

    NOT_CREATED = internals.TOPICLIST_NOT_CREATED
    CREATED = internals.TOPICLIST_CREATED
    FAILURE = internals.TOPICLIST_FAILURE

    def __init__(self, original=None):
        """Create an empty TopicList or TopicList based on 'original'.

        If 'original' is None - create empty TopicList. Otherwise create a
        TopicList from 'original'.
        """
        if isinstance(original, ResolutionList):
            self.__handle = \
                internals.blpapi_TopicList_createFromResolutionList(
                    original._handle())
            self.__sessions = original._sessions()
        else:
            self.__handle = internals.blpapi_TopicList_create(None)
            self.__sessions = set()

    def __del__(self):
        """Destroy this TopicList."""
        internals.blpapi_TopicList_destroy(self.__handle)

    def add(self, topicOrMessage, correlationId=None):
        """Add the specified topic or topic from message to this TopicList.

        Add the specified 'topic' to this list, optionally specifying a
        'correlationId'. Returns 0 on success or negative number on failure.
        After a successful call to add() the status for this entry is
        NOT_CREATED.

        If Message is passed as 'topicOrMessage', add the topic contained in
        the specified 'topicSubscribedMessage' or 'resolutionSuccessMessage'
        to this list, optionally specifying a 'correlationId'.
        Returns 0 on success or a negative number on failure.
        After a successful call to add() the status for this entry is
        NOT_CREATED.
        """
        if correlationId is None:
            correlationId = CorrelationId()
        if not isinstance(correlationId, CorrelationId):
            raise TypeError(
                "correlationId should be an instance of 'CorrelationId'")
        if isinstance(topicOrMessage, Message):
            return internals.blpapi_TopicList_addFromMessage(
                self.__handle,
                topicOrMessage._handle(),
                correlationId._handle())
        else:
            return internals.blpapi_TopicList_add(
                self.__handle,
                topicOrMessage,
                correlationId._handle())

    def correlationIdAt(self, index):
        """Return the CorrelationId at the specified 'index'.

        Return the CorrelationId of the specified 'index'th entry
        in this TopicList. An exception is raised if 'index'>=size().
        """
        errorCode, cid = internals.blpapi_TopicList_correlationIdAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return cid

    def topicString(self, correlationId):
        """Return the topic of the entry identified by 'correlationId'.

        Return the topic of the entry identified by 'correlationId'. If the
        'correlationId' does not identify an entry in this TopicList then an
        exception is raised.
        """
        errorCode, topic = internals.blpapi_TopicList_topicString(
            self.__handle,
            correlationId._handle())
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def topicStringAt(self, index):
        """Return the full topic string at the specified 'index'.

        Return the full topic string of the specified 'index'th entry in this
        TopicList. An exception is raised if 'index'>=size().
        """
        errorCode, topic = internals.blpapi_TopicList_topicStringAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def status(self, correlationId):
        """Return the status of the entry identified by 'correlationId'.

        Return the status of the entry in this TopicList identified by the
        specified 'correlationId'. This may be NOT_CREATED, CREATED and
        FAILURE. If the 'correlationId' does not identify an entry in this
        TopicList then an exception is raised.
        """
        errorCode, status = internals.blpapi_TopicList_status(
            self.__handle,
            correlationId._handle())
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def statusAt(self, index):
        """Return the status at the specified 'index'.

        Return the status of the specified 'index'th entry in this TopicList.
        This may be NOT_CREATED, CREATED and FAILURE.
        An exception is raised if 'index'>=size().
        """
        errorCode, status = internals.blpapi_TopicList_statusAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def message(self, correlationId):
        """Return the message identified by 'correlationId'.

        Return the value of the message received during creation of the
        topic identified by the specified 'correlationId'. If 'correlationId'
        does not identify an entry in this TopicList or if the status of the
        entry identify by 'correlationId' is not CREATED an exception is
        raised.

        The message returned can be used when creating an instance of Topic.
        """
        errorCode, message = internals.blpapi_TopicList_message(
            self.__handle,
            correlationId._handle())
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self.__sessions)

    def messageAt(self, index):
        """Return the message received during creation of entry at 'index'.

        Return the value of the message received during creation of the
        specified 'index'th entry in this TopicList. If 'index' >= size() or if
        the status of the 'index'th entry is not CREATED an exception is
        thrown.

        The message returned can be used when creating an instance of Topic.
        """
        errorCode, message = internals.blpapi_TopicList_messageAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self.__sessions)

    def size(self):
        """Return the number of entries in this TopicList."""
        return internals.blpapi_TopicList_size(self.__handle)

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle

    def _sessions(self):
        """Return session(s) that this 'ResolutionList' is related to.

        For internal use."""
        return self.__sessions

    def _addSession(self, session):
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
