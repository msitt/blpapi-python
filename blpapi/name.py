# name.py

"""Provide a representation of a string for efficient comparison.

This file defines a class 'Name' which represents a string in a
form for efficient string comparison.

"""

from __future__ import absolute_import

from . import internals


class Name(object):
    """Name represents a string in a form which is efficient for comparison.

    Name(nameString) constructs a Name object.

    Name objects are used to identify and access the classes which define the
    schema - SchemaTypeDefinition, SchemaElementDefinition, SchemaConstant,
    SchemaConstantList. They are also used to access the values in Element
    objects and Message objects.

    The Name class is an efficient substitute for a string when used as a key,
    providing constant time comparison and ordering operations. Two Name
    objects constructed from equal strings will always compare equally.

    Where possible Name objects should be initialized once and then reused.
    Creating a Name object involves a search in a container requiring multiple
    string comparison operations.

    Note: Each Name instance refers to an entry in a global static table. Name
    instances for identical strings will refer to the same data. There is no
    provision for removing entries from the static table so Name objects should
    only be used when the set of input strings is bounded.

    For example, creating a Name for every possible field name and type in a
    data model is reasonable (in fact, the API will do this whenever it
    receives schema information). However converting sequence numbers on
    incoming messages to strings and creating a Name from each one of those
    strings will cause the static table to grow in an unbounded manner.

    """

    __handle = None

    @staticmethod
    def findName(nameString):
        """Return an existing Name object representing 'nameString'.

        If no such object exists, None is returned.
        """
        nameHandle = internals.blpapi_Name_findName(nameString)
        return None if nameHandle is None \
            else Name._createInternally(nameHandle)

    @staticmethod
    def hasName(nameString):
        """Return True if a Name object representing 'nameString' exists.
        """
        return internals.blpapi_Name_hasName(nameString)

    @staticmethod
    def _createInternally(handle):
        return Name(None, handle)

    def __init__(self, nameString, internalHandle=None):
        if internalHandle is not None:
            self.__handle = internalHandle
        else:
            self.__handle = internals.blpapi_Name_create(nameString)

    def __del__(self):
        if self.__handle is not None:
            internals.blpapi_Name_destroy(self.__handle)

    def __len__(self):
        """Return the length of the string that this Name represents.
        """

        return internals.blpapi_Name_length(self.__handle)

    def __str__(self):
        """x.__str__() <==> str(x)

        Return a string that this Name represents.

        """

        return internals.blpapi_Name_string(self.__handle)

    def __eq__(self, other):
        """x.__eq__(y) <==> x==y"""
        try:
            if isinstance(other, str):
                return 0 != internals.blpapi_Name_equalsStr(self.__handle,
                                                            other)
            else:
                if isinstance(other, unicode):
                    raise TypeError(
                        "unicode strings are not currently supported")
                return self.__handle == other.__handle
        except Exception:
            return NotImplemented

    def __ne__(self, other):
        """x.__ne__(y) <==> x!=y"""
        equal = self.__eq__(other)
        return NotImplemented if equal is NotImplemented else not equal

    def __hash__(self):
        """x.__hash__() <==> hash(x)"""
        return long(self.__handle)

    def _handle(self):
        return self.__handle


def getNamePair(name):
    """Create a tuple that contains nameString and blpapi_Name_t *.

    Return (None, name._handle()) if 'name' is a Name instance or (name, None)
    if name is a string. In other cases raise TypeError exception.

    """

    if isinstance(name, Name):
        return (None, name._handle())
    elif isinstance(name, str):
        return (name, None)
    else:
        raise TypeError(
            "name should be an instance of a string or blpapi.Name")

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
