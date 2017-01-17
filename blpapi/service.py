# service.py

"""A service which provides access to API data (provide or consume).

All API data is associated with a 'Service'. A service object is obtained
from a Session and contains zero or more 'Operations'. A service can be a
provider service (can generate API data) or a consumer service.

"""


from __future__ import absolute_import

from .event import Event
from .name import getNamePair
from .request import Request
from .schema import SchemaElementDefinition
from .exception import _ExceptionUtil
from . import utils
from . import internals


class Operation(object):
    """Defines an operation which can be performed by a Service.

    Operation objects are obtained from a Service object. They provide
    read-only access to the schema of the Operations Request and the schema of
    the possible response.

    """

    def __init__(self, handle, sessions):
        self.__handle = handle
        self.__sessions = sessions

    def name(self):
        """Return the name of this Operation."""
        return internals.blpapi_Operation_name(self.__handle)

    def description(self):
        """Return a human readable description of this Operation."""
        return internals.blpapi_Operation_description(self.__handle)

    def requestDefinition(self):
        """Return a SchemaElementDefinition for this Operation.

        Return a SchemaElementDefinition which defines the schema for this
        Operation.

        """

        errCode, definition = internals.blpapi_Operation_requestDefinition(
            self.__handle)
        return None if 0 != errCode else\
            SchemaElementDefinition(definition, self.__sessions)

    def numResponseDefinitions(self):
        """Return the number of the response types for this Operation.

        Return the number of the response types that can be returned by this
        Operation.

        """

        return internals.blpapi_Operation_numResponseDefinitions(self.__handle)

    def getResponseDefinitionAt(self, position):
        """Return a SchemaElementDefinition for the response to this Operation.

        Return a SchemaElementDefinition which defines the schema for the
        response that this Operation delivers.

        If 'position' >= numResponseDefinitions() an exception is raised.

        """

        errCode, definition = internals.blpapi_Operation_responseDefinition(
            self.__handle,
            position)
        _ExceptionUtil.raiseOnError(errCode)
        return SchemaElementDefinition(definition, self.__sessions)

    def responseDefinitions(self):
        """Return an iterator over response for this Operation.

        Return an iterator over response types that can be returned by this
        Operation.

        Response type is defined by SchemaElementDefinition object.

        """

        return utils.Iterator(self,
                              Operation.numResponseDefinitions,
                              Operation.getResponseDefinitionAt)

    def _sessions(self):
        """Return session(s) this object is related to. For internal use."""
        return self.__sessions


