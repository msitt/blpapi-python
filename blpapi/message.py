# message.py

"""Defines a message containing elements.

This file defines a class 'Message' which represents an individual message
inside an event and containing elements.

"""

from __future__ import absolute_import

from .element import Element
from .name import Name
from . import internals
import weakref

# Handling a circular dependancy between modules:
#   service->event->message->service
import sys
service = sys.modules.get('blpapi.service')
if service is None:
    from . import service


class Message(object):
    """A handle to a single message.

    Message objects are obtained by iterating an Event. Each Message is
    associated with a Service and with one or more CorrelationId values.  The
    Message contents are represented as an Element and all Elements accessors
    could be used to access the data.

    """

    __handle = None

    def __init__(self, handle, event=None, sessions=None):
        internals.blpapi_Message_addRef(handle)
        self.__handle = handle
        if event is None:
            if sessions is None:
                self.__sessions = set()
            else:
                self.__sessions = sessions
        else:
            self.__sessions = event._sessions()

        self.__element = None

    def __del__(self):
        if self.__handle is not None:
            internals.blpapi_Message_release(self.__handle)

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string representation of this Message. Call of str(message)
        is equivalent to message.toString() called with default parameters.

        """

        return self.toString()

    def messageType(self):
        """Return the type of this message as a Name."""
        return Name._createInternally(
            internals.blpapi_Message_messageType(self.__handle))

    def topicName(self):
        """Return a string containing the topic string of this message.

        If there iss no topic associated with this message then an empty string
        is returned.

        """

        return internals.blpapi_Message_topicName(self.__handle)

    def service(self):
        """Return the Service that this Message is associated with."""
        serviceHandle = internals.blpapi_Message_service(self.__handle)
        return None if serviceHandle is None \
            else service.Service(serviceHandle, self.__sessions)

    def correlationIds(self):
        """Return the list of CorrelationIds associated with this message.

        Note: A Message will have exactly one CorrelationId unless
        'allowMultipleCorrelatorsPerMsg' option was enabled for the Session
        this Message belongs to. When 'allowMultipleCorrelatorsPerMsg' is
        disabled (the default) and more than one active subscription would
        result in the same Message the Message is delivered multiple times
        (without making physical copies). Each Message is accompanied by a
        single CorrelationId. When 'allowMultipleCorrelatorsPerMsg' is enabled
        and more than one active subscription would result in the same Message
        the Message is delivered once with a list of corresponding
        CorrelationId values.

        """

        res = []
        for i in xrange(
                internals.blpapi_Message_numCorrelationIds(self.__handle)):
            res.append(
                internals.blpapi_Message_correlationId(self.__handle, i))
        return res

    def hasElement(self, name, excludeNullElements=False):
        """Equivalent to asElement().hasElement(name, excludeNullElements)."""
        return self.asElement().hasElement(name, excludeNullElements)

    def numElements(self):
        """Equivalent to asElement().numElements()."""
        return self.asElement().numElements()

    def getElement(self, name):
        """Equivalent to asElement().getElement(name)."""
        return self.asElement().getElement(name)

    def getElementAsBool(self, name):
        """Equivalent to asElement().getElementAsBool(name)."""
        return self.asElement().getElementAsBool(name)

    def getElementAsString(self, name):
        """Equivalent to asElement().getElementAsString(name)."""
        return self.asElement().getElementAsString(name)

    def getElementAsInteger(self, name):
        """Equivalent to asElement().getElementAsInteger(name)."""
        return self.asElement().getElementAsInteger(name)

    def getElementAsFloat(self, name):
        """Equivalent to asElement().getElementAsFloat(name)."""
        return self.asElement().getElementAsFloat(name)

    def getElementAsDatetime(self, name):
        """Equivalent to asElement().getElementAsDatetime(name)."""
        return self.asElement().getElementAsDatetime(name)

    def asElement(self):
        """Return the content of this Message as an Element."""
        el = None
        if self.__element:
            el = self.__element()
        if el is None:
            el = Element(internals.blpapi_Message_elements(self.__handle),
                         self)
            self.__element = weakref.ref(el)
        return el

    def toString(self, level=0, spacesPerLevel=4):
        """Format this Element to the string."""
        return self.asElement().toString(level, spacesPerLevel)

    def _handle(self):
        return self.__handle

    def _sessions(self):
        """Return session(s) this Message related to. For internal use."""
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
