# element.py

"""Provide a representation of an item in a message or request.

This file defines these classes:
    'Element' - represents an item in a message.

"""

from .exception import _ExceptionUtil
from .exception import UnsupportedOperationException
from .datetime import _DatetimeUtil
from .datatype import DataType
from .name import Name, getNamePair
from .schema import SchemaElementDefinition
from .compat import conv2str, isstr, int_typelist, Mapping
from .utils import Iterator, isNonScalarSequence
from . import internals

# pylint: disable=useless-object-inheritance,protected-access,too-many-return-statements,too-many-public-methods
class ElementIterator:
    """An iterator over the objects within an :class:`Element`.

    If the :class:`Element` is a sequence or choice, this iterates over its
    sub-:class:`Element`\ s. Otherwise, iterate over the :class:`Element`\ 's
    value(s).
    """

    def __init__(self, element):
        self._element = element
        self._index = 0

    def __next__(self):
        i = self._index
        self._index += 1

        if self._element.isComplexType():
            if self._element.numElements() > i:
                return self._element.getElement(i)
        # for array and scalar elements
        elif self._element.numValues() > i:
            return self._element.getValue(i)

        raise StopIteration()

    next = __next__ # Python 2 compatibility


class Element(object):
    """Represents an item in a message.

    An :class:`Element` can represent:

    - A single value of any data type supported by the Bloomberg API
    - An array of values
    - A sequence or a choice

    The value(s) in an :class:`Element` can be queried in a number of ways. For
    an :class:`Element` which represents a single value or an array of values
    use the :meth:`getValueAsBool()` etc. functions. For an :class:`Element`
    which represents a sequence or choice use :meth:`getElementAsBool()` etc.
    functions. In addition, for choices and sequences, :meth:`hasElement()` and
    :meth:`getElement()` are useful.

    This example shows how to access the value of a scalar element ``s`` as a
    floating point number::

        f = s.getValueAsFloat()

    Similarly, this example shows how to retrieve the third value in an array
    element ``a``, as a floating point number::

        f = a.getValueAsFloat(2)

    Use :meth:`numValues()` to determine the number of values available. For
    single values, it will return either ``0`` or ``1``. For arrays it will
    return the actual number of values in the array.

    To retrieve values from a complex element types (sequences and choices) use
    the ``getElementAs...()`` family of methods. This example shows how to get
    the value of the element ``city`` in the sequence element ``address``::

        city = address.getElementAsString("city")

    Note:
        ``getElementAsXYZ(name)`` method is a shortcut to
        ``getElement(name).getValueAsXYZ()``.

    The value(s) of an :class:`Element` can be set in a number of ways. For an
    :class:`Element` which represents a single value or an array of values use
    the :meth:`setValue()` or :meth:`appendValue()` functions. For an element
    which represents a sequence or a choice use the :meth:`setElement()`
    functions.

    This example shows how to set the value of an :class:`Element` ``s``::

        value=5
        s.setValue(value)

    This example shows how to append a value to an array element ``a``::

        value=5
        a.appendValue(value)

    To set values in a complex element (a sequence or a choice) use the
    :meth:`setElement()` family of functions. This example shows how to set the
    value of the element ``city`` in the sequence element ``address`` to a
    string::

        address.setElement("city", "New York")

    Methods which specify an :class:`Element` name accept name in two forms:
    :class:`Name` or a string. Passing :class:`Name` is more efficient.
    However, it requires the :class:`Name` to have been created in the global
    name table.

    The form which takes a string is less efficient but will not cause a new
    :class:`Name` to be created in the global name table. Because all valid
    :class:`Element` names will have already been placed in the global name
    table by the API if the supplied string cannot be found in the global name
    table the appropriate error or exception can be returned.

    The API will convert data types as long as there is no loss of precision
    involved.

    :class:`Element` objects are always created by the API, never directly by
    the application.
    """

    __boolTraits = (
        internals.blpapi_Element_setElementBool,
        internals.blpapi_Element_setValueBool,
        None)

    __datetimeTraits = (
        internals.blpapi_Element_setElementHighPrecisionDatetime,
        internals.blpapi_Element_setValueHighPrecisionDatetime,
        _DatetimeUtil.convertToBlpapi)

    __int32Traits = (
        internals.blpapi_Element_setElementInt32,
        internals.blpapi_Element_setValueInt32,
        None)

    __int64Traits = (
        internals.blpapi_Element_setElementInt64,
        internals.blpapi_Element_setValueInt64,
        None)

    __floatTraits = (
        internals.blpapi_Element_setElementFloat,
        internals.blpapi_Element_setValueFloat,
        None)

    __nameTraits = (
        internals.blpapi_Element_setElementFromName,
        internals.blpapi_Element_setValueFromName,
        Name._handle)

    __stringTraits = (
        internals.blpapi_Element_setElementString,
        internals.blpapi_Element_setValueString,
        conv2str)

    __defaultTraits = (
        internals.blpapi_Element_setElementString,
        internals.blpapi_Element_setValueString,
        str)

    @staticmethod
    def __getTraits(value):
        """ traits dispatcher """
        if isstr(value):
            return Element.__stringTraits
        if isinstance(value, bool):
            return Element.__boolTraits
        if isinstance(value, int_typelist):
            if -(2 ** 31) <= value <= (2 ** 31 - 1):
                return Element.__int32Traits
            if -(2 ** 63) <= value <= (2 ** 63 - 1):
                return Element.__int64Traits
            raise ValueError("value is out of element's supported range")
        if isinstance(value, float):
            return Element.__floatTraits
        if _DatetimeUtil.isDatetime(value):
            return Element.__datetimeTraits
        if isinstance(value, Name):
            return Element.__nameTraits
        return Element.__defaultTraits

    def __assertIsValid(self):
        if not self.isValid():
            raise RuntimeError("Element is not valid")

    def __init__(self, handle, dataHolder):
        self.__handle = handle
        self.__dataHolder = dataHolder

    def _getDataHolder(self):
        """Return the owner of underlying data. For internal use."""
        return self if self.__dataHolder is None else self.__dataHolder

    def _sessions(self):
        """Return session(s) that this 'Element' is related to.

        For internal use."""
        if self.__dataHolder is None:
            return list()
        return self.__dataHolder._sessions()

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string representation of this Element. Call of 'str(element)'
        is equivalent to 'element.toString()' called with default parameters.

        """

        return self.toString()

    def __getitem__(self, nameOrIndex):
        """
        Args:
            nameOrIndex (Name or str or int): The :class:`Name` identifying the
                :class:`Element` to retrieve from this :class:`Element`\ , or
                the index to retrieve the value from this :class:`Element`\ .

        Returns:
            If a :class:`Name` or :py:class:`str` is used, and the
            :class:`Element` whose name is ``nameOrIndex`` is a sequence,
            choice, array, or is null, that :class:`Element` is returned.
            Otherwise, if a :class:`Name` or :py:class:`str` is used, return
            the value of the :class:`Element`. If ``nameOrIndex`` is an
            :py:class:`int`, return the value at index ``nameOrIndex`` in this
            :class:`Element`.

        Raises:
            KeyError:
                If ``nameOrIndex`` is a :class:`Name` or :py:class:`str` and
                this :class:`Element` does not contain a sub-:class:`Element`
                with name ``nameOrIndex``.
            InvalidConversionException:
                If ``nameOrIndex`` is an :py:class:`int` and the data type of
                this :class:`Element` is either a sequence or a choice.
            IndexOutOfRangeException:
                If ``nameOrIndex`` is an :py:class:`int` and
                ``nameOrIndex`` >= :meth:`numValues`.
        """
        # is index
        if isinstance(nameOrIndex, int_typelist):
            return self.getValue(nameOrIndex)

        # is name
        if not self.hasElement(nameOrIndex):
            raise KeyError("Element {} does not contain element {}"
                           .format(self.name(), nameOrIndex))

        element = self.getElement(nameOrIndex)

        if element.isComplexType() or element.isArray():
            return element
        elif element.isNull():
            # Scalar element with a null value
            return None

        return element.getValue()

    def __setitem__(self, name, value):
        """
        Args:
            name (Name or str): The :class:`Name` identifying one of this
                :class:`Element`\ 's sub-:class:`Element`\ s.
            value: Used to format the :class:`Element`. See :meth:`fromPy` for
                more details.

        Raises:
            Exception:
                If ``name`` does not identify one of this :class:`Element`\ 's
                sub-:class:`Element`\ s.
            Exception:
                If the :class:`Element` identified by ``name`` is has been
                previously formatted.
            Exception:
                If the :class:`Element` identified by ``name`` cannot be
                formatted by ``value`` (See :meth:`fromPy` for more details).

        Format this :class:`Element`\ 's sub-:class:`Element` identified by
        ``name`` with ``value``. See :meth:`fromPy` for more details.

        Note:
            :class:`Element`\ s that have been previously formatted in any way
            cannot be formatted further with this method. To further format an
            :class:`Element`\ , use the get/set/append Element/Value methods.
        Note:
            :class:`Element`\ s cannot be modified by index.
        """
        if isinstance(name, int_typelist):
            raise Exception("Elements cannot be formatted by index")

        self.getElement(name).fromPy(value)

    def __iter__(self):
        """
        Returns:
            An iterator over the contents of this :class:`Element`. If this
            :class:`Element` is a complex type (see :meth:`isComplexType`),
            return an iterator over the :class:`Element`\ s in this
            :class:`Element`. Otherwise, return an iterator over this
            :class:`Element`\ 's value(s).
        """
        return ElementIterator(self)

    def __len__(self):
        """
        Returns:
            int: if this :class:`Element` is a complex type
            (see :meth:`isComplexType`), return the number of
            :class:`Element`\ s in this :class:`Element`. Otherwise, return the
            number of values in this :class:`Element`.
        """
        if self.isComplexType():
            return self.numElements()

        return self.numValues()

    def __contains__(self, item):
        """
        Args:
            item (str or blpapi.Name or bool or int or float or datetime.date \
                  or datetime.time or datetime.datetime or None):
                item to check for existence in this :class:`Element`.

        Returns:
            bool: If this :class:`Element` is a complex type, return whether
            this :class:`Element` contains an :class:`Element` with the
            specified :class:`Name` ``item``. Otherwise, return whether
            ``item`` is a value in this :class:`Element`.
        """
        if self.isComplexType():
            return self.hasElement(item)
        return item in self.values()

    def name(self):
        """
        Returns:
            Name: If this :class:`Element` is part of a sequence or choice
            :class:`Element`, then return the :class:`Name` of this
            :class:`Element` within the sequence or choice :class:`Element`
            that owns it. If this :class:`Element` is not part of a sequence
            :class:`Element` (that is it is an entire :class:`Request` or
            :class:`Message`) then return the :class:`Name` of the
            :class:`Request` or :class:`Message`.
        """

        self.__assertIsValid()
        return Name._createInternally(
            internals.blpapi_Element_name(self.__handle))

    def datatype(self):
        """
        Returns:
            int: Basic data type used to represent a value in this
            :class:`Element`.

        The possible types are enumerated in :class:`DataType`.
        """

        self.__assertIsValid()
        return internals.blpapi_Element_datatype(self.__handle)

    def isComplexType(self):
        """
        Returns:
            bool: ``True`` if ``datatype()==DataType.SEQUENCE`` or
            ``datatype()==DataType.CHOICE`` and ``False`` otherwise.
        """

        self.__assertIsValid()
        return bool(internals.blpapi_Element_isComplexType(self.__handle))

    def isArray(self):
        """
        Returns:
            bool: ``True`` if this element is an array.

        This element is an array if ``elementDefinition().maxValues()>1`` or if
        ``elementDefinition().maxValues()==UNBOUNDED``.
        """

        self.__assertIsValid()
        return bool(internals.blpapi_Element_isArray(self.__handle))

    def isValid(self):
        """
        Returns:
            bool: ``True`` if this :class:`Element` is valid.
        """
        return self.__handle is not None

    def isNull(self):
        """
        Returns:
            bool: ``True`` if this :class:`Element` has a null value.
        """
        self.__assertIsValid()
        return bool(internals.blpapi_Element_isNull(self.__handle))

    def isReadOnly(self):
        """
        Returns:
            bool: ``True`` if this :class:`Element` cannot be modified.
        """
        self.__assertIsValid()
        return bool(internals.blpapi_Element_isReadOnly(self.__handle))

    def elementDefinition(self):
        """
        Return:
            SchemaElementDefinition: Reference to the read-only element
            definition object that defines the properties of this elements
            value.
        """
        self.__assertIsValid()
        return SchemaElementDefinition(
            internals.blpapi_Element_definition(self.__handle),
            self._sessions())

    def numValues(self):
        """
        Returns:
            int: Number of values contained by this element.

        The number of values is ``0`` if :meth:`isNull()` returns ``True``, and
        no greater than ``1`` if :meth:`isComplexType()` returns ``True``. The
        value returned will always be in the range defined by
        ``elementDefinition().minValues()`` and
        ``elementDefinition().maxValues()``.
        """

        self.__assertIsValid()
        return internals.blpapi_Element_numValues(self.__handle)

    def numElements(self):
        """
        Returns:
            int: Number of elements in this element.

        The number of elements is ``0`` if :meth:`isComplexType()` returns
        ``False``, and no greater than ``1`` if the :class:`DataType` is
        :attr:`~DataType.CHOICE`; if the :class:`DataType` is
        :attr:`~DataType.SEQUENCE` this may return any number (including
        ``0``).
        """

        self.__assertIsValid()
        return internals.blpapi_Element_numElements(self.__handle)

    def isNullValue(self, position=0):
        """
        Args:
            position (int): Position of the sub-element

        Returns:
            bool: ``True`` if the value of the sub-element at the ``position``
            is a null value.

        Raises:
            Exception: If ``position >= numElements()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_isNullValue(self.__handle, position)
        if res in (0, 1):
            return bool(res)
        _ExceptionUtil.raiseOnError(res)
        return None # unreachable

    def toPy(self):
        """
        Returns:
            A :py:class:`dict`, :py:class:`list`, or value representation of
            this :class:`Element`. This is a deep copy containing only native
            python datatypes, like :py:class:`list`, :py:class:`dict`,
            :py:class:`str`, and :py:class:`int`.

        If an :class:`Element` is

        * a complex type, it is converted to a :py:class:`dict` whose keys are
          the :py:class:`str` names of its sub-:class:`Element`\ s.
        * an array, it is converted to a :py:class:`list` of the
          :class:`Element`'s values.
        * null, it is converted an empty :py:class:`dict`.

        Otherwise, the :class:`Element` is converted to its associated value.
        If that value was a :class:`Name`, it will be converted to a
        :py:class:`str`.

        For example, the following ``exampleElement`` has the following BLPAPI
        representation:

        >>> exampleElement

        .. code-block:: none

            exampleElement = {
                complexElement = {
                    nullElement = {
                    }
                }
                arrayElement[] = {
                    arrayElement = {
                        id = 2
                        endpoint = {
                            address = "127.0.0.1:8000"
                        }
                    }
                }
                valueElement = "Sample value"
                nullValueElement =
            }

        ``exampleElement`` produces the following Python representation:

        >>> exampleElement.toPy()

        .. code-block:: python

            {
                "complexElement": {
                    "nullElement": {}
                },
                "arrayElement": [
                    {
                        "id": 2
                        "endpoint": {
                            "address": "127.0.0.1:8000"
                        }
                    }
                ],
                "valueElement": "Sample value",
                "nullValueElement": None
            }

        """
        return internals.blpapi_Element_toPy(self.__handle)

    def toString(self, level=0, spacesPerLevel=4):
        """Format this :class:`Element` to the string at the specified
        indentation level.

        Args:
            level (int): Indentation level
            spacesPerLevel (int): Number of spaces per indentation level for
                this and all nested objects

        Returns:
            str: This element formatted as a string

        If ``level`` is negative, suppress indentation of the first line. If
        ``spacesPerLevel`` is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by ``level``).
        """

        self.__assertIsValid()
        return internals.blpapi_Element_printHelper(self.__handle,
                                                    level,
                                                    spacesPerLevel)

    def getElement(self, nameOrIndex):
        """
        Args:
            nameOrIndex (Name or str or int): Sub-element identifier

        Returns:
            Element: Sub-element identified by ``nameOrIndex``

        Raises:
            Exception: If ``nameOrIndex`` is a string or a :class:`Name` and
                ``hasElement(nameOrIndex) != True``, or if ``nameOrIndex`` is an
                integer and ``nameOrIndex >= numElements()``. Also if this
                :class:`Element` is neither a sequence nor a choice.
        """

        if not isinstance(nameOrIndex, int):
            self.__assertIsValid()
            name = getNamePair(nameOrIndex)
            res = internals.blpapi_Element_getElement(self.__handle,
                                                      name[0],
                                                      name[1])
            _ExceptionUtil.raiseOnError(res[0])
            return Element(res[1], self._getDataHolder())
        self.__assertIsValid()
        res = internals.blpapi_Element_getElementAt(self.__handle, nameOrIndex)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def elements(self):
        """
        Returns:
            Iterator over elements contained in this :class:`Element`.

        Raises:
            UnsupportedOperationException: If this :class:`Element` is not a
                sequence.
        """

        if self.datatype() != DataType.SEQUENCE:
            raise UnsupportedOperationException(
                description="Only sequences are supported", errorCode=None)
        return Iterator(self, Element.numElements, Element.getElement)

    def hasElement(self, name, excludeNullElements=False):
        """
        Args:
            name (Name or str): Name of the element
            excludeNullElements (bool): Whether to exclude null elements

        Returns:
            bool: ``True`` if this :class:`Element` is a choice or sequence
            (``isComplexType() == True``) and it contains an :class:`Element`
            with the specified ``name``.

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string.
        """

        self.__assertIsValid()
        name = getNamePair(name)
        res = internals.blpapi_Element_hasElementEx(
            self.__handle,
            name[0],
            name[1],
            1 if excludeNullElements else 0,
            0)
        return bool(res)

    def getChoice(self):
        """
        Returns:
            Element: The selection name of this element as :class:`Element`.

        Raises:
            Exception: If ``datatype() != DataType.CHOICE``
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getChoice(self.__handle)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def getValueAsBool(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            bool: ``index``\ th entry in the :class:`Element` as a boolean.

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` cannot be converted to a boolean.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsBool(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return bool(res[1])

    def getValueAsString(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            str: ``index``\ th entry in the :class:`Element` as a string.

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` cannot be converted to a string.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsString(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    def getValueAsDatetime(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            datetime.time or datetime.date or datetime.datetime: ``index``\ th
            entry in the :class:`Element` as one of the datetime types.

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` cannot be converted to a datetime.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsHighPrecisionDatetime(
            self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return _DatetimeUtil.convertToNative(res[1])

    def getValueAsInteger(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            int: ``index``\ th entry in the :class:`Element` as a integer

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` cannot be converted to an integer.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsInt64(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    def getValueAsFloat(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            float: ``index``\ th entry in the :class:`Element` as a float.

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` cannot be converted to an float.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsFloat64(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    def getValueAsName(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            Name: ``index``\ th entry in the :class:`Element` as a Name.

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` cannot be converted to a :class:`Name`.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsName(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return Name._createInternally(res[1])

    def getValueAsElement(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            Element: ``index``\ th entry in the :class:`Element` as a Element.

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` cannot be converted to an :class:`Element`.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsElement(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def getValue(self, index=0):
        """
        Args:
            index (int): Index of the value in the element

        Returns:
            ``index``\ th entry in the :class:`Element` defined by this
            element's datatype.

        Raises:
            InvalidConversionException: If the data type of this
                :class:`Element` is either a sequence or a choice.
            IndexOutOfRangeException: If ``index >= numValues()``.
        """

        datatype = self.datatype()
        valueGetter = _ELEMENT_VALUE_GETTER.get(datatype,
                                                Element.getValueAsString)
        return valueGetter(self, index)

    def values(self):
        """
        Returns:
            Iterator over values contained in this :class:`Element`.

        If :meth:`isComplexType()` returns ``True`` for this :class:`Element`,
        the empty iterator is returned.
        """

        if self.isComplexType():
            return iter(())  # empty tuple
        datatype = self.datatype()
        valueGetter = _ELEMENT_VALUE_GETTER.get(datatype,
                                                Element.getValueAsString)
        return Iterator(self, Element.numValues, valueGetter)

    def getElementAsBool(self, name):
        """
        Args:
            name (Name or str): Sub-element identifier

        Returns:
            bool: This element's sub-element with ``name`` as a boolean

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this :class:`Element` is neither a sequence nor a choice, or
                in case it has no sub-element with the specified ``name``, or
                in case the element's value can't be returned as a boolean.
        """

        return self.getElement(name).getValueAsBool()

    def getElementAsString(self, name):
        """
        Args:
            name (Name or str): Sub-element identifier

        Returns:
            str: This element's sub-element with ``name`` as a string

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this :class:`Element` is neither a sequence nor a choice, or
                in case it has no sub-element with the specified ``name``, or
                in case the element's value can't be returned as a string.
        """

        return self.getElement(name).getValueAsString()

    def getElementAsDatetime(self, name):
        """
        Args:
            name (Name or str): Sub-element identifier

        Returns:
            datetime.time or datetime.date or datetime.datetime: This element's
            sub-element with ``name`` as one of the datetime types

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this :class:`Element` is neither a sequence nor a choice, or
                in case it has no sub-element with the specified ``name``, or
                in case the element's value can't be returned as a datetime.
        """

        return self.getElement(name).getValueAsDatetime()

    def getElementAsInteger(self, name):
        """
        Args:
            name (Name or str): Sub-element identifier

        Returns:
            int: This element's sub-element with ``name`` as an integer

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this :class:`Element` is neither a sequence nor a choice, or
                in case it has no sub-element with the specified ``name``, or
                in case the element's value can't be returned as an integer.
        """

        return self.getElement(name).getValueAsInteger()

    def getElementAsFloat(self, name):
        """
        Args:
            name (Name or str): Sub-element identifier

        Returns:
            float: This element's sub-element with ``name`` as a float

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this :class:`Element` is neither a sequence nor a choice, or
                in case it has no sub-element with the specified ``name``, or
                in case the element's value can't be returned as a float.
        """

        return self.getElement(name).getValueAsFloat()

    def getElementAsName(self, name):
        """
        Args:
            name (Name or str): Sub-element identifier

        Returns:
            Name: This element's sub-element with ``name`` as a :class:`Name`

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this :class:`Element` is neither a sequence nor a choice, or
                in case it has no sub-element with the specified ``name``, or
                in case the element's value can't be returned as a
                :class:`Name`.
        """

        return self.getElement(name).getValueAsName()

    def getElementValue(self, name):
        """
        Args:
            name (Name or str): Sub-element identifier

        Returns:
            This element's sub-element with ``name`` defined by its datatype

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this :class:`Element` is neither a sequence nor a choice, or
                in case it has no sub-element with the specified ``name``.
        """

        return self.getElement(name).getValue()

    def setElement(self, name, value):
        """Set this Element's sub-element with 'name' to the specified 'value'.

        Args:
            name (Name or str): Sub-element identifier
            value: Value to set the sub-element to

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string, or
                if this element has no sub-element with the specified ``name``,
                or if the :class:`Element` identified by the specified ``name``
                cannot be initialized from the type of the specified ``value``.

        This method can process the following types of ``value`` without
        conversion:

        - boolean
        - integers
        - float
        - string
        - datetypes (``datetime.time``, ``datetime.date`` or
          ``datetime.datetime``)
        - :class:`Name`

        Any other ``value`` will be converted to a string with ``str`` function
        and then processed in the same way as string ``value``.
        """

        self.__assertIsValid()

        traits = Element.__getTraits(value)
        name = getNamePair(name)
        if traits[2] is not None:
            value = traits[2](value)
        _ExceptionUtil.raiseOnError(
            traits[0](self.__handle, name[0], name[1], value))

    def setValue(self, value, index=0):
        """Set the specified ``index``\ th entry in this :class:`Element` to
        the ``value``.

        Args:
            index (int): Index of the sub-element
            value: Value to set the sub-element to

        Raises:
            Exception: If this :class:`Element`\ 's datatype can't be
                initialized with the type of the specified ``value``, or if
                ``index >= numValues()``.

        This method can process the following types of ``value`` without
        conversion:

        - boolean
        - integers
        - float
        - string
        - datetypes (``datetime.time``, ``datetime.date`` or
          ``datetime.datetime``)
        - :class:`Name`

        Any other ``value`` will be converted to a string with ``str`` function
        and then processed in the same way as string ``value``.
        """

        self.__assertIsValid()
        traits = Element.__getTraits(value)
        if traits[2] is not None:
            value = traits[2](value)
        _ExceptionUtil.raiseOnError(traits[1](self.__handle, value, index))

    def appendValue(self, value):
        """Append the specified ``value`` to this :class:`Element`\ s entries
        at the end.

        Args:
            value: Value to append

        Raises:
            Exception: If this :class:`Element`\ 's datatype can't be
                initialized from the type of the specified ``value``, or if the
                current size of this :class:`Element` (:meth:`numValues()`) is
                equal to the maximum defined by
                ``elementDefinition().maxValues()``.

        This method can process the following types of ``value`` without
        conversion:

        - boolean
        - integers
        - float
        - string
        - datetypes (``datetime.time``, ``datetime.date`` or
          ``datetime.datetime``)
        - :class:`Name`

        Any other ``value`` will be converted to a string with ``str`` function
        and then processed in the same way as string ``value``.
        """

        self.setValue(value, internals.ELEMENT_INDEX_END)

    def appendElement(self):
        """Append a new element to this array :class:`Element`.

        Returns:
            Element: The newly appended element

        Raises:
            Exception: If this :class:`Element` is not an array of sequence or
                choice :class:`Element`\ s.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_appendElement(self.__handle)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def setChoice(self, selectionName):
        """Set this :class:`Element`\ 's active element to ``selectionName``.

        Args:
            selectionName (Name or str): Name of the element to set the active
                choice

        Returns:
            Element: The newly active element

        Raises:
            Exception: If ``selectionName`` is neither a :class:`Name` nor a
                string, or if this :class:`Element` is not a choice.
        """

        self.__assertIsValid()
        name = getNamePair(selectionName)
        res = internals.blpapi_Element_setChoice(self.__handle,
                                                 name[0],
                                                 name[1],
                                                 0)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def fromPy(self, value):
        """Format this :class:`Element` with the provided native Python value.

        Args:
            value: Used to format this :class:`Element`

        Raises:
            Exception:
                If the provided value does not properly represent the structure
                of this :class:`Element`.
            Exception:
                If this method is used to format an :class:`Element` that has
                already been formatted.

        If the :class:`Element` is

        * a complex type, it is formatted using a
          :py:class:`collections.abc.Mapping` (e.g. :py:class:`dict`) whose
          keys are the :py:class:`str` names of its sub-:class:`Element`\ s.
        * an array, it is formatted using a
          :py:class:`collections.abc.Sequence` (e.g. :py:class:`list`) of the
          :class:`Element`\ 's values (see note below for more detais).
        * null, it is formatted using an empty
          :py:class:`collections.abc.Mapping`.

        Otherwise, the :class:`Element` is formatted using its associated
        value (e.g :py:class:`str` or :py:class:`int`).

        Note:
            Although :py:class:`str`, :py:class:`bytes`, :py:class:`bytearray`,
            and :py:class:`memoryview` are sub-types of
            :py:class:`collections.abc.Sequence`, :meth:`fromPy` treats them as
            scalars of type string and will use them to format scalar
            :class:`Element`\ s. If you wish to format an array
            :class:`Element` with instances of the aforementioned types, put
            them in a different :py:class:`collections.abc.Sequence`, like
            :py:class:`list`.

        Note:
            Using :meth:`fromPy` to format an :class:`Element` or one of its
            sub-:class:`Element`\ s that has already been formatted is not
            supported. To further format an :class:`Element`, use the
            get/set/append Element/Value methods.

        For example, the following ``exampleElement`` has the following BLPAPI
        representation:

        .. code-block:: none

            exampleElement = {
                complexElement = {
                    nullElement = {
                    }
                }
                arrayElement[] = {
                    arrayElement = {
                        id = 2
                        endpoint = {
                            address = "127.0.0.1:8000"
                        }
                    }
                }
                valueElement = "Sample value"
                nullValueElement =
            }

        ``exampleElement`` can be created with the following code:

        .. code-block:: python

            exampleRequest = service.createRequest("ExampleRequest")
            exampleElement = exampleRequest.asElement()

            complexElement = exampleElement.getElement("complexElement")
            complexElement.getElement("nullElement")

            arrayElement = exampleElement.getElement("arrayElement")
            array = arrayElement.appendElement()
            arrayValue.setElement("id", 2)
            endpointElement = arrayValue.getElement("endpoint")
            endpointElement.setElement("address", "127.0.0.1:8000")

            exampleElement.setElement("valueElement", "Sample value")

        :meth:`fromPy` can be used to format ``exampleElement`` the same way:

        .. code-block:: python

            exampleRequest = service.createRequest("ExampleRequest")
            exampleElement = exampleRequest.asElement()
            exampleElementAsDict = {
                "complexElement": {
                    "nullElement": {}
                },
                "arrayElement": [
                    {
                        "id": 2,
                        "endpoint": {
                            "address": "127.0.0.1:8000"
                        }
                    }
                ],
                "valueElement": "Sample value",
                "nullValueElement": None
            }
            exampleElement.fromPy(exampleElementAsDict)

        :meth:`fromPy` can also be called with
        :class:`collections.abc.Sequence`\ s and scalar values to format array
        :class:`Element`\ s and scalar :class:`Element`\ s, respectively.

        .. code-block:: python

            arrayElementAsList = [{
                    "id": 2,
                    "endpoint": { "address": "127.0.0.1:8000" }
            }]
            arrayElement = exampleElement.getElement("arrayElement")
            arrayElement.fromPy(arrayElementAsList)

            exampleElement.getElement("valueElement").fromPy("Sample value")

        Calling :meth:`toPy` on an :class:`Element` formatted by :meth:`fromPy`
        with a given value will return an equal value. Continuing from the
        preceding example:

        .. code-block:: python

            exampleElement.fromPy(exampleElementAsDict)
            print(exampleElementAsDict == exampleElement.toPy()) # True

        """
        self._fromPyHelper(value)

    def _fromPyHelper(self, value, name=None, path=None):
        """Helper method for `fromPy`.

        Args:
            value: Used to format this `Element` or the `Element` specified
                by ``name``.
            name (Name or str): If ``name`` is ``None``, format this `Element`
                with ``value``. Otherwise, ``name`` refers to this `Element`'s
                sub-`Element` that will be formatted with ``value``.
            path (str): The path uniquely identifying this `Element`, starting
                from the root `Element`.
        """
        # Note, the double exception throwing has no good solution in Python 2,
        # but Python 3 has exception chaining that we should use when we can

        activeElement = self

        def getActivePathMessage(isArrayEntry=False):
            elementType = "scalar"
            if activeElement.isArray():
                elementType = "array"
            elif activeElement.isComplexType():
                elementType = "complex"

            arrayEntryText = "an entry in " if isArrayEntry else ""
            return "While operating on {}{} Element `{}`, ".format(
                    arrayEntryText, elementType, path)

        if path is None:
            path = str(activeElement.name())
        if name is not None:
            try:
                activeElement = self.getElement(name)
                path += "/" + str(activeElement.name())
            except Exception as exc:
                errorMsg = "encountered error: {}".format(exc)
                raise Exception(getActivePathMessage() + errorMsg)

        if activeElement.numElements() or activeElement.numValues():
            errorMsg = "this Element has already been formatted"
            raise Exception(getActivePathMessage() + errorMsg)

        if isinstance(value, Mapping):
            if not activeElement.isComplexType():
                errorMsg = "encountered a `Mapping` instance while" \
                           " formatting a non-complex Element"
                raise Exception(getActivePathMessage() + errorMsg)

            complexElement = activeElement
            for subName in value:
                subValue = value[subName]
                complexElement._fromPyHelper(subValue, subName, path)

        elif isNonScalarSequence(value):
            if not activeElement.isArray():
                errorMsg = "encountered a `Sequence` while formatting a" \
                           " non-array Element"
                raise Exception(getActivePathMessage() + errorMsg)

            arrayElement = activeElement
            typeDef = arrayElement.elementDefinition().typeDefinition()
            arrayValuesAreScalar = not typeDef.isComplexType()
            for index, val in enumerate(value):
                if isinstance(val, Mapping):
                    if arrayValuesAreScalar:
                        path += "[{}]".format(index)
                        errorMsg = "encountered a `Mapping` where a scalar" \
                                   " value was expected."
                        raise Exception(getActivePathMessage(isArrayEntry=True)
                                        + errorMsg)

                    appendedElement = arrayElement.appendElement()
                    arrayEntryPath = path + "[{}]".format(index)
                    appendedElement._fromPyHelper(val, path=arrayEntryPath)
                elif isNonScalarSequence(val):
                    path += "[{}]".format(index)
                    expectedObject = "scalar value" if arrayValuesAreScalar \
                        else "`Mapping`"
                    errorMsg = "encountered a nested `Sequence` where a {}" \
                               " was expected.".format(expectedObject)
                    raise Exception(getActivePathMessage(isArrayEntry=True)
                                    + errorMsg)

                else:
                    if not arrayValuesAreScalar:
                        path += "[{}]".format(index)
                        errorMsg = "encountered a scalar value where a" \
                                   " `Mapping` was expected."
                        raise Exception(getActivePathMessage(isArrayEntry=True)
                                        + errorMsg)

                    try:
                        arrayElement.appendValue(val)
                    except Exception as exc:
                        path += "[{}]".format(index)
                        errorMsg = "encountered error: {}".format(exc)
                        raise Exception(getActivePathMessage(isArrayEntry=True)
                                        + errorMsg)
        else:
            if value is None:
                return

            if activeElement.isComplexType() or activeElement.isArray():
                errorMsg = "encountered an incompatible type, {}, for a" \
                           " non-scalar Element".format(type(value))
                raise Exception(getActivePathMessage() + errorMsg)

            try:
                activeElement.setValue(value)
            except Exception as exc:
                errorMsg = "encountered error: {}".format(exc)
                raise Exception(getActivePathMessage() + errorMsg)

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle


_ELEMENT_VALUE_GETTER = {
    DataType.BOOL: Element.getValueAsBool,
    DataType.CHAR: Element.getValueAsString,
    DataType.BYTE: Element.getValueAsInteger,
    DataType.INT32: Element.getValueAsInteger,
    DataType.INT64: Element.getValueAsInteger,
    DataType.FLOAT32: Element.getValueAsFloat,
    DataType.FLOAT64: Element.getValueAsFloat,
    DataType.STRING: Element.getValueAsString,
    DataType.DATE: Element.getValueAsDatetime,
    DataType.TIME: Element.getValueAsDatetime,
    DataType.DATETIME: Element.getValueAsDatetime,
    DataType.ENUMERATION: Element.getValueAsName,
    DataType.SEQUENCE: Element.getValueAsElement,
    DataType.CHOICE: Element.getValueAsElement
}

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