class Service(object):
    """Defines a service which provides access to API data.

    A Service object is obtained from a Session and contains the Operations
    (each of which contains its own schema) and the schema for Events which
    this Service may produce. A Service object is also used to create Request
    objects used with a Session to issue requests.

    Provider services are created to generate API data and must be registered
    before use.

    The Service object is a handle to the underlying data which is owned by the
    Session. Once a Service has been succesfully opened in a Session it remains
    accessible until the Session is terminated.

    """

    def __init__(self, handle, sessions):
        self.__handle = handle
        self.__sessions = sessions
        internals.blpapi_Service_addRef(self.__handle)

    def __del__(self):
        internals.blpapi_Service_release(self.__handle)

    def __str__(self):
        """Convert the service schema to a string."""
        return self.toString()

    def toString(self, level=0, spacesPerLevel=4):
        """Convert this Service schema to a string.

        Convert this Service schema to a string at (absolute value specified
        for) the optionally specified indentation 'level'. If 'level' is
        specified, optionally specify 'spacesPerLevel', the number of spaces
        per indentation level for this and all of its nested objects. If
        'level' is negative, suppress indentation of the first line. If
        'spacesPerLevel' is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by 'level').

        """

        return internals.blpapi_Service_printHelper(self.__handle,
                                                    level,
                                                    spacesPerLevel)

    def createPublishEvent(self):
        """Create an Event suitable for publishing to this Service.

        Use an EventFormatter to add Messages to the Event and set fields.

        """

        errCode, event = internals.blpapi_Service_createPublishEvent(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return Event(event, self.__sessions)

    def createAdminEvent(self):
        """Create an Admin Event suitable for publishing to this Service.

        Use an EventFormatter to add Messages to the Event and set fields.

        """

        errCode, event = internals.blpapi_Service_createAdminEvent(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return Event(event, self.__sessions)

    def createResponseEvent(self, correlationId):
        """Create a response Event to answer the request.

        Use an EventFormatter to add a Message to the Event and set fields.

        """

        errCode, event = internals.blpapi_Service_createResponseEvent(
            self.__handle,
            correlationId._handle())
        _ExceptionUtil.raiseOnError(errCode)
        return Event(event, self.__sessions)

    def name(self):
        """Return the name of this service."""
        return internals.blpapi_Service_name(self.__handle)

    def description(self):
        """Return a human-readable description of this service."""
        return internals.blpapi_Service_description(self.__handle)

    def hasOperation(self, name):
        """Return True if the specified 'name' is a valid Operation.

        Return True if the specified 'name' identifies a valid Operation in
        this Service.

        """

        names = getNamePair(name)
        return internals.blpapi_Service_hasOperation(self.__handle,
                                                     names[0],
                                                     names[1])

    def getOperation(self, nameOrIndex):
        """Return a specified operation.

        Return an 'Operation' object identified by the specified
        'nameOrIndex', which must be either a string, a Name, or an integer.
        If 'nameOrIndex' is a string or a Name and 'hasOperation(nameOrIndex)
        != True', or if 'nameOrIndex' is an integer and 'nameOrIndex >=
        numOperations()', then an exception is raised.

        """

        if not isinstance(nameOrIndex, (int, long)):
            names = getNamePair(nameOrIndex)
            errCode, operation = internals.blpapi_Service_getOperation(
                self.__handle, names[0], names[1])
            _ExceptionUtil.raiseOnError(errCode)
            return Operation(operation, self.__sessions)
        errCode, operation = internals.blpapi_Service_getOperationAt(
            self.__handle,
            nameOrIndex)
        _ExceptionUtil.raiseOnError(errCode)
        return Operation(operation, self.__sessions)

    def numOperations(self):
        """Return the number of Operations defined by this Service."""
        return internals.blpapi_Service_numOperations(self.__handle)

    def operations(self):
        """Return an iterator over Operations defined by this Service"""
        return utils.Iterator(self,
                              Service.numOperations,
                              Service.getOperation)

    def hasEventDefinition(self, name):
        """Return True if the specified 'name' identifies a valid event.

        Return True if the specified 'name' identifies a valid event in this
        Service, False otherwise.

        Exception is raised if 'name' is neither a Name nor a string.

        """

        names = getNamePair(name)
        return internals.blpapi_Service_hasEventDefinition(self.__handle,
                                                           names[0],
                                                           names[1])

    def getEventDefinition(self, nameOrIndex):
        """Return the definition of a specified event.

        Return a 'SchemaElementDefinition' object describing the element
        identified by the specified 'nameOrIndex', which must be either a
        string or an integer. If 'nameOrIndex' is a string and
        'hasEventDefinition(nameOrIndex) != True', then a 'NotFoundException'
        is raised; if 'nameOrIndex' is an integer and 'nameOrIndex >=
        numEventDefinitions()' then an 'IndexOutOfRangeException' is raised.

        """

        if not isinstance(nameOrIndex, (int, long)):
            names = getNamePair(nameOrIndex)
            errCode, definition = internals.blpapi_Service_getEventDefinition(
                self.__handle,
                names[0],
                names[1])
            _ExceptionUtil.raiseOnError(errCode)
            return SchemaElementDefinition(definition, self.__sessions)
        errCode, definition = internals.blpapi_Service_getEventDefinitionAt(
            self.__handle,
            nameOrIndex)
        _ExceptionUtil.raiseOnError(errCode)
        return SchemaElementDefinition(definition, self.__sessions)

    def numEventDefinitions(self):
        """Return the number of unsolicited events defined by this Service."""
        return internals.blpapi_Service_numEventDefinitions(self.__handle)

    def eventDefinitions(self):
        """Return an iterator over unsolicited events defined by this Service.
        """

        return utils.Iterator(self,
                              Service.numEventDefinitions,
                              Service.getEventDefinition)

    def authorizationServiceName(self):
        """Return the authorization service name.

        Return the name of the Service which must be used in order to authorize
        access to restricted operations on this Service. If no authorization is
        required to access operations on this service an empty string is
        returned. Authorization services never require authorization to use.
        """
        return internals.blpapi_Service_authorizationServiceName(self.__handle)

    def createRequest(self, operation):
        """Return a empty Request object for the specified 'operation'.

        If 'operation' does not identify a valid operation in the Service then
        an exception is raised.

        An application must populate the Request before issuing it using
        Session.sendRequest().

        """

        errCode, request = internals.blpapi_Service_createRequest(
            self.__handle,
            operation)
        _ExceptionUtil.raiseOnError(errCode)
        return Request(request, self.__sessions)

    def createAuthorizationRequest(self, authorizationOperation=None):
        """Return an empty Request object for 'authorizationOperation'.

        If the 'authorizationOperation' does not indentify a valid operation
        for this Service then an exception is raised.

        An application must populate the Request before issuing it using
        Session.sendAuthorizationRequest().

        """

        errCode, request = internals.blpapi_Service_createAuthorizationRequest(
            self.__handle,
            authorizationOperation)
        _ExceptionUtil.raiseOnError(errCode)
        return Request(request, self.__sessions)

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle

    def _sessions(self):
        """Return session(s) this object is related to. For internal use."""
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
