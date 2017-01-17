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
from .compat import conv2str, isstr, int_typelist
from . import utils
from . import internals

import sys


class Element(object):
    """Element represents an item in a message.

    An Element can represent: a single value of any data type supported by the
    Bloomberg API; an array of values; a sequence or a choice.

    The value(s) in an Element can be queried in a number of ways. For an
    Element which represents a single value or an array of values use the
    'getValueAs()' functions or 'getValueAsBool()' etc. For an Element which
    represents a sequence or choice use 'getElementAsBool()' etc. In addition,
    for choices and sequences, 'hasElement()' and 'getElement()' are useful.

    This example shows how to access the value of a scalar element 's' as a
    floating point number:

         f = s.getValueAsFloat()

    Similarly, this example shows how to retrieve the third value in an array
    element 'a', as a floating point number:

         f = a.getValueAsFloat(2)

    Use 'numValues()' to determine the number of values available. For single
    values, it will return either 0 or 1. For arrays it will return the actual
    number of values in the array.

    To retrieve values from a complex element types (sequnces and choices) use
    the 'getElementAs...()' family of methods. This example shows how to get the
    value of the the element 'city' in the sequence element 'address':

         city = address.getElementAsString("city")

    Note that 'getElementAsXYZ(name)' method is a shortcut to
    'getElement(name).getValueAsXYZ()'.

    The value(s) of an Element can be set in a number of ways. For an Element
    which represents a single value or an array of values use the 'setValue()' or
    'appendValue()' functions. For an element which represents a seqeunce or a
    choice use the 'setElement()' functions.

    This example shows how to set the value of an Element 's':

         value=5
         s.setValue(value)

    This example shows how to append a value to an array element 'a':

         value=5;
         s.appendValue(value);

    To set values in a complex element (a sequence or a choice) use the
    'setElement()' family of functions. This example shows how to set the value
    of the element 'city' in the sequence element 'address' to a string.

         address.setElement("city", "New York")

    Methods which specify an Element name accept name in two forms: 'blpapi.Name'
    or a string. Passing 'blpapi.Name' is more efficient. However, it requires
    the Name to have been created in the global name table.

    The form which takes a string is less efficient but will not cause a new
    Name to be created in the global Name table. Because all valid Element
    names will have already been placed in the global name table by the API if
    the supplied string cannot be found in the global name table the
    appropriate error or exception can be returned.

    The API will convert data types as long as there is no loss of precision
    involved.

    Element objects are always created by the API, never directly by the
    application.

    """

    __boolTraits = (
        internals.blpapi_Element_setElementBool,
        internals.blpapi_Element_setValueBool,
        None)

    __datetimeTraits = (
        internals.blpapi_Element_setElementDatetime,
        internals.blpapi_Element_setValueDatetime,
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
        if isstr(value):
            return Element.__stringTraits
        elif isinstance(value, bool):
            return Element.__boolTraits
        elif isinstance(value, int_typelist):
            if value >= -(2 ** 31) and value <= (2 ** 31 - 1):
                return Element.__int32Traits
            elif value >= -(2 ** 63) and value <= (2 ** 63 - 1):
                return Element.__int64Traits
            else:
                raise ValueError("value is out of element's supported range")
        elif isinstance(value, float):
            return Element.__floatTraits
        elif _DatetimeUtil.isDatetime(value):
            return Element.__datetimeTraits
        elif isinstance(value, Name):
            return Element.__nameTraits
        else:
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
        else:
            return self.__dataHolder._sessions()

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string representation of this Element. Call of 'str(element)' is
        equivalent to 'element.toString()' called with default parameters.

        """

        return self.toString()

    def name(self):
        """Return the name of this Element.

        If this Element is part of a sequence or choice Element then return the
        Name of this Element within the sequence or choice Element that owns
        it. If this Element is not part of a sequence Element (that is it is an
        entire Request or Message) then return the Name of the Request or
        Message.

        """

        self.__assertIsValid()
        return Name._createInternally(
            internals.blpapi_Element_name(self.__handle))

    def datatype(self):
        """Return the basic data type of this Element.

        Return the basic data type used to represent a value in this Element.

        The possible return values are enumerated in DataType class.

        """

        self.__assertIsValid()
        return internals.blpapi_Element_datatype(self.__handle)

    def isComplexType(self):
        """Return True is this Element is a SEQUENCE or CHOICE.

        Return True if 'datatype()==DataType.SEQUENCE' or
        'datatype()==DataType.CHOICE' and False otherwise.

        """

        self.__assertIsValid()
        return bool(internals.blpapi_Element_isComplexType(self.__handle))

    def isArray(self):
        """Return True is this element is an array.

        Return True if 'elementDefinition().maxValues()>1' or if
        'elementDefinition().maxValues()==UNBOUNDED', and False otherwise.

        """

        self.__assertIsValid()
        return bool(internals.blpapi_Element_isArray(self.__handle))

    def isValid(self):
        """Return True if this Element is valid."""
        return self.__handle is not None

    def isNull(self):
        """Return True if this Element has a null value."""
        self.__assertIsValid()
        return bool(internals.blpapi_Element_isNull(self.__handle))

    def isReadOnly(self):
        """Return True if this element cannot be modified."""
        self.__assertIsValid()
        return bool(internals.blpapi_Element_isReadOnly(self.__handle))

    def elementDefinition(self):
        """Return a read-only SchemaElementDefinition for this Element.

        Return a reference to the read-only element definition object that
        defines the properties of this elements value.

        """
        self.__assertIsValid()
        return SchemaElementDefinition(
            internals.blpapi_Element_definition(self.__handle),
            self._sessions())

    def numValues(self):
        """Return the number of values contained by this element.

        Return the number of values contained by this element. The number of
        values is 0 if 'isNull()' returns True, and no greater than 1 if
        'isComplexType()' returns True. The value returned will always be in
        the range defined by 'elementDefinition().minValues()' and
        'elementDefinition().maxValues()'.

        """

        self.__assertIsValid()
        return internals.blpapi_Element_numValues(self.__handle)

    def numElements(self):
        """Return the number of elements in this Element.

        Return the number of elements contained by this element.  The number
        of elements is 0 if 'isComplex()' returns False, and no greater than
        1 if the Datatype is CHOICE; if the DataType is SEQUENCE this may
        return any number (including 0).

        """

        self.__assertIsValid()
        return internals.blpapi_Element_numElements(self.__handle)

    def isNullValue(self, position=0):
        """Return True if the value at the 'position' is a null value.

        Return True if the value of the sub-element at the specified 'position'
        in a sequence or choice element is a null value. An exception is raised
        if 'position >= numElements()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_isNullValue(self.__handle, position)
        if res == 0 or res == 1:
            return bool(res)
        _ExceptionUtil.raiseOnError(res)

    def toString(self, level=0, spacesPerLevel=4):
        """Format this Element to the string.

        Format this Element to the string at the specified indentation level.

        You could optionally specify 'spacesPerLevel' - the number of spaces
        per indentation level for this and all of its nested objects. If
        'level' is negative, suppress indentation of the first line. If
        'spacesPerLevel' is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by 'level').

        """

        self.__assertIsValid()
        return internals.blpapi_Element_printHelper(self.__handle,
                                                    level,
                                                    spacesPerLevel)

    def getElement(self, nameOrIndex):
        """Return a specified subelement.

        Return a subelement identified by the specified 'nameOrIndex', which
        must be either a string, a Name, or an integer. If 'nameOrIndex' is a
        string or a Name and 'hasElement(nameOrIndex) != True', or if
        'nameOrIndex' is an integer and 'nameOrIndex >= numElements()', then
        an exception is raised.

        An exception is also raised if this Element is neither a sequence nor
        a choice.

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
        """Return an iterator over elements contained in this Element.

        An exception is raised if this 'Element' is not a sequence.
        """

        if (self.datatype() != DataType.SEQUENCE):
            raise UnsupportedOperationException()
        return utils.Iterator(self, Element.numElements, Element.getElement)

    def hasElement(self, name, excludeNullElements=False):
        """Return True if this Element contains sub-element with this 'name'.

        Return True if this Element is a choice or sequence ('isComplexType()
        == True') and it contains an Element with the specified 'name'.

        Exception is raised if 'name' is neither a Name nor a string.

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
        """Return the selection name of this element as Element.

        Return the selection name of this element if 
        'datatype() == DataType.CHOICE'; otherwise, an exception is raised.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getChoice(self.__handle)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def getValueAsBool(self, index=0):
        """Return the specified 'index'th entry in the Element as a boolean.

        An exception is raised if the data type of this Element cannot be
        converted to a boolean or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsBool(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return bool(res[1])

    def getValueAsString(self, index=0):
        """Return the specified 'index'th entry in the Element as a string.

        An exception is raised if the data type of this Element cannot be
        converted to a string or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsString(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    def getValueAsDatetime(self, index=0):
        """Return the specified 'index'th entry as one of the datetime types.

        The possible result types are 'datetime.time', 'datetime.date' or
        'datetime.datetime'.

        An exception is raised if the data type of this Element cannot be
        converted to one of these types or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsDatetime(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return _DatetimeUtil.convertToNative(res[1])

    def getValueAsInteger(self, index=0):
        """Return the specified 'index'th entry in the Element as an integer.

        An exception is raised if the data type of this Element cannot be
        converted to an integer or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsInt64(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    def getValueAsFloat(self, index=0):
        """Return the specified 'index'th entry in the Element as a float.

        An exception is raised if the data type of this Element cannot be
        converted to a float or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsFloat64(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    def getValueAsName(self, index=0):
        """Return the specified 'index'th entry in the Element as a Name.

        An exception is raised if the data type of this Element cannot be
        converted to a Name or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsName(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return Name._createInternally(res[1])

    def getValueAsElement(self, index=0):
        """Return the specified 'index'th entry in the Element as an Element.

        An exception is raised if the data type of this Element cannot be
        converted to an Element or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_getValueAsElement(self.__handle, index)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def getValue(self, index=0):
        """Return the specified 'index'th entry in the Element.

        Return the specified 'index'th entry in the Element in the format
        defined by this Element datatype.

        An exception is raised if this Element either a sequence or a choice or
        if 'index >= numValues()'.

        """

        datatype = self.datatype()
        valueGetter = _ELEMENT_VALUE_GETTER.get(datatype,
                                                Element.getValueAsString)
        return valueGetter(self, index)

    def values(self):
        """Return an iterator over values contained in this Element.

        If 'isComplexType()' returns True for this Element, the empty iterator is
        returned.

        """

        if self.isComplexType():
            return iter(())  # empty tuple
        datatype = self.datatype()
        valueGetter = _ELEMENT_VALUE_GETTER.get(datatype,
                                                Element.getValueAsString)
        return utils.Iterator(self, Element.numValues, valueGetter)

    def getElementAsBool(self, name):
        """Return this Element's sub-element with 'name' as a boolean.

        Exception is raised if 'name' is neither a Name nor a string, or if
        this Element is neither a sequence nor a choice, or in case it has no
        sub-element with the specified 'name', or in case the Element's value
        can't be returned as a boolean.

        """

        return self.getElement(name).getValueAsBool()

    def getElementAsString(self, name):
        """Return this Element's sub-element with 'name' as a string.

        Exception is raised if 'name' is neither a Name nor a string, or if
        this Element is neither a sequence nor a choice, or in case it has no
        sub-element with the specified 'name', or in case the Element's value
        can't be returned as a string.

        """

        return self.getElement(name).getValueAsString()

    def getElementAsDatetime(self, name):
        """Return this Element's sub-element with 'name' as a datetime type.

        The possible result types are datetime.time, datetime.date or
        datetime.datetime.

        Exception is raised if 'name' is neither a Name nor a string, or if
        this Element is neither a sequence nor a choice, or in case it has no
        sub-element with the specified 'name', or in case the Element's value
        can't be returned as one of datetype types.

        """

        return self.getElement(name).getValueAsDatetime()

    def getElementAsInteger(self, name):
        """Return this Element's sub-element with 'name' as an integer.

        Exception is raised if 'name' is neither a Name nor a string, or if
        this Element is neither a sequence nor a choice, or in case it has no
        sub-element with the specified 'name', or in case the Element's value
        can't be returned as an integer.

        """

        return self.getElement(name).getValueAsInteger()

    def getElementAsFloat(self, name):
        """Return this Element's sub-element with 'name' as a float.

        Exception is raised if 'name' is neither a Name nor a string, or if
        this Element is neither a sequence nor a choice, or in case it has no
        sub-element with the specified 'name', or in case the Element's value
        can't be returned as a float.

        """

        return self.getElement(name).getValueAsFloat()

    def getElementAsName(self, name):
        """Return this Element's sub-element with 'name' as a Name.

        Exception is raised if 'name' is neither a Name nor a string, or if
        this Element is neither a sequence nor a choice, or in case it has no
        sub-element with the specified 'name', or in case the Element's value
        can't be returned as a Name.

        """

        return self.getElement(name).getValueAsName()

    def getElementValue(self, name):
        """Return this Element's sub-element with 'name'.

        The value is returned in the format defined by this Element datatype.

        Exception is raised if 'name' is neither a Name nor a string, or if
        this Element is neither a sequence nor a choice, or in case it has no
        sub-element with the specified 'name'.

        """

        return self.getElement(name).getValue()

    def setElement(self, name, value):
        """Set this Element's sub-element with 'name' to the specified 'value'.

        This method can process the following types of 'value' without
        conversion:

        - boolean
        - integers
        - float
        - string
        - datetypes ('datetime.time', 'datetime.date' or 'datetime.datetime')
        - Name

        Any other 'value' will be converted to a string with 'str' function and
        then processed in the same way as string 'value'.

        An exception is raised if 'name' is neither a Name nor a string, or if
        this element has no sub-elemen with the specified 'name', or if the
        Element identified by the specified 'name' cannot be initialized from
        the type of the specified 'value'.

        """

        self.__assertIsValid()

        traits = Element.__getTraits(value)
        name = getNamePair(name)
        if traits[2] is not None:
            value = traits[2](value)
        _ExceptionUtil.raiseOnError(
            traits[0](self.__handle, name[0], name[1], value))

    def setValue(self, value, index=0):
        """Set the specified 'index'th entry in this Element to the 'value'.

        This method can process the following types of 'value' without
        conversion:

        - boolean
        - integers
        - float
        - string
        - datetypes ('datetime.time', 'datetime.date' or 'datetime.datetime')
        - Name

        Any other 'value' will be converted to a string with 'str' function and
        then processed in the same way as string 'value'.

        An exception is raised if this Element's datatype can't be initialized
        with the type of the specified 'value', or if 'index >= numValues()'.

        """

        self.__assertIsValid()
        traits = Element.__getTraits(value)
        if traits[2] is not None:
            value = traits[2](value)
        _ExceptionUtil.raiseOnError(traits[1](self.__handle, value, index))

    def appendValue(self, value):
        """Append the specified 'value' to this Element's entries at the end.

        This method can process the following types of 'value' without
        conversion:

        - boolean
        - integers
        - float
        - string
        - datetypes ('datetime.time', 'datetime.date' or 'datetime.datetime')
        - Name

        Any other 'value' will be converted to a string with 'str' function and
        then processed in the same way as string 'value'.

        An exception is raised if this Element's datatype can't be initialized
        from the type of the specified 'value', or if the current size of this
        Element ('numValues()') is equal to the maximum defined by
        'elementDefinition().maxValues()'.

        """

        self.setValue(value, internals.ELEMENT_INDEX_END)

    def appendElement(self):
        """Append a new element to this array Element, return the new Element.

        An exception is raised if this Element is not an array of sequence or
        choice Elements.

        """

        self.__assertIsValid()
        res = internals.blpapi_Element_appendElement(self.__handle)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

    def setChoice(self, selectionName):
        """Set this Element's active Element to 'selectionName'.

        Exception is raised if 'selectionName' is neither a Name nor a string,
        or if this Element is not a choice.

        """

        self.__assertIsValid()
        name = getNamePair(selectionName)
        res = internals.blpapi_Element_setChoice(self.__handle,
                                                 name[0],
                                                 name[1],
                                                 0)
        _ExceptionUtil.raiseOnError(res[0])
        return Element(res[1], self._getDataHolder())

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
