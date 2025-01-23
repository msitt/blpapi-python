# subscriptionlist.py

"""Provide a list of subscriptions.

This component provides a class to hold the data used (and returned) by the
'Session.subscribe', 'Session.resubscribe', and 'Session.unsubscribe'
methods.  This class comprises a list in which each list entry contains two
primary fields: a 'CorrelationId' associated with the subscription, and a
string, called a *subscription* *string*, describing the data to be delivered
as a part of the subscription.

STRUCTURE OF SUBSCRIPTION STRING
---------------------------------
The simplest form of a subscription string is a *fully* *qualified*
subscription string, which has the following structure:

"//blp/mktdata/ticker/IBM US Equity?fields=BID,ASK&interval=2"
 \\-----------/\\------/\\-----------/\\------------------------/
       |          |         |                  |
    Service    Prefix   Instrument           Suffix

Such a fully-qualified string is composed of:
: Service Identifier: a string matching the expression
:   '^//[-_.a-zA-Z0-9]+/[-_.a-zA-Z0-9]+$', e.g. //blp/mktdata.  See
:   'blpapi_abstractsession' for further details.
:
: Prefix: a string matching the expression '/([-_.a-zA-Z0-9]+/)?', often used
:   as a symbology identifier.  Common examples include '/ticker/' and
:   '/cusip/'.  Not all services make use of prefices.  Note than an "empty"
:   topic prefix consists of the string "/", so the topic prefix always
:   separates the service string from the instrument string.
:
: Instrument: a non-empty string that does not contain the character '?'
:   (i.e. a string matching '[^?]+') e.g. "IBM US Equity", or "SPX Index".
:   The service, prefix, and instrument together uniquely identify a source
:   for subscription data.
:
: Suffix: a suffix contains a question mark followed by a list of options
:   which can affect the content delivery.  The format of these options is
:   service specific, but they generally follow URI query string conventions:
:   a sequence of "key=value" pairs separated by "&" characters.  Further,
:   many common services follow the convention that the value given for the
:   'fields' key is formatted as a comma-separated list of field names.
:   BLPAPI provides several convenience functions to assist in formatting
:   subscription strings for services that make use of these conventions;
:   see the 'SubscriptionList.add' methods for details.

Subscription strings need not be fully qualified: BLPAPI allows the service and
prefix to be omitted from subscription strings, and automatically qualifies
these strings using information stored in a 'Session' object.

QUALIFYING SUBSCRIPTION STRINGS
-------------------------------
The subscription strings passed to 'Session.subscribe' and
'Session.resubscribe' are automatically qualified if the service identifier is
missing (i.e. if the subscription string does not start with "//"). The
subscription parameters (i.e. the optional part after instrument identifier)
are never modified.

The rules for qualifying the subscription string are:

: o If the subscription string begins with "//" then it is assumed to be a
:   a fully qualified subscription string including service identifier,
:   prefix, and instrument.  In this case the string will not be modified and
:   session options defaults have no affect on the subscription.
:
: o If the subscription string begins with a '/' and the second character is
:   not '/', then the string is assumed to begin with the topic prefix, but
:   no service identifier. In this case the string is qualified by prepending
:   the 'SessionOptions.defaultSubscriptionService()' to the specified
:   string.
:
: o If the subscription string does not begin with a '/' it is assumed to
:   begin with an instrument identifier.  In this case the string is
:   qualified by prepending the
:   'SessionOptions.defaultSubscriptionService()' followed by
:   'SessionOptions.defaultTopicPrefix()' to the specified string.
:   If the 'defaultTopicPrefix' is empty or null, then the prefix used is
:   '/'.  Otherwise (in the case of a nontrivial prefix) if the separator '/'
:   is not specified at the beginning or the end of the 'defaultTopicPrefix',
:   then it will be added.
"""

from __future__ import absolute_import
from typing import Mapping, Optional, Sequence, Union

from .exception import _ExceptionUtil
from . import internals
from .correlationid import CorrelationId
from .utils import conv2str, get_handle, isstr
from .chandle import CHandle
from . import typehints  # pylint: disable=unused-import


