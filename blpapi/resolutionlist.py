# resolutionlist.py

"""Provide a representation of a list of topics.

This component implements a list of topics that require resolution.
"""

from __future__ import absolute_import

from .element import Element
from .exception import _ExceptionUtil
from .message import Message
from .name import Name
from . import internals
from . import utils
from .internals import CorrelationId


class ResolutionList(object):
    """Contains a list of topics that require resolution.

    Created from topic strings or from SUBSCRIPTION_STARTED messages. This is
    passed to a resolve() call or resolveAsync() call on a ProviderSession. It
    is updated and returned by the resolve() call.
    """

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums

    UNRESOLVED = internals.RESOLUTIONLIST_UNRESOLVED
    RESOLVED = internals.RESOLUTIONLIST_RESOLVED
    RESOLUTION_FAILURE_BAD_SERVICE = \
        internals.RESOLUTIONLIST_RESOLUTION_FAILURE_BAD_SERVICE
    RESOLUTION_FAILURE_SERVICE_AUTHORIZATION_FAILED = \
        internals.RESOLUTIONLIST_RESOLUTION_FAILURE_SERVICE_AUTHORIZATION_FAILED
    RESOLUTION_FAILURE_BAD_TOPIC = \
        internals.RESOLUTIONLIST_RESOLUTION_FAILURE_BAD_TOPIC
    RESOLUTION_FAILURE_TOPIC_AUTHORIZATION_FAILED = \
        internals.RESOLUTIONLIST_RESOLUTION_FAILURE_TOPIC_AUTHORIZATION_FAILED

    @staticmethod
    def extractAttributeFromResolutionSuccess(message, attribute):
        """Return the value of the value in the specified 'message'.

        Return the value of the value in the specified 'message' which
        represents the specified 'attribute'. The 'message' must be a message
        of type "RESOLUTION_SUCCESS". The 'attribute' should be an attribute
        that was requested using addAttribute() on the ResolutionList passed to
        the resolve() or resolveAsync() that caused this RESOLUTION_SUCCESS
        message. If the 'attribute' is not present an empty Element is
        returned.
        """
        i = internals  # to fit next line in 79 chars
        res = i.blpapi_ResolutionList_extractAttributeFromResolutionSuccess(
            message._handle(), attribute._handle())
        return Element(res, message)

    def __init__(self):
        """Create an empty ResolutionList.

        Create an empty ResolutionList.
        """
        self.__handle = internals.blpapi_ResolutionList_create(None)
        self.__sessions = set()

    def __del__(self):
        """Destroy this ResolutionList."""
        internals.blpapi_ResolutionList_destroy(self.__handle)

    def add(self, topicOrMessage, correlationId=None):
        """Add the specified topic or topic from message to this list.

        If 'topicOrMessage' is of string type, add the specified
        'topicOrMessage' to this list, optionally specifying a 'correlationId'.
        Returns 0 on success or negative number on failure. After a successful
        call to add() the status for this entry is UNRESOLVED_TOPIC.

        If 'topicOrMessage' is of Message type, add the topic contained in the
        specified 'topicOrMessage' to this list, optionally specifying a
        'correlationId'.  Returns 0 on success or a negative number on failure.
        After a successful call to add() the status for this entry is
        UNRESOLVED_TOPIC.
        """
        if correlationId is None:
            correlationId = CorrelationId()
        if not isinstance(correlationId, CorrelationId):
            raise TypeError(
                "correlationId should be an instance of 'CorrelationId'")
        if isinstance(topicOrMessage, Message):
            return internals.blpapi_ResolutionList_addFromMessage(
                self.__handle,
                topicOrMessage._handle(),
                correlationId._handle())
        else:
            return internals.blpapi_ResolutionList_add(
                self.__handle,
                topicOrMessage,
                correlationId._handle())

    def addAttribute(self, attribute):
        """Add the specified 'attribute' to the list of attributes.

        Add the specified 'attribute' to the list of attributes requested
        during resolution for each topic in this ResolutionList. Returns 0 on
        success or a negative number on failure.
        """
        if isinstance(attribute, str):
            attribute = Name(attribute)
        if isinstance(attribute, unicode):
            raise TypeError("unicode strings are not currently supported")
        return internals.blpapi_ResolutionList_addAttribute(
            self.__handle, attribute._handle())

    def correlationIdAt(self, index):
        """Return the CorrelationId at the specified 'index'.

        Return the CorrelationId of the specified 'index'th entry
        in this ResolutionList. An exception is raised if 'index'>=size().
        """
        errorCode, cid = internals.blpapi_ResolutionList_correlationIdAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return cid

    def topicString(self, correlationId):
        """Return the topic of the entry identified by 'correlationId'.

        Return the topic of the entry identified by 'correlationId'. If the
        'correlationId' does not identify an entry in this ResolutionList then
        an exception is raised.
        """
        errorCode, topic = internals.blpapi_ResolutionList_topicString(
            self.__handle,
            correlationId._handle())
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def topicStringAt(self, index):
        """Return the full topic string at the specified 'index'.

        Return the full topic string of the specified 'index'th entry in this
        ResolutionList. An exception is raised if 'index'>=size().
        """
        errorCode, topic = internals.blpapi_ResolutionList_topicStringAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def status(self, correlationId):
        """Return the status of the entry in this ResolutionList.

        Return the status of the entry in this ResolutionList identified by the
        specified 'correlationId'. This may be UNRESOLVED, RESOLVED,
        RESOLUTION_FAILURE_BAD_SERVICE,
        RESOLUTION_FAILURE_SERVICE_AUTHORIZATION_FAILED,
        RESOLUTION_FAILURE_BAD_TOPIC,
        RESOLUTION_FAILURE_TOPIC_AUTHORIZATION_FAILED. If the 'correlationId'
        does not identify an entry in this ResolutionList then an exception is
        raised.
        """
        errorCode, status = internals.blpapi_ResolutionList_status(
            self.__handle,
            correlationId._handle())
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def statusAt(self, index):
        """Return the status of the specified 'index'th entry in this list.

        Return the status of the specified 'index'th entry in this
        ResolutionList. This may be UNRESOLVED, RESOLVED,
        RESOLUTION_FAILURE_BAD_SERVICE,
        RESOLUTION_FAILURE_SERVICE_AUTHORIZATION_FAILED,
        RESOLUTION_FAILURE_BAD_TOPIC,
        RESOLUTION_FAILURE_TOPIC_AUTHORIZATION_FAILED. If 'index' > size() an
        exception is raised.
        """
        errorCode, status = internals.blpapi_ResolutionList_statusAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return status

    def attribute(self, attribute, correlationId):
        """Return the value for the specified 'attribute' of this list entry.

        Return the value for the specified 'attribute' of the entry in this
        ResolutionList identified by the specified 'correlationId'. The Element
        returned may be empty if the resolution service cannot provide the
        attribute. If 'correlationId' does not identify an entry in this
        ResolutionList or if the status of the entry identified by
        'correlationId' is not RESOLVED an exception is raised.
        """
        if isinstance(attribute, str):
            attribute = Name(attribute)
        if isinstance(attribute, unicode):
            raise TypeError("unicode strings are not currently supported")
        errorCode, element = internals.blpapi_ResolutionList_attribute(
            self.__handle,
            attribute._handle(),
            correlationId._handle())

        _ExceptionUtil.raiseOnError(errorCode)

        return Element(element, self)

    def attributeAt(self, attribute, index):
        """Return the value for the specified 'attribute' of 'index'th entry.

        Return the value for the specified 'attribute' of the specified
        'index'th entry in this ResolutionList. The Element returned may be
        empty if the resolution service cannot provide the attribute. If
        'index' >= size() or if the status of the 'index'th entry is not
        RESOLVED an exception is raised.
        """
        if isinstance(attribute, str):
            attribute = Name(attribute)
        if isinstance(attribute, unicode):
            raise TypeError("unicode strings are not currently supported")
        errorCode, element = internals.blpapi_ResolutionList_attributeAt(
            self.__handle,
            attribute._handle(),
            index)

        _ExceptionUtil.raiseOnError(errorCode)

        return Element(element, self)

    def message(self, correlationId):
        """Return the message identified by 'correlationId'.

        Return the value of the message received during resolution of the topic
        identified by the specified 'correlationId'. If 'correlationId' does
        not identify an entry in this ResolutionList or if the status of the
        entry identify by 'correlationId' is not RESOLVED an exception is
        raised.

        The message returned can be used when creating an instance of Topic.
        """
        errorCode, message = internals.blpapi_ResolutionList_message(
            self.__handle,
            correlationId._handle())
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self.__sessions)

    def messageAt(self, index):
        """Return the message received during resolution of entry at 'index'.

        Returns the value of the message received during resolution of the
        specified 'index'th entry in this ResolutionList. If 'index' >= size()
        or if the status of the 'index'th entry is not RESOLVED an exception is
        raised.

        The message returned can be used when creating an instance of Topic.
        """
        errorCode, message = internals.blpapi_ResolutionList_messageAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return Message(message, sessions=self.__sessions)

    def size(self):
        """Return the number of entries in this ResolutionList."""
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
