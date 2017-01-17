# request.py

"""Defines a request which can be sent for a service.

This file defines a class 'Request' which represents a request sent through the
Session.

"""

from __future__ import absolute_import

from .element import Element
from . import internals
import weakref


class Request(object):
    """A single request to a single service.

    Request objects are created using Service.createRequest() or
    Service.createAuthorizationRequest(). They are used with
    Session.sendRequest() or Session.sendAuthorizationRequest().

    The Request object contains the parameters for a single request to a single
    service. Once a Request has been created its fields can be populated
    directly using the functions provided by Element or using the Element
    interface on the Element returned by asElement().

    The schema for the Request can be queried using the Element interface.

    """

    def __init__(self, handle, sessions):
        self.__handle = handle
        self.__sessions = sessions
        self.__element = None

    def __del__(self):
        internals.blpapi_Request_destroy(self.__handle)

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string representation of this Request. Call of str(request) is
        equivalent to request.toString() called with default parameters.

        """

        return self.toString()

    def set(self, name, value):
        """Equivalent to asElement().setElement(name, value)."""
        self.asElement().setElement(name, value)

    def append(self, name, value):
        """Equivalent to getElement(name).appendValue(value)."""
        return self.getElement(name).appendValue(value)

    def asElement(self):
        """Return the content of this Request as an Element."""
        el = None
        if self.__element:
            el = self.__element()
        if el is None:
            el = Element(internals.blpapi_Request_elements(self.__handle),
                         self)
            self.__element = weakref.ref(el)
        return el

    def getElement(self, name):
        """Equivalent to asElement().getElement(name)."""
        return self.asElement().getElement(name)

    def toString(self, level=0, spacesPerLevel=4):
        """Format this Element to the string."""
        return self.asElement().toString(level, spacesPerLevel)

    def _handle(self):
        return self.__handle

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
