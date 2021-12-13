# request.py

"""Defines a request which can be sent for a service.

This file defines a class 'Request' which represents a request sent through the
Session.

"""

import weakref
from .element import Element
from .exception import _ExceptionUtil
from . import internals
from .chandle import CHandle

class Request(CHandle):
    """A single request to a single service.

    :class:`Request` objects are created using :meth:`Service.createRequest()`
    or :meth:`Service.createAuthorizationRequest()`. They are used with
    :meth:`Session.sendRequest()` or
    :meth:`Session.sendAuthorizationRequest()`.

    The :class:`Request` object contains the parameters for a single request to
    a single service. Once a :class:`Request` has been created its fields can
    be populated directly using the functions provided by :class:`Element` or
    using the :class:`Element` interface on the :class:`Element` returned by
    :meth:`asElement()`.

    The schema for the :class:`Request` can be queried using the
    :class:`Element` interface.
    """

    def __init__(self, handle, sessions):
        super(Request, self).__init__(handle, internals.blpapi_Request_destroy)
        self.__handle = handle
        self.__sessions = sessions
        self.__element = None

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string representation of this Request. Call of str(request) is
        equivalent to request.toString() called with default parameters.

        """

        return self.toString()

    def __getitem__(self, name):
        """Equivalent to :meth:`asElement().__getitem__(name)
        <Element.__getitem__>`."""
        return self.asElement()[name]

    def __setitem__(self, name, value):
        """Equivalent to :meth:`asElement().__setitem__(name, value)
        <Element.__setitem__>`."""
        self.asElement()[name] = value

    def set(self, name, value):
        """Equivalent to :meth:`asElement().setElement(name, value)
        <Element.setElement>`."""
        self.asElement().setElement(name, value)

    def append(self, name, value):
        """Equivalent to :meth:`getElement(name).appendValue(value)
        <Element.appendValue>`."""
        return self.getElement(name).appendValue(value)

    def fromPy(self, requestDict):
        """Equivalent to :meth:`asElement().fromPy(requestDict)
        <Element.fromPy>`.

        Args:
            requestDict (collections.abc.Mapping): used to format this
                :class:`Request`. See :meth:`Element.fromPy` for more details.

        Note:
            Using :meth:`fromPy` to format a :class:`Request` that has already
            been formatted is not supported. To further format a
            :class:`Request`, use :meth:`set` / :meth:`append` or the
            ``*Element()`` methods.
        """
        self.asElement().fromPy(requestDict)

    def asElement(self):
        """
        Returns:
            Element: The content of this :class:`Request` as an
            :class:`Element`.
        """
        el = None
        if self.__element:
            el = self.__element()
        if el is None:
            el = Element(internals.blpapi_Request_elements(self.__handle),
                         self)
            self.__element = weakref.ref(el)
        return el

    def getElement(self, name):
        """Equivalent to :meth:`asElement().getElement(name)
        <Element.getElement>`."""
        return self.asElement().getElement(name)

    def getRequestId(self):
        """
        Return the request's id if one exists, otherwise return ``None``.

        If there are issues with this request, the request id
        can be reported to Bloomberg for troubleshooting purposes.

        Note that request id is not the same as correlation
        id and should not be used for correlation purposes.

        Returns:
            str: The request id of the request.
        """
        rc, requestId = internals.blpapi_Request_getRequestId(self.__handle)
        _ExceptionUtil.raiseOnError(rc)
        return requestId

    def toString(self, level=0, spacesPerLevel=4):
        """Equivalent to :meth:`asElement().toString(level, spacesPerLevel)
        <Element.toString>`."""
        return self.asElement().toString(level, spacesPerLevel)

    def _sessions(self):
        """Return session(s) this Request related to. For internal use."""
        return self.__sessions

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
