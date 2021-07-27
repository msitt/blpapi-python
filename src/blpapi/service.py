# service.py

"""A service which provides access to API data (provide or consume).

All API data is associated with a 'Service'. A service object is obtained
from a Session and contains zero or more 'Operations'. A service can be a
provider service (can generate API data) or a consumer service.

"""
import warnings
from .event import Event
from .name import getNamePair
from .request import Request
from .schema import SchemaElementDefinition
from .exception import _ExceptionUtil
from . import utils
from .utils import get_handle
from . import internals
from .chandle import CHandle


class Operation(object):
    """Defines an operation which can be performed by a :class:`Service`.

    Operation objects are obtained from a :class:`Service` object. They provide
    read-only access to the schema of the Operations Request and the schema of
    the possible response.
    """

    def __init__(self, handle, sessions):
        self.__handle = handle
        self.__sessions = sessions

    def name(self):
        """
        Returns:
            str: The name of this :class:`Operation`.
        """
        return internals.blpapi_Operation_name(self.__handle)

    def description(self):
        """
        Returns:
            str: a human readable description of this Operation.
        """
        return internals.blpapi_Operation_description(self.__handle)

    def requestDefinition(self):
        """
        Returns:
            SchemaElementDefinition: Object which defines the schema for this
            :class:`Operation`.
        """

        errCode, definition = internals.blpapi_Operation_requestDefinition(
            self.__handle)
        return None if errCode != 0 else\
            SchemaElementDefinition(definition, self.__sessions)

    def numResponseDefinitions(self):
        """
        Returns:
            int: The number of the response types that can be returned by this
            :class:`Operation`.

        """

        return internals.blpapi_Operation_numResponseDefinitions(self.__handle)

    def getResponseDefinitionAt(self, position):
        """
        Args:
            position (int): Index of the response type

        Returns:
            SchemaElementDefinition: Object which defines the schema for the
            response that this :class:`Operation` delivers.

        Raises:
            Exception: If ``position >= numResponseDefinitions()``.
        """

        errCode, definition = internals.blpapi_Operation_responseDefinition(
            self.__handle,
            position)
        _ExceptionUtil.raiseOnError(errCode)
        return SchemaElementDefinition(definition, self.__sessions)

    def responseDefinitions(self):
        """
        Returns:
            Iterator over response types that can be returned by this
            :class:`Operation`.

        Response type is defined by :class:`SchemaElementDefinition`.
        """

        return utils.Iterator(self,
                              Operation.numResponseDefinitions,
                              Operation.getResponseDefinitionAt)

    def _sessions(self):
        """Return session(s) this object is related to. For internal use."""
        return self.__sessions


