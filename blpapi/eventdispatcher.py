# eventdispatcher.py

"""Provide a dispatcher to dispatch events.

This component implements a dispatcher to dispatch events from one or more
Sessions through callbacks.
"""


from __future__ import absolute_import

from . import internals


class EventDispatcher(object):
    """Dispatches events from one or more Sessions through callbacks

    EventDispatcher objects are optionally specified when Session objects are
    created. A single EventDispatcher can be shared by multiple Session
    objects.

    The EventDispatcher provides an event-driven interface, generating
    callbacks from one or more internal threads for one or more sessions.
    """

    __handle = None

    def __init__(self, numDispatcherThreads=1):
        """Construct an EventDispatcher.

        If 'numDispatcherThreads' is 1 (the default) then a single internal
        thread is created to dispatch events. If 'numDispatcherThreads' is
        greater than 1 then an internal pool of 'numDispatcherThreads' threads
        is created to dispatch events. The behavior is undefined if
        'numDispatcherThreads' is 0.
        """

        self.__handle = internals.blpapi_EventDispatcher_create(
            numDispatcherThreads)

    def __del__(self):
        """Destructor."""
        internals.blpapi_EventDispatcher_destroy(self.__handle)

    def start(self):
        """Start generating callbacks.

        Start generating callbacks for events from sessions associated with
        this EventDispatcher.
        """

        return internals.blpapi_EventDispatcher_start(self.__handle)

    def stop(self, async=False):
        """Stop generating callbacks.

        Stop generating callbacks for events from sessions associated with this
        EventDispatcher. If the specified 'async' is False (the default) then
        this method blocks until all current callbacks which were dispatched
        through this EventDispatcher have completed. If 'async' is True, this
        method returns immediately and no further callbacks will be dispatched.

        Note: If stop is called with 'async' of False from within a callback
        dispatched by this EventDispatcher then the 'async' parameter is
        overridden to True.
        """

        return internals.blpapi_EventDispatcher_stop(self.__handle, async)

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
