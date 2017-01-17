# subscriptionlist.py

"""Provide a list of subscriptions.

This component provides a list of subscriptions for subscribing and
unsubscribing.
"""

from __future__ import absolute_import

from .exception import _ExceptionUtil
from . import internals
from .internals import CorrelationId


class SubscriptionList(object):
    """A list of subscriptions.

    Contains a list of subscriptions used when subscribing and
    unsubscribing.

    A SubscriptionList is used when calling Session.subscribe(),
    Session.resubscribe() and Session.unsubscribe(). The entries
    can be constructed in a variety of ways.
    """
    def __init__(self):
        """Create an empty SubscriptionList."""
        self.__handle = internals.blpapi_SubscriptionList_create()

    def __del__(self):
        """Destroy this SubscriptionList."""
        internals.blpapi_SubscriptionList_destroy(self.__handle)

    def add(self, topic, fields=None, options=None, correlationId=None):
        """Add the specified 'topic' to this SubscriptionList.

        Add the specified 'topic', with the optionally specified 'fields' and
        the 'options' to this SubscriptionList, associating the optionally
        specified 'correlationId' with it. The 'fields' must be represented as
        a comma separated string or a list of strings, 'options' - as an
        ampersand separated string or list of strings or a name=>value
        dictionary.

        Note that in case of unsubscribe, you can pass empty string or None for
        'topic'
        """
        if correlationId is None:
            correlationId = CorrelationId()
        if topic is None:
            topic = ""
        if (fields is not None) and (not isinstance(fields, str)):
            if isinstance(fields, unicode):
                raise TypeError("unicode strings are not currently supported")
            fields = ",".join(fields)
        if (options is not None) and (not isinstance(options, str)):
            if isinstance(options, unicode):
                raise TypeError("unicode strings are not currently supported")
            if isinstance(options, (list, tuple)):
                options = "&".join(options)
            else:
                options = "&".join(map(
                    lambda x: x[0] if x[1]
                    is None else x[0] + "=" + str(x[1]), options.iteritems()))
        return internals.blpapi_SubscriptionList_addHelper(
            self.__handle,
            topic,
            correlationId._handle(),
            fields,
            options)

    def append(self, subscriptionList):
        """Append a copy of the specified 'subscriptionList' to this list"""
        return internals.blpapi_SubscriptionList_append(
            self.__handle,
            subscriptionList.__handle)

    def clear(self):
        """Remove all entries from this SubscriptionList."""
        return internals.blpapi_SubscriptionList_clear(self.__handle)

    def size(self):
        """Return the number of subscriptions in this SubscriptionList."""
        return internals.blpapi_SubscriptionList_size(self.__handle)

    def correlationIdAt(self, index):
        """Return the CorrelationId at the specified 'index'.

        Return the CorrelationId of the specified 'index'th entry
        in this SubscriptionList. An exception is raised if 'index'>=size().
        """
        errorCode, cid = internals.blpapi_SubscriptionList_correlationIdAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return cid

    def topicStringAt(self, index):
        """Return the full topic string at the specified 'index'.

        Return the full topic string of the specified 'index'th entry in this
        SubscriptionList. An exception is raised if 'index'>=size().
        """
        errorCode, topic = internals.blpapi_SubscriptionList_topicStringAt(
            self.__handle,
            index)
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

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
