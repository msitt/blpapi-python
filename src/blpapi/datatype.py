# datatype.py

"""Provide "enum" representing all possible data types in an Element.

This file defines these classes:
    'DataType' - "enum" representing all possible data types in an Element.
"""

from . import internals
from . import utils


# pylint: disable=too-few-public-methods
class DataType(metaclass=utils.MetaClassForClassesWithEnums):
    """Contains the possible data types which can be represented in an
    :class:`Element`.
    """

    BOOL = internals.DATATYPE_BOOL # type: ignore
    """Boolean"""
    CHAR = internals.DATATYPE_CHAR # type: ignore
    """Char"""
    BYTE = internals.DATATYPE_BYTE # type: ignore
    """Unsigned 8 bit value"""
    INT32 = internals.DATATYPE_INT32 # type: ignore
    """32 bit Integer"""
    INT64 = internals.DATATYPE_INT64 # type: ignore
    """64 bit Integer"""
    FLOAT32 = internals.DATATYPE_FLOAT32 # type: ignore
    """32 bit Floating point"""
    FLOAT64 = internals.DATATYPE_FLOAT64 # type: ignore
    """64 bit Floating point"""
    STRING = internals.DATATYPE_STRING # type: ignore
    """ASCIIZ string"""
    BYTEARRAY = internals.DATATYPE_BYTEARRAY # type: ignore
    """Opaque binary data"""
    DATE = internals.DATATYPE_DATE # type: ignore
    """Date"""
    TIME = internals.DATATYPE_TIME # type: ignore
    """Timestamp"""
    DECIMAL = internals.DATATYPE_DECIMAL # type: ignore
    """Currently Unsupported"""
    DATETIME = internals.DATATYPE_DATETIME # type: ignore
    """Date and time"""
    ENUMERATION = internals.DATATYPE_ENUMERATION # type: ignore
    """An opaque enumeration"""
    SEQUENCE = internals.DATATYPE_SEQUENCE # type: ignore
    """Sequence type"""
    CHOICE = internals.DATATYPE_CHOICE # type: ignore
    """Choice type"""
    CORRELATION_ID = internals.DATATYPE_CORRELATION_ID # type: ignore
    """Used for some internal messages"""

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
