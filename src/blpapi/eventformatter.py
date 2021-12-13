# eventformatter.py

"""Add messages to an Event for publishing

This component adds messages to an Event which can be later published.
"""

from .exception import _ExceptionUtil, InvalidConversionException, \
    IndexOutOfRangeException, InvalidArgumentException, NotFoundException
from .datetime import _DatetimeUtil
from .message import Message
from .name import Name, getNamePair
from . import internals
from .utils import get_handle, invoke_if_valid, isNonScalarSequence
from .chandle import CHandle
from .compat import Mapping

from collections import deque

class EventFormatter(CHandle):
    """:class:`EventFormatter` is used to populate :class:`Event`\ s for
    publishing.

    An :class:`EventFormatter` is created from an :class:`Event` obtained from
    :class:`~Service.createPublishEvent()` on :class:`Service`. Once the
    :class:`Message` or :class:`Message`\ s have been appended to the
    :class:`Event` using the :class:`EventFormatter` the :class:`Event` can be
    published using :meth:`~ProviderSession.publish()` on the
    :class:`ProviderSession`.

    :class:`EventFormatter` objects cannot be copied to ensure that there is
    no ambiguity about what happens if two :class:`EventFormatter`\ s are both
    formatting the same :class:`Event`.

    The :class:`EventFormatter` supports appending message of the same type
    multiple times in the same :class:`Event`. However the
    :class:`EventFormatter` supports write once only to each field. It is an
    error to call :meth:`setElement()` or :meth:`pushElement()` for the same
    name more than once at a particular level of the schema when creating a
    message.
    """

    __boolTraits = (
        internals.blpapi_EventFormatter_setValueBool,
        internals.blpapi_EventFormatter_appendValueBool,
        None)

    __datetimeTraits = (
        internals.blpapi_EventFormatter_setValueHighPrecisionDatetime,
        internals.blpapi_EventFormatter_appendValueHighPrecisionDatetime,
        _DatetimeUtil.convertToBlpapi)

    __int32Traits = (
        internals.blpapi_EventFormatter_setValueInt32,
        internals.blpapi_EventFormatter_appendValueInt32,
        None)

    __int64Traits = (
        internals.blpapi_EventFormatter_setValueInt64,
        internals.blpapi_EventFormatter_appendValueInt64,
        None)

    __floatTraits = (
        internals.blpapi_EventFormatter_setValueFloat,
        internals.blpapi_EventFormatter_appendValueFloat,
        None)

    __nameTraits = (
        internals.blpapi_EventFormatter_setValueFromName,
        internals.blpapi_EventFormatter_appendValueFromName,
        Name._handle) #pylint: disable=protected-access

    __stringTraits = (
        internals.blpapi_EventFormatter_setValueString,
        internals.blpapi_EventFormatter_appendValueString,
        None)

    __defaultTraits = (
        internals.blpapi_EventFormatter_setValueString,
        internals.blpapi_EventFormatter_appendValueString,
        str)

    #pylint: disable=too-many-return-statements
    @staticmethod
    def __getTraits(value):
        """Returns traits for value based on its type"""
        if isinstance(value, str):
            return EventFormatter.__stringTraits
        if isinstance(value, bool):
            return EventFormatter.__boolTraits
        if isinstance(value, int):
            if -(2 ** 31) <= value <= (2 ** 31 - 1):
                return EventFormatter.__int32Traits
            if -(2 ** 63) <= value <= (2 ** 63 - 1):
                return EventFormatter.__int64Traits
            raise InvalidConversionException(
                "Value is out of supported range (INT64): {}".format(value), 0)
        if isinstance(value, float):
            return EventFormatter.__floatTraits
        if _DatetimeUtil.isDatetime(value):
            return EventFormatter.__datetimeTraits
        if isinstance(value, Name):
            return EventFormatter.__nameTraits
        return EventFormatter.__defaultTraits

    def __init__(self, event):
        """Create an :class:`EventFormatter` to create :class:`Message`\ s in
        the specified ``event``.

        Args:
            event (Event): Event to be formatted

        An :class:`Event` may only be referenced by one :class:`EventFormatter`
        at any time.  Attempting to create a second :class:`EventFormatter`
        referencing the same :class:`Event` will result in an exception being
        raised.
        """
        selfhandle = internals.blpapi_EventFormatter_create(get_handle(event))
        super(EventFormatter, self).__init__(
            selfhandle,
            internals.blpapi_EventFormatter_destroy)
        self.__handle = selfhandle
        self.latestMessageName = None

    def appendMessage(self, messageType, topic, sequenceNumber=None):
        """Append an (empty) message to the :class:`Event` referenced by this
        :class:`EventFormatter`

        Args:
            messageType (Name or str): Type of the message
            topic (Topic): Topic to publish the message under
            sequenceNumber (int): Sequence number of the message

        After a message has been appended its elements can be set using the
        various :meth:`setElement()` methods.

        Note:
            It is expected that ``sequenceNumber`` is greater (unless the value
            wrapped or ``None`` is specified) than the last value used in any
            previous message on this ``topic``, otherwise the behavior is
            undefined.
        """
        name = getNamePair(messageType)

        if sequenceNumber is None:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendMessage(
                    self.__handle,
                    name[0],
                    name[1],
                    get_handle(topic)))
        else:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendMessageSeq(
                    self.__handle,
                    name[0],
                    name[1],
                    get_handle(topic),
                    sequenceNumber,
                    0))

        self.latestMessageName = messageType

    def appendResponse(self, operationName):
        """Append an (empty) response message for the specified
        ``operationName``.

        Args:
            operationName (Name or str): Name of the operation whose response
                type to use

        Append an (empty) response message for the specified ``operationName``
        (e.g. ``ReferenceDataRequest``) that will be sent in response to the
        previously received operation request. After a message for this
        operation has been appended its elements can be set using the
        :meth:`setElement()` method. Only one response can be appended.

        Note:
            The behavior is undefined unless the :class:`Event` is currently
            empty.

        Note:
            For ``PermissionRequest`` messages, use the ``PermissionResponse``
            operation name.
        """
        name = getNamePair(operationName)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_appendResponse(
                self.__handle,
                name[0],
                name[1]))

        self.latestMessageName = "<Response>"

    def appendRecapMessage(self, topic, correlationId=None,
                           sequenceNumber=None,
                           fragmentType=Message.FRAGMENT_NONE):
        """Append a (empty) recap message to the :class:`Event` referenced by
        this :class:`EventFormatter`.

        Args:
            topic (Topic): Topic to publish under
            correlationId (CorrelationId): Specify if recap message
                added in response to a ``TOPIC_RECAP`` message
            sequenceNumber (int): Sequence number of the message
            fragmentType (int): Type of the message fragment

        Specify the optional ``correlationId`` if this recap message is added
        in response to a ``TOPIC_RECAP`` message.

        After a message has been appended its elements can be set using the
        various :meth:`setElement()` methods. It is an error to create append a
        recap message to an Admin event.

        Single-tick recap messages should have ``fragmentType`` set to
        :attr:`Message.FRAGMENT_NONE`. Multi-tick recaps can have either
        :attr:`Message.FRAGMENT_START`, :attr:`Message.FRAGMENT_INTERMEDIATE`,
        or :attr:`Message.FRAGMENT_END` as the ``fragmentType``.

        Note:
            It is expected that ``sequenceNumber`` is greater (unless the value
            wrapped or ``None`` is specified) than the last value used in any
            previous message on this ``topic``, otherwise the behavior is
            undefined.
        """
        # pylint: disable=line-too-long
        cIdHandle = None if correlationId is None else get_handle(correlationId)

        if sequenceNumber is None:
            if fragmentType == Message.FRAGMENT_NONE:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendRecapMessage(
                        self.__handle,
                        get_handle(topic),
                        cIdHandle))
            else:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendFragmentedRecapMessage(
                        self.__handle,
                        None,
                        None,
                        get_handle(topic),
                        cIdHandle,
                        fragmentType))
        else:
            if fragmentType == Message.FRAGMENT_NONE:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendRecapMessageSeq(
                        self.__handle,
                        get_handle(topic),
                        cIdHandle,
                        sequenceNumber,
                        0))
            else:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendFragmentedRecapMessageSeq(
                        self.__handle,
                        None,
                        None,
                        get_handle(topic),
                        fragmentType,
                        sequenceNumber))

        self.latestMessageName = "<Recap>"

    def setElement(self, name, value):
        """Set an element in the :class:`Event` referenced by this
        :class:`EventFormatter`.

        Args:
            name (Name or str): Name of the element to set
            value (bool or str or int or float or ~datetime.datetime or Name):
                Value to set the element to

        If the ``name`` is invalid for the current message, or if
        :meth:`appendMessage()` has never been called, or if the element
        identified by ``name`` has already been set, an exception will be
        raised.

        Note:
            Clients wishing to format and publish null values (e.g. for the
            purpose of cache management) should *not* use this function; use
            :meth:`setElementNull` instead.
        """
        traits = EventFormatter.__getTraits(value)
        name = getNamePair(name)
        value = invoke_if_valid(traits[2], value)
        _ExceptionUtil.raiseOnError(
            traits[0](self.__handle, name[0], name[1], value))

    def setElementNull(self, name):
        """Create a null element with the specified ``name``.

        Args:
            name (Name or str): Name of the element

        Note:
            Whether or not fields containing null values are published to
            subscribers depends on the details of the service and schema
            configuration.
        """
        name = getNamePair(name)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_setValueNull(
                self.__handle,
                name[0],
                name[1]))

    def pushElement(self, name):
        """Change the level at which this :class:`EventFormatter` is operating.

        Args:
            name (Name or str): Name of the element that is used to determine
                                the level

        After this returns the context of the :class:`EventFormatter` is set to
        the element ``name`` in the schema and any calls to
        :meth:`setElement()` or :meth:`pushElement()` are applied at that
        level.

        If ``name`` represents an array of scalars then :meth:`appendValue()`
        must be used to add values.

        If ``name`` represents an array of complex types then
        :meth:`appendElement()` creates the first entry and sets the context of
        the :class:`EventFormatter` to that element.

        Calling :meth:`appendElement()` again will create another entry.

        If the ``name`` is invalid for the current message, if
        :meth:`appendMessage()` has never been called or if the element
        identified by ``name`` has already been set an exception is raised.

        Note:
            The element ``name`` must identify either a choice, a sequence or
            an array at the current level of the schema or the behavior is
            undefined.
        """
        name = getNamePair(name)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_pushElement(
                self.__handle,
                name[0],
                name[1]))

    def popElement(self):
        """Undo the most recent call to :meth:`pushElement` or
        :meth:`appendElement` on this :class:`EventFormatter` and return the
        context of the :class:`EventFormatter` to where it was before the call
        to :meth:`pushElement` or :meth:`appendElement`. Once
        :meth:`popElement` has been called it is invalid to attempt to
        re-visit the same context.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_popElement(self.__handle))

    def appendValue(self, value):
        """
        Args:
            value (bool or str or int or float or ~datetime.datetime or Name):
                Value to append
        """
        traits = EventFormatter.__getTraits(value)
        value = invoke_if_valid(traits[2], value)
        _ExceptionUtil.raiseOnError(traits[1](self.__handle, value))

    def appendElement(self):
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_appendElement(self.__handle))

    def fromPy(self, value):
        """
        Format this :class:`EventFormatter`\ 's underlying :class:`Event` using
        ``value``.

        Args:
            value (collections.abc.Mapping): the object used for formatting

        Raises:
            Exception: if ``value`` cannot properly format the :class:`Event`

        The ``value`` used to format the :class:`Event` is always a
        :py:class:`collections.abc.Mapping` instance. The keys are
        :class:`Name` or :py:class:`str` instances, and the values vary
        depending on the :class:`Element` being formatted.

        If the :class:`Element` identified by the key is

        * a complex type, it is formatted using a
          :py:class:`collections.abc.Mapping` whose keys are the names of its
          sub-:class:`Element`\ s.
        * an array, it is formatted using a
          :py:class:`collections.abc.Sequence` of the :class:`Element`'s
          values (see note below for more details).

        Otherwise, the :class:`Element` is formatted using its associated
        scalar value (e.g. :py:class:`str` or :py:class:`int`).

        Note:
            Although :py:class:`str`, :py:class:`bytes`, :py:class:`bytearray`,
            and :py:class:`memoryview` are sub-types of
            :py:class:`collections.abc.Sequence`, :meth:`fromPy` treats them as
            scalars of type string and will use them to format scalar
            :class:`Element`\ s. If you wish to format an array
            :class:`Element` with instances of the aforementioned types, put
            them in a different :py:class:`collections.abc.Sequence`, like
            :py:class:`list`.

        For null :class:`Element`\ s:

        * A null complex :class:`Element` is formatted using an empty
          :py:class:`collections.abc.Mapping`.
        * A null scalar :class:`Element` is formatted using ``None``.
        * An empty array :class:`Element` is formatted using an empty
          :py:class:`collections.abc.Sequence`.

        Note:
            The behavior is undefined if :meth:`fromPy` is used to format an
            :class:`Event` that has already been formatted. Further formatting
            after :meth:`fromPy` is also undefined.

        For example, the following ``SampleOperation`` has the following BLPAPI
        representation:

        .. code-block:: none

            SampleOperation = {
                complexElement = {
                    nullElement = {
                    }
                }
                scalarArray[] = {
                    "value1", "value2"
                }
                complexArray[] = {
                    complexArray = {
                        value = 1
                        message = "msg"
                    }
                }
                valueElement = "value"
                nullValueElement =
            }

        ``SampleOperation`` can be created with the following code:

        .. code-block:: python

            response = service.createResponseEvent(CorrelationId(0))
            ef = EventFormatter(response)
            ef.appendResponse("SampleOperation")

            ef.pushElement("complexElement")
            ef.setElementNull("nullElement")
            ef.popElement()
            ef.pushElement("scalarArray")
            ef.appendValue("value1")
            ef.appendValue("value2")
            ef.popElement()
            ef.pushElement("complexArray")
            ef.appendElement()
            ef.setElement("value", 1)
            ef.setElement("message", "msg")
            ef.popElement()
            ef.popElement()
            ef.setElement("valueElement", "value")
            ef.setElementNull("nullValueElement")

        :meth:`fromPy` can be used to format ``SampleOperation`` the same way:

        .. code-block:: python

            response = service.createResponseEvent(CorrelationId(0))
            ef = EventFormatter(response)
            ef.appendResponse("SampleOperation")
            sampleResponseAsDict = {
                "complexElement": {
                    "nullElement": {
                    }
                },
                "scalarArray": [
                    "value1", "value2"
                ],
                "complexArray": [
                    {
                        "value": 1
                        "message": "msg"
                    }
                ],
                "valueElement": "value",
                "nullValueElement": None
            }
            ef.fromPy(sampleResponseAsDict)
        """

        if not isinstance(value, Mapping):
            raise Exception("`value` must be a `Mapping` instance")
        self._fromPyHelper(value)

    def _fromPyHelper(self, value, name=None, path=None):
        """
        Args:
            value (Mapping or Sequence or scalar-type): used to format the
               :class:`Element` at the current level
            name (str or blpapi.Name or None): the :class:`blpapi.Name`
                identifying the :class:`Element` to be formatted. If ``name``
                is ``None``, format the :class:`Event` at the current level.
            path (deque): represents the level at which this
                :class:`Eventformatter` is operating
        """
        if path is None:
            path = deque()

        def getPathErrorMessage():
            path.appendleft(str(self.latestMessageName))
            pathStr = "/".join(path)
            return "While operating on Element `{}`, ".format(pathStr)

        if isinstance(value, Mapping):
            for key, val in value.items():
                if isinstance(val, Mapping):
                    if val:
                        try:
                            self.pushElement(key)
                        except Exception as exc:
                            raise Exception(getPathErrorMessage()
                                            + _fromPyErrorTemplate.format(exc))

                        path.append(key)
                        self._fromPyHelper(val, name=key, path=path)
                        self.popElement()
                        path.pop()
                    else:
                        try:
                            self.setElementNull(key)
                        except (NotFoundException, Exception) as exc:
                            raise Exception(getPathErrorMessage()
                                            + _fromPyErrorTemplate.format(exc))
                else:
                    self._fromPyHelper(val, name=key, path=path)

        elif isNonScalarSequence(value):
            try:
                self.pushElement(name)
            except Exception as exc:
                raise Exception(getPathErrorMessage()
                                + _fromPyErrorTemplate.format(exc))

            for index, val in enumerate(value):
                path.append("{}[{}]".format(name, index))

                if isinstance(val, Mapping):
                    try:
                        self.appendElement()
                    except Exception as exc:
                        errorMsg = "encountered a `Mapping` where a scalar" \
                                   " value was expected. Error: {}".format(exc)
                        raise Exception(getPathErrorMessage()
                                        + errorMsg)

                    self._fromPyHelper(val, path=path)
                    self.popElement()
                elif isNonScalarSequence(val):
                    errorMsg = "encountered nested `Sequences`s. An array of" \
                               " array Elements should be represented as" \
                               " `Sequence`s of `Mappings`s with `Sequence`" \
                               " values."
                    raise Exception(getPathErrorMessage() + errorMsg)
                else:
                    try:
                        self.appendValue(val)
                    except Exception as exc:
                        raise Exception(getPathErrorMessage()
                                        + _fromPyErrorTemplate.format(exc))

                path.pop()

            self.popElement()

        else:
            try:
                if value is None:
                    self.setElementNull(name)
                else:
                    self.setElement(name, value)
            except IndexOutOfRangeException:
                path.append(name)
                errorMsg = "attempted to format an array Element using a" \
                           " scalar value. Array Elements are formatted with" \
                           " `Sequence`s."
                raise Exception(getPathErrorMessage() + errorMsg)
            except (InvalidConversionException, InvalidArgumentException) \
                    as exc:
                path.append(name)
                raise Exception(getPathErrorMessage()
                                + _fromPyErrorTemplate.format(exc))
            except Exception as exc:
                raise Exception(getPathErrorMessage()
                                + _fromPyErrorTemplate.format(exc))


_fromPyErrorTemplate = "encountered Error: {}"


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
