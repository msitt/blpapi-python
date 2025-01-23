# name.py

"""Provide a representation of a string for efficient comparison.

This file defines a class 'Name' which represents a string in a
form for efficient string comparison.

"""
from __future__ import annotations
from typing import Any, Optional, Tuple, Union
from . import internals
from .utils import conv2str, get_handle, isstr
from .chandle import CHandle
from . import typehints  # pylint: disable=unused-import
from .typehints import BlpapiNameHandle


# pylint: disable=broad-except
class Name(CHandle):
    """:class:`Name` represents a string in a form which is efficient for hashing and
    comparison, thus providing efficient lookup when used as a key in either
    ordered or hash-based containers.

    :class:`Name` objects are used to identify and access the classes which
    define the schema - :class:`SchemaTypeDefinition`,
    :class:`SchemaElementDefinition`, :class:`Constant`, :class:`ConstantList`.
    They are also used to access the values in :class:`Element` objects and
    :class:`Message` objects.

    The :class:`Name` class is an efficient substitute for a string when used
    as a key, providing constant time comparison and ordering operations. Two
    :class:`Name` objects constructed from equal strings will always compare
    equally.

    :class:`Name` objects should be initialized once and then
    reused.  Creating a :class:`Name` object involves a search in a container
    requiring multiple string comparison operations.

    Note:
        Each :class:`Name` instance refers to an entry in a global static
        table. :class:`Name` instances for identical strings will refer to the
        same data. There is no provision for removing entries from the static
        table so :class:`Name` objects should only be used when the set of
        input strings is bounded.

        For example, creating a :class:`Name` for every possible field name and
        type in a data model is reasonable (in fact, the API will do this
        whenever it receives schema information). However converting sequence
        numbers on incoming messages to strings and creating a :class:`Name`
        from each one of those strings will cause the static table to grow in
        an unbounded manner.
    """

    @staticmethod
    def findName(nameString: str) -> Optional[Name]:
        """
        Args:
            nameString: String represented by an existing :class:`Name`

        Returns:
            An existing :class:`Name` object representing ``nameString``.
            If no such object exists, ``None`` is returned.
        """
        nameHandle = internals.blpapi_Name_findName(nameString)
        return (
            None if nameHandle is None else Name._createInternally(nameHandle)
        )

    @staticmethod
    def hasName(nameString: str) -> bool:
        """
        Args:
            nameString: String represented by an existing :class:`Name`

        Returns:
            ``True`` if a :class:`Name` object representing
            ``nameString`` exists
        """
        return bool(internals.blpapi_Name_hasName(nameString))

    @staticmethod
    def _createInternally(handle: BlpapiNameHandle) -> Name:
        return Name(None, handle)

    def __init__(
        self,
        nameString: Optional[str],
        internalHandle: Optional[BlpapiNameHandle] = None,
    ) -> None:
        selfhandle = internalHandle
        if selfhandle is None:
            selfhandle = internals.blpapi_Name_create(nameString)
        super(Name, self).__init__(selfhandle, internals.blpapi_Name_destroy)
        self.__handle = selfhandle

    def __len__(self) -> int:
        """Return the length of the string that this Name represents."""

        return internals.blpapi_Name_length(self.__handle)

    def __str__(self) -> str:
        """x.__str__() <==> str(x)

        Return a string that this Name represents.

        """

        return internals.blpapi_Name_string(self.__handle)

    def __repr__(self) -> str:
        """

        Return a string that this Name represents.
        Container's __str__ uses contained objects' __repr__

        """
        return f"blpapi.Name('{self}')"

    def __eq__(self, other: Any) -> bool:
        """x.__eq__(y) <==> x==y"""
        if not isstr(other):
            if other is None:
                return False
            return self.__handle.value == get_handle(other).value  # type: ignore

        s = conv2str(other)
        p = internals.blpapi_Name_equalsStr(self.__handle, s)
        return p != 0

    def __ne__(self, other: Any) -> bool:
        """x.__ne__(y) <==> x!=y"""
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """x.__hash__() <==> hash(x)"""
        return int(self.__handle.value)  # type: ignore


def getNamePair(
    name: Union[Name, str],
) -> Union[Tuple[None, BlpapiNameHandle], Tuple[str, None]]:
    """Create a tuple that contains a name string and blpapi_Name_t*.

    Args:
        name: A :class:`Name` or a string instance

    Returns:
        ``(None, name._handle())`` if ``name`` is a :class:`Name` instance, or
        ``(name, None)`` if ``name`` is a string. In other cases raise
        TypeError exception.

    Raises:
        TypeError: If ``name`` is neither a :class:`Name` nor a string

    For internal use only.

    Note:
        :class:`Name` **objects should be initialized
        once and then reused** in order to minimize lookup cost.
    """

    if isinstance(name, Name):
        return (None, get_handle(name))
    if isstr(name):
        return (conv2str(name), None)
    raise TypeError("name should be an instance of a string or blpapi.Name")


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
