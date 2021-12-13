# eventdispatcher.py

"""Provide a dispatcher to dispatch events.

This component implements a dispatcher to dispatch events from one or more
Sessions through callbacks.
"""

import warnings
from . import internals
from .chandle import CHandle

class EventDispatcher(CHandle):
    """Dispatches events from one or more Sessions through callbacks

    :class:`EventDispatcher` objects are optionally specified when Session
    objects are created. A single :class:`EventDispatcher` can be shared by
    multiple Session objects.

    The :class:`EventDispatcher` provides an event-driven interface, generating
    callbacks from one or more internal threads for one or more sessions.
    """

    __handle = None # pylint: disable=unused-private-member

    def __init__(self, numDispatcherThreads=1):
        """Construct an :class:`EventDispatcher`.

        Args:
            numDispatcherThreads (int): Number of dispatcher threads

        If ``numDispatcherThreads`` is ``1`` (the default) then a single
        internal thread is created to dispatch events. If
        ``numDispatcherThreads`` is greater than ``1`` then an internal pool of
        ``numDispatcherThreads`` threads is created to dispatch events. The
        behavior is undefined if ``numDispatcherThreads`` is ``0``.
        """
        selfhandle = internals.blpapi_EventDispatcher_create(numDispatcherThreads)
        super(EventDispatcher, self).__init__(
            selfhandle,
            internals.blpapi_EventDispatcher_destroy)
        self.__handle = selfhandle

    def start(self):
        """Start generating callbacks for events from sessions associated with
        this :class:`EventDispatcher`.
        """

        return internals.blpapi_EventDispatcher_start(self.__handle)

    def stop(self, async_=False, **kwargs):
        """Stop generating callbacks.

        Args:
            async\_ (bool): Whether to execute this method asynchronously

        Stop generating callbacks for events from sessions associated with this
        :class:`EventDispatcher`. If the specified ``async_`` is ``False`` (the
        default) then this method blocks until all current callbacks which were
        dispatched through this :class:`EventDispatcher` have completed. If
        ``async_`` is ``True``, this method returns immediately and no further
        callbacks will be dispatched.

        Note:
            If stop is called with ``async_`` of ``False`` from within a
            callback dispatched by this :class:`EventDispatcher` then the
            ``async_`` parameter is overridden to ``True``.
        """

        if 'async' in kwargs:
            warnings.warn(
                "async parameter has been deprecated in favor of async_",
                DeprecationWarning)
            async_ = kwargs.pop('async')

        if kwargs:
            raise TypeError(
                "EventDispatcher.stop() got an unexpected keyword "
                "argument. Only 'async' is allowed for backwards "
                "compatibility.")

        return internals.blpapi_EventDispatcher_stop(self.__handle, async_)

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
