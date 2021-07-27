# topic.py

"""Provide representation of a Topic

This component provides a topic that is used for publishing data on.
"""

from . import internals
from .service import Service
from .utils import get_handle
from .chandle import CHandle


class Topic(CHandle):
    """Used to identify the stream on which a message is published.

    Topic objects are obtained from :meth:`~ProviderSession.createTopics()` on
    :class:`ProviderSession`.  They are used when adding a message to an Event
    for publishing using :meth:`~EventFormatter.appendMessage()` on
    :class:`EventFormatter`.
    """

    def __init__(self, handle=None, sessions=None):
        """Create a :class:`Topic` object.

        Args:
            handle: Handle to the internal implementation
            sessions: Sessions associated with this object

        A :class:`Topic` created with ``handle`` set to ``None`` is not a valid
        topic and must be assigned to from a valid topic before it can be used.
        """
        selfhandle = handle
        if handle is not None:
            selfhandle = internals.blpapi_Topic_create(handle)
        super(Topic, self).__init__(selfhandle, internals.blpapi_Topic_destroy)
        self.__handle = selfhandle
        self.__sessions = sessions

    def isValid(self):
        """
        Returns:
            bool: ``True`` if this :class:`Topic` is valid and can be used to
            publish a message on.
        """
        return self.__handle is not None

    def isActive(self):
        """
        Returns:
            bool: ``True`` if this topic was elected by the platform to become
            the primary publisher.
        """
        return bool(internals.blpapi_Topic_isActive(self.__handle))

    def service(self):
        """
        Returns:
            Service: The service for which this topic was created.
        """
        return Service(internals.blpapi_Topic_service(self.__handle),
                       self.__sessions)

    def __cmp__(self, other):
        """3-way comparison of Topic objects."""
        return internals.blpapi_Topic_compare(
            self.__handle,
            get_handle(other))

    def __lt__(self, other):
        """2-way comparison of Topic objects."""
        return internals.blpapi_Topic_compare(
            self.__handle, get_handle(other)) < 0

    def __eq__(self, other):
        """2-way comparison of Topic objects."""
        return internals.blpapi_Topic_compare(
            self.__handle, get_handle(other)) == 0

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
