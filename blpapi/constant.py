# constant.py

"""Provide a representation for schema-level enumeration constants.

This file defines these classes:
    'Constant' - schema enumeration constant
    'ConstantList' - list of schema enumeration constants

This component provides a representation of a schema enumeration constant, and
a representation for lists of such constants
"""

from __future__ import absolute_import

from .exception import _ExceptionUtil, NotFoundException, \
    IndexOutOfRangeException
from .name import Name, getNamePair
from .datatype import DataType
from .datetime import _DatetimeUtil
from . import utils
from . import internals


class Constant:
    """Represents the value of a schema enumeration constant.

    Constants can be any of the following DataTypes: BOOL, CHAR, BYTE, INT32,
    INT64, FLOAT32, FLOAT64, STRING, DATE, TIME, DATETIME. This class provides
    access not only to to the constant value, but also to the symbolic name,
    the description, and the status of the constant.

    'Constant' objects are read-only.

    Application clients never create 'Constant' object directly; applications
    will typically work with 'Constant' objects returned by other 'blpapi'
    components.
    """

    def __init__(self, handle, sessions):
        self.__handle = handle
        self.__sessions = sessions

    def name(self):
        """Return the symbolic name of this 'Constant'."""
        return Name._createInternally(
            internals.blpapi_Constant_name(self.__handle))

    def description(self):
        """Return a human readable description of this 'Constant'."""
        return internals.blpapi_Constant_description(self.__handle)

    def status(self):
        """Return the status of this 'Constant'.

        The possible return values are enumerated in 'SchemaStatus' class.
        """
        return internals.blpapi_Constant_status(self.__handle)

    def datatype(self):
        """Return the data type used to represent the value of this 'Constant'.

        The possible return values are enumerated in 'DataType' class.
        """
        return internals.blpapi_Constant_datatype(self.__handle)

    def getValueAsInteger(self):
        """Return the value of this object as an integer.

        If the value cannot be converted to an integer an exception is raised.
        """
        errCode, value = internals.blpapi_Constant_getValueAsInt64(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return value

    def getValueAsFloat(self):
        """Return the value of this object as a float.

        If the value cannot be converted to a float an exception is raised.
        """
        errCode, value = internals.blpapi_Constant_getValueAsFloat64(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return value

    def getValueAsDatetime(self):
        """Return the value of this object as one of the datetime types.

        Possible result types are: datetime.time, datetime.date or
        datetime.datetime.

        If the value cannot be converted to one of these types an exception is
        raised.
        """
        errCode, value = internals.blpapi_Constant_getValueAsDatetime(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return _DatetimeUtil.convertToNative(value)

    def getValueAsString(self):
        """Return the value of this object as a string.

        If the value cannot be converted to a string an exception is raised.
        """
        errCode, value = internals.blpapi_Constant_getValueAsString(
            self.__handle)
        _ExceptionUtil.raiseOnError(errCode)
        return value

    def getValue(self):
        """Return the value of this object as it is stored in the object."""
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

    As well as the list of 'Constant' objects, this class also provides access
    to the symbolic name, description and status of the list as a whole. All
    'Constant' objects in a 'ConstantsList' are of the same DataType.

    'ConstantList' objects are read-only.

    Application clients never create 'ConstantList' object directly;
    applications will typically work with 'ConstantList' objects returned by
    other 'blpapi' components.
    """

    def __init__(self, handle, sessions):
        self.__handle = handle
        self.__sessions = sessions

    def __iter__(self):
        """Return the iterator over constants contained in this ConstantsList.
        """
        return utils.Iterator(self,
                              ConstantList.numConstants,
                              ConstantList.getConstantAt)

    def name(self):
        """Return the symbolic name of this 'ConstantList'."""
        return Name._createInternally(
            internals.blpapi_ConstantList_name(self.__handle))

    def description(self):
        """Return a human readable description of this 'ConstantList'."""
        return internals.blpapi_ConstantList_description(self.__handle)

    def status(self):
        """Return the status of this 'ConstantList'.

        The possible return values are enumerated in 'SchemaStatus' class.
        """
        return internals.blpapi_ConstantList_status(self.__handle)

    def numConstants(self):
        """Return the number of 'Constant' objects.

        Return the number of 'Constant' objects contained in this
        'ConstantsList'.
        """
        return internals.blpapi_ConstantList_numConstants(self.__handle)

    def datatype(self):
        """Return the data type used to represent the value of this constant.

        The possible return values are enumerated in 'DataType' class.
        """
        return internals.blpapi_ConstantList_datatype(self.__handle)

    def hasConstant(self, name):
        """True if this 'ConstantList' contains an item with this 'name'.

        Returns True if this 'ConstantList' contains an item with the specified
        'name', and False otherwise.

        Exception is raised if 'name' is neither a Name nor a string.
        """
        names = getNamePair(name)
        return internals.blpapi_ConstantList_hasConstant(self.__handle,
                                                         names[0],
                                                         names[1])

    def getConstant(self, name):
        """Return the 'Constant' with the specified 'name'.

        Return the 'Constant' in this 'ConstantsList' identified by the
        specified 'name'. If this 'ConstantsList' does not contain a 'Constant'
        with the specified 'name' then an exception is raised.
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
        """Return the 'Constant' at the specified 'index'.

        Return the 'Constant' at the specified 'index' in this 'ConstantList'.
        If 'index' is not in the range from 0 to numConstants() - 1 then an
        exception is raised.
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