class Service(CHandle):
    """Defines a service which provides access to API data.

    A :class:`Service` object is obtained from a :class:`Session` and contains
    the :class:`Operation`\ s (each of which contains its own schema) and the
    schema for :class:`Event`\ s which this :class:`Service` may produce. A
    :class:`Service` object is also used to create :class:`Request` objects
    used with a :class:`Session` to issue requests.

    Provider services are created to generate API data and must be registered
    before use.

    The :class:`Service` object is a handle to the underlying data which is
    owned by the :class:`Session`. Once a :class:`Service` has been succesfully
    opened in a :class:`Session` it remains accessible until the
    :class:`Session` is terminated.
    """

    def __init__(self, handle, sessions):
        super(Service, self).__init__(handle, internals.blpapi_Service_release)
        self.__handle = handle
        self.__sessions = sessions
        internals.blpapi_Service_addRef(self.__handle)

    def __str__(self):
        """Convert the service schema to a string."""
        return self.toString()

    def toString(self, level=0, spacesPerLevel=4):
        """Convert this :class:`Service` schema to a string.

        Args:
            level (int): Indentation level
            spacesPerLevel (int): Number of spaces per indentation level for
                this and all nested objects

        Returns:
            str: This object formatted as a string

        If ``level`` is negative, suppress indentation of the first line. If
        ``spacesPerLevel`` is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by ``level``).
        """

        return internals.blpapi_Service_printHelper(self.__handle,
                                                    level,
                                                    spacesPerLevel)

    def createPublishEvent(self):
        """
        Returns:
            Event: :class:`Event` suitable for publishing to this
            :class:`Service`

        Use an :class:`EventFormatter` to add :class:`Message`\ s to the
        :class:`Event` and set fields.
        """

        errCode, event = internals.blpapi_Service_createPublishEvent(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return Event(event, self.__sessions)

    def createAdminEvent(self):
        """
        Returns:
            Event: An :attr:`~Event.ADMIN` :class:`Event` suitable for
            publishing to this :class:`Service`

        Use an :class:`EventFormatter` to add :class:`Message`\ s to the
        :class:`Event` and set fields.

        **DEPRECATED**
        Use :meth:`Service.createPublishEvent()`.

        """

        warnings.warn(
            "This method is deprecated, see docstring for details",
            DeprecationWarning)
        errCode, event = internals.blpapi_Service_createAdminEvent(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return Event(event, self.__sessions)

    def createResponseEvent(self, correlationId):
        """Create a :attr:`~Event.RESPONSE` :class:`Event` to answer the
        request.

        Args:
            correlationId (CorrelationId): Correlation id to associate with the
                created event

        Returns:
            Event: The created response event.

        Use an :class:`EventFormatter` to add :class:`Message`\ s to the
        :class:`Event` and set fields.
        """

        errCode, event = internals.blpapi_Service_createResponseEvent(
            self.__handle,
            get_handle(correlationId))
        _ExceptionUtil.raiseOnError(errCode)
        return Event(event, self.__sessions)

    def name(self):
        """
        Returns:
            str: Name of this service.
        """
        return internals.blpapi_Service_name(self.__handle)

    def description(self):
        """
        Returns:
            str: Human-readable description of this service.
        """
        return internals.blpapi_Service_description(self.__handle)

    def hasOperation(self, name):
        """
        Returns:
            bool: ``True`` if the specified ``name`` is a valid
            :class:`Operation` in this :class:`Service`.
        """

        names = getNamePair(name)
        return bool(internals.blpapi_Service_hasOperation(self.__handle,
                                                          names[0],
                                                          names[1]))

    def getOperation(self, nameOrIndex):
        """
        Args:
            nameOrIndex (Name or str or int): Name or index of the operation

        Returns:
            Operation: The specified operation.

        Raises:
            Exception: If ``nameOrIndex`` is a string or a :class:`Name` and
                ``hasOperation(nameOrIndex) != True``, or if ``nameOrIndex`` is
                an integer and ``nameOrIndex >= numOperations()``.
        """

        if not isinstance(nameOrIndex, int):
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
        """
        Returns:
            int: The number of :class:`Operation`\ s defined by this
            :class:`Service`.
        """
        return internals.blpapi_Service_numOperations(self.__handle)

    def operations(self):
        """
        Returns:
            Iterator over :class:`Operation`\ s defined by this :class:`Service`
        """
        return utils.Iterator(self,
                              Service.numOperations,
                              Service.getOperation)

    def hasEventDefinition(self, name):
        """
        Args:
            name (Name or str): Event identifier

        Returns:
            bool: ``True`` if the specified ``name`` identifies a valid event
            in this :class:`Service`, ``False`` otherwise.

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string.
        """

        names = getNamePair(name)
        return bool(internals.blpapi_Service_hasEventDefinition(self.__handle,
                                                                names[0],
                                                                names[1]))

    def getEventDefinition(self, nameOrIndex):
        """Get the definition of a specified event.

        Args:
            nameOrIndex (Name or str or int): Name or index of the event

        Returns:
            SchemaElementDefinition: Object describing the element
            identified by the specified ``nameOrIndex``.

        Raises:
            NotFoundException: If ``nameOrIndex`` is a string and
                ``hasEventDefinition(nameOrIndex) != True``
            IndexOutOfRangeException: If ``nameOrIndex`` is an integer and
                ``nameOrIndex >= numEventDefinitions()``
        """

        if not isinstance(nameOrIndex, int):
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
        """
        Returns:
            int: The number of unsolicited events defined by this
            :class:`Service`.
        """
        return internals.blpapi_Service_numEventDefinitions(self.__handle)

    def eventDefinitions(self):
        """
        Returns:
            An iterator over unsolicited events defined by this
            :class:`Service`.
        """

        return utils.Iterator(self,
                              Service.numEventDefinitions,
                              Service.getEventDefinition)

    def authorizationServiceName(self):
        """Get the authorization service name.

        Returns:
            str: The name of the :class:`Service` which must be used in order
            to authorize access to restricted operations on this
            :class:`Service`. If no authorization is required to access
            operations on this service an empty string is returned.

        Authorization services never require authorization to use.
        """
        return internals.blpapi_Service_authorizationServiceName(self.__handle)

    def createRequest(self, operation):
        """Create an empty Request object for the specified ``operation``.

        Args:
            operation: A valid operation on this service

        Returns:
            Request: An empty request for the specified ``operation``.

        Raises:
            Exception: If ``operation`` does not identify a valid operation in
                the :class:`Service`

        An application must populate the :class:`Request` before issuing it
        using :meth:`Session.sendRequest()`.
        """

        errCode, request = internals.blpapi_Service_createRequest(
            self.__handle,
            operation)
        _ExceptionUtil.raiseOnError(errCode)
        return Request(request, self.__sessions)

    def createAuthorizationRequest(self, authorizationOperation=None):
        """Create an empty :class:`Request` object for
        ``authorizationOperation``.

        Args:
            authorizationOperation: A valid operation on this service

        Returns:
            Request: An empty request for the specified
            ``authorizationOperation``.

        Raises:
            Exception: If ``authorizationOperation`` does not identify a valid
                operation in the :class:`Service`

        An application must populate the :class:`Request` before issuing it
        using :meth:`Session.sendAuthorizationRequest()`.
        """

        errCode, request = internals.blpapi_Service_createAuthorizationRequest(
            self.__handle,
            authorizationOperation)
        _ExceptionUtil.raiseOnError(errCode)
        return Request(request, self.__sessions)

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
