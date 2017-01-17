# datatype.py

"""Provide "enum" representing all possible data types in an Element.

This file defines these classes:
    'DataType' - "enum" representing all possible data types in an Element.
"""

from __future__ import absolute_import

from . import internals
from . import utils


class DataType:
    """Contains the possible data types which can be represented in an Element.

    Class attributes:
        BOOL            Boolean
        CHAR            Char
        BYTE            Unsigned 8 bit value
        INT32           32 bit Integer
        INT64           64 bit Integer
        FLOAT32         32 bit Floating point
        FLOAT64         64 bit Floating point
        STRING          ASCIIZ string
        BYTEARRAY       Opaque binary data
        DATE            Date
        TIME            Timestamp
        DECIMAL         Currently Unsuppored
        DATETIME        Date and time
        ENUMERATION     An opaque enumeration
        SEQUENCE        Sequence type
        CHOICE          Choice type
        CORRELATION_ID  Used for some internal messages
    """

    BOOL = internals.DATATYPE_BOOL
    """Boolean"""
    CHAR = internals.DATATYPE_CHAR
    """Char"""
    BYTE = internals.DATATYPE_BYTE
    """Unsigned 8 bit value"""
    INT32 = internals.DATATYPE_INT32
    """32 bit Integer"""
    INT64 = internals.DATATYPE_INT64
    """64 bit Integer"""
    FLOAT32 = internals.DATATYPE_FLOAT32
    """32 bit Floating point"""
    FLOAT64 = internals.DATATYPE_FLOAT64
    """64 bit Floating point"""
    STRING = internals.DATATYPE_STRING
    """ASCIIZ string"""
    BYTEARRAY = internals.DATATYPE_BYTEARRAY
    """Opaque binary data"""
    DATE = internals.DATATYPE_DATE
    """Date"""
    TIME = internals.DATATYPE_TIME
    """Timestamp"""
    DECIMAL = internals.DATATYPE_DECIMAL
    """Currently Unsupported"""
    DATETIME = internals.DATATYPE_DATETIME
    """Date and time"""
    ENUMERATION = internals.DATATYPE_ENUMERATION
    """An opaque enumeration"""
    SEQUENCE = internals.DATATYPE_SEQUENCE
    """Sequence type"""
    CHOICE = internals.DATATYPE_CHOICE
    """Choice type"""
    CORRELATION_ID = internals.DATATYPE_CORRELATION_ID
    """Used for some internal messages"""

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums

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
