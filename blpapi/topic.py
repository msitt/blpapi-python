# topic.py

"""Provide representation of a Topic

This component provides a topic that is used for publishing data on.
"""

from __future__ import absolute_import

from .exception import _ExceptionUtil
from .message import Message
from . import internals
from .internals import CorrelationId
from .service import Service


class Topic(object):
    """Used to identify the stream on which a message is published.

    Topic objects are obtained from createTopic() on ProviderSession. They are
    used when adding a message to an Event for publishing using appendMessage()
    on EventFormatter.
    """

    def __init__(self, handle=None):
        """Create a Topic object.

        Create a Topic object. A Topic created with handle set to None is not
        a valid topic and must be assigned to from a valid topic before it can
        be used.
        """
        self.__handle = handle
        if handle is not None:
            self.__handle = internals.blpapi_Topic_create(handle)

    def __del__(self):
        """Destroy this Topic object."""
        internals.blpapi_Topic_destroy(self.__handle)

    def isValid(self):
        """Return True if this Topic is valid.

        Return True if this Topic is valid and can be used to publish
        a message on.
        """
        return self.__handle is not None

    def isActive(self):
        """Return True if this topic is the primary publisher.

        Return True if this topic was elected by the platform to become the
        primary publisher.
        """
        return bool(internals.blpapi_Topic_isActive(self.__handle))

    def service(self):
        """Return the service for which this topic was created.

        Return the service for which this topic was created.
        """
        return Service(internals.blpapi_Topic_service(self.__handle), None)

    def __cmp__(self, other):
        """3-way comparison of Topic objects."""
        return internals.blpapi_Topic_compare(self.__handle, other.__handle)

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
