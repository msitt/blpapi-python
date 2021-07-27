# constant.py

"""Provide a representation for schema-level enumeration constants.

This file defines these classes:
    'Constant' - schema enumeration constant
    'ConstantList' - list of schema enumeration constants

This component provides a representation of a schema enumeration constant, and
a representation for lists of such constants
"""



from .exception import _ExceptionUtil, NotFoundException, \
    IndexOutOfRangeException
from .name import Name, getNamePair
from .datatype import DataType
from .datetime import _DatetimeUtil
from . import utils
from . import internals

# pylint: disable=protected-access

class Constant:
    """Represents the value of a schema enumeration constant.

    Constants can be any of the following :class:`DataType`\ s:
    :attr:`~DataType.BOOL`, :attr:`~DataType.CHAR`, :attr:`~DataType.BYTE`,
    :attr:`~DataType.INT32`, :attr:`~DataType.INT64`,
    :attr:`~DataType.FLOAT32`, :attr:`~DataType.FLOAT64`,
    :attr:`~DataType.STRING`, :attr:`~DataType.DATE`, :attr:`~DataType.TIME`,
    :attr:`~DataType.DATETIME`. This class provides access not only to to the
    constant value, but also to the symbolic name, the description, and the
    status of the constant.

    :class:`Constant` objects are read-only.

    Application clients never create :class:`Constant` object directly;
    applications will typically work with :class:`Constant` objects returned
    by other ``blpapi`` components.
    """

    def __init__(self, handle, sessions):
        """
        Args:
            handle: Handle to the internal implementation
            sessions: Sessions to which this object is related to
        """
        self.__handle = handle
        self.__sessions = sessions

    def name(self):
        """
        Returns:
            Name: The symbolic name of this :class:`Constant`.
        """
        return Name._createInternally(
            internals.blpapi_Constant_name(self.__handle))

    def description(self):
        """
        Returns:
            str: Human readable description of this :class:`Constant`.
        """
        return internals.blpapi_Constant_description(self.__handle)

    def status(self):
        """
        Returns:
            int: Status of this :class:`Constant`.

        The possible return values are enumerated in :class:`SchemaStatus`.
        """
        return internals.blpapi_Constant_status(self.__handle)

    def datatype(self):
        """
        Returns:
            int: Data type used to represent the value of this
            :class:`Constant`.

        The possible return values are enumerated in :class:`DataType`.
        """
        return internals.blpapi_Constant_datatype(self.__handle)

    def getValueAsInteger(self):
        """
        Returns:
            int: Value of this object as an integer.

        Raises:
            InvalidConversionException: If the value cannot be converted to an
                integer.
        """
        if self.datatype() == DataType.INT32:
            errCode, value = internals.blpapi_Constant_getValueAsInt32(
                self.__handle)
        else:
            errCode, value = internals.blpapi_Constant_getValueAsInt64(
                self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return value

    def getValueAsFloat(self):
        """
        Returns:
            float: Value of this object as a float.

        Raises:
            InvalidConversionException: If the value cannot be converted to a
                float.
        """
        if self.datatype() == DataType.FLOAT32:
            errCode, value = internals.blpapi_Constant_getValueAsFloat32(
                self.__handle)
        else:
            errCode, value = internals.blpapi_Constant_getValueAsFloat64(
                self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return value

    def getValueAsDatetime(self):
        """
        Returns:
            datetime.time or datetime.date or datetime.datetime: Value of this
            object as one of the datetime types.

        Raises:
            InvalidConversionException: If the value cannot be converted to
                one of the datetime types.
        """
        errCode, value = internals.blpapi_Constant_getValueAsDatetime(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return _DatetimeUtil.convertToNativeNotHighPrecision(value)

    def getValueAsString(self):
        """
        Returns:
            str: Value of this object as a string.

        Raises:
            InvalidConversionException: If the value cannot be converted to a
                string.
        """
        if self.datatype() == DataType.CHAR:
            errCode, value = internals.blpapi_Constant_getValueAsChar(
                self.__handle)
        else:
            errCode, value = internals.blpapi_Constant_getValueAsString(
                self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return value

    def getValue(self):
        """
        Returns:
            Value of this object as it is stored in the object.
        """
        datatype = self.datatype()
        valueGetter = _CONSTANT_VALUE_GETTER.get(
            datatype,
            Constant.getValueAsString)
        return valueGetter(self)

    def _sessions(self):
        """Return session(s) this object is related to. For internal use."""
        return self.__sessions


class ConstantList:
    """Represents a list of schema enumeration constants.

    As well as the list of :class:`Constant` objects, this class also provides
    access to the symbolic name, description and status of the list as a whole.
    All :class:`Constant` objects in a :class:`ConstantList` are of the same
    :class:`DataType`.

    :class:`ConstantList` objects are read-only.

    Application clients never create :class:`ConstantList` object directly;
    applications will typically work with :class:`ConstantList` objects
    returned by other ``blpapi`` components.
    """

    def __init__(self, handle, sessions):
        """
        Args:
            handle: Handle to the internal implementation
            sessions: Sessions to which this object is related to
        """
        self.__handle = handle
        self.__sessions = sessions

    def __iter__(self):
        """
        Returns:
            Iterator over constants contained in this :class:`ConstantList`
        """
        return utils.Iterator(self,
                              ConstantList.numConstants,
                              ConstantList.getConstantAt)

    def name(self):
        """
        Returns:
            Name: Symbolic name of this :class:`ConstantList`
        """
        return Name._createInternally(
            internals.blpapi_ConstantList_name(self.__handle))

    def description(self):
        """
        Returns:
            str: Human readable description of this :class:`ConstantList`
        """
        return internals.blpapi_ConstantList_description(self.__handle)

    def status(self):
        """
        Returns:
            int: Status of this :class:`ConstantList`

        The possible return values are enumerated in :class:`SchemaStatus`
        """
        return internals.blpapi_ConstantList_status(self.__handle)

    def numConstants(self):
        """
        Returns:
            int: Number of :class:`Constant` objects in this list
        """
        return internals.blpapi_ConstantList_numConstants(self.__handle)

    def datatype(self):
        """
        Returns:
            int: Data type used to represent the value of this constant

        The possible return values are enumerated in :class:`DataType`.
        """
        return internals.blpapi_ConstantList_datatype(self.__handle)

    def hasConstant(self, name):
        """
        Args:
            name (Name or str): Name of the constant

        Returns:
            bool: ``True`` if this :class:`ConstantList` contains an item with
            this ``name``.

        Raises:
            TypeError: If ``name`` is neither a :class:`Name` nor a string
        """
        names = getNamePair(name)
        return bool(internals.blpapi_ConstantList_hasConstant(self.__handle,
                                                              names[0],
                                                              names[1]))

    def getConstant(self, name):
        """
        Args:
            name (Name or str): Name of the constant

        Returns:
            Constant: Constant with the specified ``name``

        Raises:
            NotFoundException: If this :class:`ConstantList` does not contain a
                :class:`Constant` with the specified ``name``
        """
        names = getNamePair(name)
        res = internals.blpapi_ConstantList_getConstant(self.__handle,
                                                        names[0],
                                                        names[1])
        if res is None:
            errMessage = \
                "Constant '{0!s}' is not found in '{1!s}'.".\
                format(name, self.name())
            raise NotFoundException(errMessage, 0)
        return Constant(res, self.__sessions)

    def getConstantAt(self, position):
        """
        Args:
            position (int): Position of the requested constant in the list

        Returns:
            Constant: Constant at the specified ``position``.

        Raises:
            IndexOutOfRangeException: If ``position`` is not in the range from
                ``0`` to ``numConstants() - 1``.
        """
        res = internals.blpapi_ConstantList_getConstantAt(self.__handle,
                                                          position)
        if res is None:
            errMessage = "Index '{0}' out of bounds.".format(position)
            raise IndexOutOfRangeException(errMessage, 0)
        return Constant(res, self.__sessions)

    def _sessions(self):
        """Return session(s) this object is related to. For internal use."""
        return self.__sessions


_CONSTANT_VALUE_GETTER = {
    DataType.CHAR: Constant.getValueAsString,
    DataType.BYTE: Constant.getValueAsInteger,
    DataType.INT32: Constant.getValueAsInteger,
    DataType.INT64: Constant.getValueAsInteger,
    DataType.FLOAT32: Constant.getValueAsFloat,
    DataType.FLOAT64: Constant.getValueAsFloat,
    DataType.STRING: Constant.getValueAsString,
    DataType.DATE: Constant.getValueAsDatetime,
    DataType.TIME: Constant.getValueAsDatetime,
    DataType.DATETIME: Constant.getValueAsDatetime,
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