class SubscriptionList(CHandle):
    """A list of subscriptions.

    Contains a list of subscriptions used when subscribing and unsubscribing.

    A :class:`SubscriptionList` is used when calling
    :meth:`Session.subscribe()`, :meth:`Session.resubscribe()` and
    :meth:`Session.unsubscribe()`. The entries can be constructed in a variety
    of ways.

    The two important elements when creating a subscription are:

    - Subscription string: A subscription string represents a topic whose
      updates user is interested in.
    - CorrelationId: the unique identifier to tag all data associated with this
      subscription.

    The following table describes how various operations use the above
    elements:

    +-------------+--------------------------+----------------------------+
    |  OPERATION  |     SUBSCRIPTION STRING  |       CORRELATION ID       |
    +=============+==========================+============================+
    |  subscribe  | | Used to specify the    | | Identifier for the       |
    |             | | topic to subscribe to. | | subscription.  If        |
    |             |                          | | uninitialized            |
    |             |                          | | correlationid  was       |
    |             |                          | | specified an internally  |
    |             |                          | | generated correlationId  |
    |             |                          | | will be set for the      |
    |             |                          | | subscription.            |
    +-------------+--------------------------+----------------------------+
    | resubscribe | | Used to specify the new| | Identifier of the        |
    |             | | topic to which the     | | subscription which       |
    |             | | subscription should be | | needs to be modified.    |
    |             | | modified to.           |                            |
    +-------------+--------------------------+----------------------------+
    | unsubscribe |           NOT USED       | | Identifier of the        |
    |             |                          | | subscription which       |
    |             |                          | | needs to be canceled.    |
    +-------------+--------------------------+----------------------------+
    """

    def __init__(self) -> None:
        """Create an empty :class:`SubscriptionList`."""
        selfhandle = internals.blpapi_SubscriptionList_create()
        super(SubscriptionList, self).__init__(
            selfhandle, internals.blpapi_SubscriptionList_destroy
        )
        self.__handle = selfhandle

    def add(
        self,
        topic: Optional[str],
        fields: Union[str, Sequence[str], None] = None,
        options: Union[str, Sequence[str], Mapping, None] = None,
        correlationId: Optional[CorrelationId] = None,
    ) -> int:
        """Add the specified ``topic`` to this :class:`SubscriptionList`.

        Args:
            topic: The topic to subscribe to
            fields: List of fields to subscribe to
            options: List of options
            correlationId: Correlation id to associate with the subscription

        Add the specified ``topic``, with the optionally specified ``fields``
        and the ``options`` to this :class:`SubscriptionList`, associating the
        optionally specified ``correlationId`` with it. The ``fields`` must be
        represented as a comma separated string or a list of strings,
        ``options`` - as an ampersand separated string or list of strings or a
        ``name -> value`` dictionary.

        Note:
            In case of unsubscribe, you can pass empty string or ``None`` for
            ``topic``.
        """
        if correlationId is None:
            correlationId = CorrelationId()
        if topic is None:
            topic = ""

        if fields:
            if isstr(fields):
                fields = conv2str(fields)  # type: ignore # the isstr() check means fields must be string by this point
            else:
                fields = ",".join(fields)
            if fields:
                topic += "?fields=" + fields

        if options:
            if isstr(options):
                options_str = conv2str(options)  # type: ignore # the isstr() check means options must be string by this point
            elif isinstance(options, (list, tuple)):
                options_str = "&".join(options)
            elif isinstance(options, dict):
                options_str = "&".join(
                    [
                        key if val is None else f"{key}={val}"
                        for key, val in options.items()
                    ]
                )
            else:
                options_str = ""

            if options_str:
                opts_prefix = "&" if fields else "?"
                topic += opts_prefix + options_str

        return internals.blpapi_SubscriptionList_addHelper(
            self.__handle, topic, correlationId
        )

    def append(self, other: "typehints.SubscriptionList") -> int:
        """Append a copy of the specified :class:`SubscriptionList` to this
        list.

        Args:
            other: List to append to this one
        """
        return internals.blpapi_SubscriptionList_append(
            self.__handle, get_handle(other)
        )

    def clear(self) -> int:
        """Remove all entries from this object."""
        return internals.blpapi_SubscriptionList_clear(self.__handle)

    def size(self) -> int:
        """
        Returns:
            The number of subscriptions in this object.
        """
        return internals.blpapi_SubscriptionList_size(self.__handle)

    def correlationIdAt(self, index: int) -> CorrelationId:
        r"""
        Args:
            index: Index of the entry in the list

        Returns:
            Correlation id of the ``index``\th entry.

        Raises:
            Exception: If ``index >= size()``.
        """
        errorCode, cid = internals.blpapi_SubscriptionList_correlationIdAt(
            self.__handle, index
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return CorrelationId(cid)

    def topicStringAt(self, index: int) -> str:
        """
        Args:
            index: Index of the entry in the list

        Returns:
            The full topic string at the specified ``index``.

        Raises:
            Exception: If ``index >= size()``.
        """
        errorCode, topic = internals.blpapi_SubscriptionList_topicStringAt(
            self.__handle, index
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return topic

    def addResolved(
        self,
        subscriptionString: str,
        correlationId: Optional[CorrelationId] = None,
    ) -> int:
        """
        Args:
            subscriptionString: Fully-resolved subscription string
            correlationId: Correlation id to associate with the
                subscription

        Add the specified ``subscriptionString`` to this
        :class:`SubscriptionList` object, associating the specified
        ``correlationId`` with it.  The subscription string may include
        options.  The behavior of this function, and of functions operating on
        this :class:`SubscriptionList` object, is undefined unless
        ``subscriptionString`` is a fully-resolved subscription string; clients
        that cannot provide fully-resolved subscription strings should use
        :meth:`add()` instead.

        Note:
            It is at the discretion of each function operating on a
            :class:`SubscriptionList` whether to perform resolution on this
            subscription.
        """
        if correlationId is None:
            correlationId = CorrelationId()
        return internals.blpapi_SubscriptionList_addResolved(
            self.__handle, subscriptionString, correlationId
        )

    def isResolvedTopicAt(self, index: int) -> bool:
        """
        Args:
            index: Index of the entry in the list

        Returns:
            ``True`` if the ``index``th entry in this
            ``SubscriptionList`` object was created using :meth:`addResolved()`
            and ``False`` if it was created using :meth:`add()`.  An exception
            is thrown if ``index >= size()``.
        """
        err, res = internals.blpapi_SubscriptionList_isResolvedAt(
            self.__handle, index
        )
        _ExceptionUtil.raiseOnError(err)
        return res


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
