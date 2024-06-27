# eventformatter.py

"""Add messages to an Event for publishing

This component adds messages to an Event which can be later published.
"""

from .exception import (
    _ExceptionUtil,
    InvalidConversionException,
    IndexOutOfRangeException,
    InvalidArgumentException,
    NotFoundException,
)
from .datetime import _DatetimeUtil
from .message import Message
from .name import Name, getNamePair
from . import internals
from .utils import get_handle, invoke_if_valid, isNonScalarSequence
from .chandle import CHandle
from . import typehints  # pylint: disable=unused-import

from collections import deque
from collections.abc import Mapping
from typing import Any, Callable, Deque, Optional, Tuple, Union
from typing import Mapping as MappingType


class EventFormatter(CHandle):
    r""":class:`EventFormatter` is used to populate :class:`Event`\s for
    publishing.

    An :class:`EventFormatter` is created from an :class:`Event` obtained from
    :class:`~Service.createPublishEvent()` on :class:`Service`. Once the
    :class:`Message` or :class:`Message`\s have been appended to the
    :class:`Event` using the :class:`EventFormatter` the :class:`Event` can be
    published using :meth:`~ProviderSession.publish()` on the
    :class:`ProviderSession`.

    :class:`EventFormatter` objects cannot be copied to ensure that there is
    no ambiguity about what happens if two :class:`EventFormatter`\s are both
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
        None,
    )

    __datetimeTraits = (
        internals.blpapi_EventFormatter_setValueHighPrecisionDatetime,
        internals.blpapi_EventFormatter_appendValueHighPrecisionDatetime,
        _DatetimeUtil.convertToBlpapi,
    )

    __int32Traits = (
        internals.blpapi_EventFormatter_setValueInt32,
        internals.blpapi_EventFormatter_appendValueInt32,
        None,
    )

    __int64Traits = (
        internals.blpapi_EventFormatter_setValueInt64,
        internals.blpapi_EventFormatter_appendValueInt64,
        None,
    )

    __floatTraits = (
        internals.blpapi_EventFormatter_setValueFloat,
        internals.blpapi_EventFormatter_appendValueFloat,
        None,
    )

    # pylint: disable=protected-access
    __nameTraits = (
        internals.blpapi_EventFormatter_setValueFromName,
        internals.blpapi_EventFormatter_appendValueFromName,
        Name._handle,
    )

    __stringTraits = (
        internals.blpapi_EventFormatter_setValueString,
        internals.blpapi_EventFormatter_appendValueString,
        None,
    )

    __bytesTraits = (
        internals.blpapi_EventFormatter_setValueBytes,
        None,
        None,
    )

    __defaultTraits = (
        internals.blpapi_EventFormatter_setValueString,
        internals.blpapi_EventFormatter_appendValueString,
        str,
    )

    # pylint: disable=too-many-return-statements
    @staticmethod
    def __getTraits(
        value: Any,
    ) -> Tuple[Callable, Optional[Callable], Optional[Callable]]:
        """Returns traits for value based on its type"""
        if isinstance(value, str):
            return EventFormatter.__stringTraits
        if isinstance(value, bytes):
            return EventFormatter.__bytesTraits
        if isinstance(value, bool):
            return EventFormatter.__boolTraits
        if isinstance(value, int):
            if -(2**31) <= value <= (2**31 - 1):
                return EventFormatter.__int32Traits
            if -(2**63) <= value <= (2**63 - 1):
                return EventFormatter.__int64Traits
            raise InvalidConversionException(
                f"Value is out of supported range (INT64): {value}", 0
            )
        if isinstance(value, float):
            return EventFormatter.__floatTraits
        if _DatetimeUtil.isDatetime(value):
            return EventFormatter.__datetimeTraits
        if isinstance(value, Name):
            return EventFormatter.__nameTraits
        return EventFormatter.__defaultTraits

    def __init__(self, event: "typehints.Event") -> None:
        r"""Create an :class:`EventFormatter` to create :class:`Message`\s in
        the specified ``event``.

        Args:
            event: Event to be formatted

        An :class:`Event` may only be referenced by one :class:`EventFormatter`
        at any time.  Attempting to create a second :class:`EventFormatter`
        referencing the same :class:`Event` will result in an exception being
        raised.
        """
        selfhandle = internals.blpapi_EventFormatter_create(get_handle(event))
        super(EventFormatter, self).__init__(
            selfhandle, internals.blpapi_EventFormatter_destroy
        )
        self.__handle = selfhandle
        self.latestMessageName: Optional[Union[Name, str]] = None

    def appendMessage(
        self,
        messageType: Name,
        topic: "typehints.Topic",
        sequenceNumber: Optional[int] = None,
    ) -> None:
        """Append an (empty) message to the :class:`Event` referenced by this
        :class:`EventFormatter`

        Args:
            messageType: Type of the message
            topic: Topic to publish the message under
            sequenceNumber: Sequence number of the message

        After a message has been appended its elements can be set using the
        various :meth:`setElement()` methods.

        Note:
            It is expected that ``sequenceNumber`` is greater (unless the value
            wrapped or ``None`` is specified) than the last value used in any
            previous message on this ``topic``, otherwise the behavior is
            undefined.

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``name``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """
        name = getNamePair(messageType)

        if sequenceNumber is None:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendMessage(
                    self.__handle, name[0], name[1], get_handle(topic)
                )
            )
        else:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_EventFormatter_appendMessageSeq(
                    self.__handle,
                    name[0],
                    name[1],
                    get_handle(topic),
                    sequenceNumber,
                    0,
                )
            )

        self.latestMessageName = messageType

    def appendResponse(self, operationName: Name) -> None:
        """Append an (empty) response message for the specified
        ``operationName``.

        Args:
            operationName: Name of the operation whose response type to use

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

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``operationName``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """
        name = getNamePair(operationName)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_appendResponse(
                self.__handle, name[0], name[1]
            )
        )

        self.latestMessageName = "<Response>"

    def appendRecapMessage(
        self,
        topic: "typehints.Topic",
        correlationId: Optional["typehints.CorrelationId"] = None,
        sequenceNumber: Optional[int] = None,
        fragmentType: int = Message.FRAGMENT_NONE,
    ) -> None:
        """Append a (empty) recap message to the :class:`Event` referenced by
        this :class:`EventFormatter`.

        Args:
            topic: Topic to publish under
            correlationId: Specify if recap message
                added in response to a ``TOPIC_RECAP`` message
            sequenceNumber: Sequence number of the message
            fragmentType: Type of the message fragment

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

        cIdHandle = correlationId

        if sequenceNumber is None:
            if fragmentType == Message.FRAGMENT_NONE:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendRecapMessage(
                        self.__handle, get_handle(topic), cIdHandle
                    )
                )
            else:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendFragmentedRecapMessage(
                        self.__handle,
                        None,
                        None,
                        get_handle(topic),
                        cIdHandle,
                        fragmentType,
                    )
                )
        else:
            if fragmentType == Message.FRAGMENT_NONE:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendRecapMessageSeq(
                        self.__handle,
                        get_handle(topic),
                        cIdHandle,
                        sequenceNumber,
                        0,
                    )
                )
            else:
                _ExceptionUtil.raiseOnError(
                    internals.blpapi_EventFormatter_appendFragmentedRecapMessageSeq(
                        self.__handle,
                        None,
                        None,
                        get_handle(topic),
                        fragmentType,
                        sequenceNumber,
                    )
                )

        self.latestMessageName = "<Recap>"

    def setElement(self, name: Name, value: Any) -> None:
        """Set an element in the :class:`Event` referenced by this
        :class:`EventFormatter`.

        Args:
            name: Name of the element to set
            value (bool or str or bytes or int or float or ~datetime.datetime or Name):
                Value to set the element to

        If the ``name`` is invalid for the current message, or if
        :meth:`appendMessage()` has never been called, or if the element
        identified by ``name`` has already been set, an exception will be
        raised.

        Note:
            Clients wishing to format and publish null values (e.g. for the
            purpose of cache management) should *not* use this function; use
            :meth:`setElementNull` instead.

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``name``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """
        traits = EventFormatter.__getTraits(value)
        namepair = getNamePair(name)
        value = invoke_if_valid(traits[2], value)
        _ExceptionUtil.raiseOnError(
            traits[0](self.__handle, namepair[0], namepair[1], value)
        )

    def setElementNull(self, name: Name) -> None:
        """Create a null element with the specified ``name``.

        Args:
            name: Name of the element

        Note:
            Whether or not fields containing null values are published to
            subscribers depends on the details of the service and schema
            configuration.

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``name``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """
        namepair = getNamePair(name)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_setValueNull(
                self.__handle, namepair[0], namepair[1]
            )
        )

    def pushElement(self, name: Name) -> None:
        """Change the level at which this :class:`EventFormatter` is operating.

        Args:
            name: Name of the element that is used to determine
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

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``name``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """
        namepair = getNamePair(name)
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_pushElement(
                self.__handle, namepair[0], namepair[1]
            )
        )

    def popElement(self) -> None:
        """Undo the most recent call to :meth:`pushElement` or
        :meth:`appendElement` on this :class:`EventFormatter` and return the
        context of the :class:`EventFormatter` to where it was before the call
        to :meth:`pushElement` or :meth:`appendElement`. Once
        :meth:`popElement` has been called it is invalid to attempt to
        re-visit the same context.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_popElement(self.__handle)
        )

    def appendValue(self, value: Any) -> None:
        """
        Args:
            value (bool or str or int or float or ~datetime.datetime or Name):
                Value to append
        """
        traits = EventFormatter.__getTraits(value)
        if traits[1] is None:
            raise NotImplementedError("Arrays of bytes are not supported.")
        value = invoke_if_valid(traits[2], value)
        _ExceptionUtil.raiseOnError(traits[1](self.__handle, value))

    def appendElement(self) -> None:
        _ExceptionUtil.raiseOnError(
            internals.blpapi_EventFormatter_appendElement(self.__handle)
        )

    def fromPy(self, value: MappingType[Name, Any]) -> None:
        r"""
        Format this :class:`EventFormatter`'s underlying :class:`Event` using
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
          sub-:class:`Element`\s.
        * an array, it is formatted using a
          :py:class:`collections.abc.Sequence` of the :class:`Element`'s
          values (see note below for more details).

        Otherwise, the :class:`Element` is formatted using its associated
        scalar value (e.g. :py:class:`str` or :py:class:`int`).

        Note:
            Although :py:class:`str`, :py:class:`bytearray`, and
            :py:class:`memoryview` are sub-types of
            :py:class:`collections.abc.Sequence`, :meth:`fromPy` treats them as
            scalars of type string and will use them to format scalar
            :class:`Element`\s. If you wish to format an array
            :class:`Element` with instances of the aforementioned types, put
            them in a different :py:class:`collections.abc.Sequence`, like
            :py:class:`list`.

        Note:
            Although :py:class:`bytes` is sub-type of
            :py:class:`collections.abc.Sequence`, :meth:`fromPy` treats it as a
            scalar of type :py:class:`bytes` and will use it to format scalar
            :class:`Element`. Arrays of :py:class:`bytes` are not supported.

        For null :class:`Element`\s:

        * A null complex :class:`Element` is formatted using an empty
          :py:class:`collections.abc.Mapping`.
        * A null scalar :class:`Element` is formatted using ``None``.
        * An empty array :class:`Element` is formatted using an empty
          :py:class:`collections.abc.Sequence`.

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            MappingType key. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.

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

    def _fromPyHelper(
        self,
        value: Any,
        name: Optional[Union[Name, str]] = None,
        dpath: Optional[Deque[Union[Name, str]]] = None,
    ) -> None:
        """
        Args:
            value (Mapping or Sequence or scalar-type): used to format the
               :class:`Element` at the current level
            name: the :class:`blpapi.Name`
                identifying the :class:`Element` to be formatted. If ``name``
                is ``None``, format the :class:`Event` at the current level.
            dpath: represents the level at which this
                :class:`Eventformatter` is operating

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``name``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """
        path = deque() if dpath is None else dpath
        namestr = "" if name is None else str(name)

        def getPathErrorMessage() -> str:
            path.appendleft(str(self.latestMessageName))
            pathStr = "/".join([str(p) for p in path])
            return f"While operating on Element `{pathStr}`, "

        if isinstance(value, Mapping):
            for key, val in value.items():
                if isinstance(val, Mapping):
                    if val:
                        try:
                            self.pushElement(key)
                        except Exception as exc:
                            raise Exception(
                                getPathErrorMessage()
                                + _fromPyErrorTemplate.format(exc)
                            )

                        path.append(key)
                        self._fromPyHelper(val, name=key, dpath=path)
                        self.popElement()
                        path.pop()
                    else:
                        try:
                            self.setElementNull(key)
                        except (NotFoundException, Exception) as exc:
                            raise Exception(
                                getPathErrorMessage()
                                + _fromPyErrorTemplate.format(exc)
                            )
                else:
                    self._fromPyHelper(val, name=key, dpath=path)

        elif isNonScalarSequence(value):
            try:
                self.pushElement(Name(namestr))
            except Exception as exc:
                raise Exception(
                    getPathErrorMessage() + _fromPyErrorTemplate.format(exc)
                )

            for index, val in enumerate(value):
                path.append(f"{namestr}[{index}]")

                if isinstance(val, Mapping):
                    try:
                        self.appendElement()
                    except Exception as exc:
                        errorMsg = (
                            "encountered a `Mapping` where a scalar "
                            f"value was expected. Error: {exc}"
                        )
                        raise Exception(getPathErrorMessage() + errorMsg)

                    self._fromPyHelper(val, dpath=path)
                    self.popElement()
                elif isNonScalarSequence(val):
                    errorMsg = (
                        "encountered nested `Sequences`s. An array of"
                        " array Elements should be represented as"
                        " `Sequence`s of `Mappings`s with `Sequence`"
                        " values."
                    )
                    raise Exception(getPathErrorMessage() + errorMsg)
                else:
                    try:
                        self.appendValue(val)
                    except Exception as exc:
                        raise Exception(
                            getPathErrorMessage()
                            + _fromPyErrorTemplate.format(exc)
                        )

                path.pop()

            self.popElement()

        else:
            try:
                if value is None:
                    self.setElementNull(Name(namestr))
                else:
                    self.setElement(Name(namestr), value)
            except IndexOutOfRangeException:
                path.append(namestr)
                errorMsg = (
                    "attempted to format an array Element using a"
                    " scalar value. Array Elements are formatted with"
                    " `Sequence`s."
                )
                raise Exception(getPathErrorMessage() + errorMsg)
            except (
                InvalidConversionException,
                InvalidArgumentException,
            ) as exc:
                path.append(namestr)
                raise Exception(
                    getPathErrorMessage() + _fromPyErrorTemplate.format(exc)
                )
            except Exception as exc:
                raise Exception(
                    getPathErrorMessage() + _fromPyErrorTemplate.format(exc)
                )


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
