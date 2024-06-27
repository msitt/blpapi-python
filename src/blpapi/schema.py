# schema.py

"""Provide a representation of a schema describing structured messages.

This file defines these classes:

    'SchemaStatus' - the version status of a schema
    'SchemaTypeDefinition' - definitions of schema types
    'SchemaElementDefinition' - definitions of message elements

This component provides types for representing schemata which describe
structured messages. Such schemata consist of two distinct kinds of
definitions: "type" definitions (represented by 'SchemaTypeDefinition' objects)
declare types that can be used within other definitions (of both kinds); an
"element" definition defines a specific field by associating a field identifier
with a particular type, as well as the number of values of that type that are
permitted to be associated with that identifier.

"""
from __future__ import annotations
from typing import Sequence, Set, Optional
from typing import Iterator as IteratorType
from . import typehints  # pylint: disable=unused-import
from .typehints import BlpapiNameOrIndex
from .typehints import BlpapiSchemaElementDefinitionHandle
from .typehints import BlpapiSchemaTypeDefinitionHandle
from .exception import NotFoundException, IndexOutOfRangeException
from .name import Name, getNamePair
from .constant import ConstantList
from . import utils
from . import internals


# pylint: disable=protected-access,too-few-public-methods
class SchemaStatus(metaclass=utils.MetaClassForClassesWithEnums):
    """The possible deprecation statuses of a schema element or type."""

    ACTIVE = internals.STATUS_ACTIVE  # type: ignore
    """This item is current and may appear in Messages"""
    DEPRECATED = internals.STATUS_DEPRECATED  # type: ignore
    """This item is current and may appear in Messages but will be removed in
    due course"""
    INACTIVE = internals.STATUS_INACTIVE  # type: ignore
    """This item is not current and will not appear in Messages"""
    PENDING_DEPRECATION = internals.STATUS_PENDING_DEPRECATION  # type: ignore
    """This item is expected to be deprecated in the future; clients are
    advised to migrate away from use of this item."""


class SchemaElementDefinition(metaclass=utils.MetaClassForClassesWithEnums):
    """The definition of an individual field within a schema type.

    This class implements the definition of an individual field within a schema
    type. An element is defined by an identifer/name, a type, and the number of
    values of that type that may be associated with the identifier/name. In
    addition, this class offers access to metadata providing a description and
    deprecation status for the field.

    :class:`SchemaElementDefinition` objects are returned by :class:`Service`
    and :class:`Operation` objects to define the content of requests, replies
    and events. The :class:`SchemaTypeDefinition` returned by
    :meth:`typeDefinition()` may itself provide access to
    :class:`SchemaElementDefinition` objects when the schema contains nested
    elements.  (See the :class:`SchemaTypeDefinition` documentation for more
    information on complex types.)

    An optional element has ``minValues() == 0``.

    A mandatory element has ``minValues() >= 1``.

    An element that must contain a single value has
    ``minValues() == maxValues() == 1``.

    An element containing an array has ``maxValues() > 1``.

    An element with no upper limit on the number of values has
    ``maxValues() == UNBOUNDED``.

    :class:`SchemaElementDefinition` objects are read-only.

    Application clients need never create :class:`SchemaElementDefinition`
    objects directly; applications will typically work with objects returned by
    other blpapi components.
    """

    UNBOUNDED = internals.ELEMENTDEFINITION_UNBOUNDED  # type: ignore
    """Indicates an array has an unbounded number of values."""

    def __init__(
        self,
        handle: BlpapiSchemaElementDefinitionHandle,
        sessions: Set["typehints.AbstractSession"],
    ) -> None:
        self.__handle = handle
        self.__sessions = sessions

    def __str__(self) -> str:
        """x.__str__() <==> str(x)

        Return a string representation of this item. It is equivalent to
        toString() with default parameters.

        """

        return self.toString()

    def name(self) -> Name:
        """
        Returns:
            The name identifying this element within its containing
            structure/type.
        """

        return Name._createInternally(
            internals.blpapi_SchemaElementDefinition_name(self.__handle)
        )

    def description(self) -> str:
        """
        Returns:
            Human readable description of this element.
        """
        return internals.blpapi_SchemaElementDefinition_description(
            self.__handle
        )

    def status(self) -> int:
        """
        Returns:
            The deprecation status of this element.

        The possible return values are enumerated in :class:`SchemaStatus`.
        """

        return internals.blpapi_SchemaElementDefinition_status(self.__handle)

    def typeDefinition(self) -> SchemaTypeDefinition:
        """
        Returns:
            The type of values contained in this element.
        """
        return SchemaTypeDefinition(
            internals.blpapi_SchemaElementDefinition_type(self.__handle),
            self.__sessions,
        )

    def minValues(self) -> int:
        """
        Returns:
            The minimum number of occurrences of this element.

        This value is always greater than or equal to zero.
        """

        return internals.blpapi_SchemaElementDefinition_minValues(
            self.__handle
        )

    def maxValues(self) -> int:
        """
        Returns:
            The maximum number of occurrences of this element.

        This value is always greater than or equal to one.

        Return value is equal to :attr:`UNBOUNDED` if this item is an unbounded
        array.
        """

        return internals.blpapi_SchemaElementDefinition_maxValues(
            self.__handle
        )

    def alternateNames(self) -> Sequence[Name]:
        """
        Returns:
            The list of alternate names for this element.
        """

        res = []
        numAlternateNames = (
            internals.blpapi_SchemaElementDefinition_numAlternateNames(
                self.__handle
            )
        )
        for i in range(numAlternateNames):
            res.append(
                Name._createInternally(
                    internals.blpapi_SchemaElementDefinition_getAlternateName(
                        self.__handle, i
                    )
                )
            )
        return res

    def toString(self, level: int = 0, spacesPerLevel: int = 4) -> str:
        """
        Args:
            level: Indentation level
            spacesPerLevel: Number of spaces per indentation level for
                this and all nested objects

        Returns:
            This object formatted as a string

        If ``level`` is negative, suppress indentation of the first line. If
        ``spacesPerLevel`` is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by ``level``).
        """

        return internals.blpapi_SchemaElementDefinition_printHelper(
            self.__handle, level, spacesPerLevel
        )

    def _handle(self) -> typehints.BlpapiSchemaElementDefinitionHandle:
        """Return the internal implementation."""
        return self.__handle

    def _sessions(self) -> Set["typehints.AbstractSession"]:
        """Return session(s) this object is related to. For internal use."""
        return self.__sessions


class SchemaTypeDefinition:
    """Representation of a "type" that can be used within a schema.

    This class implements a representation of a "type" that can be used within
    a schema, including both plain types (integers, dates, strings, etc.)
    and "complex" types. The latter may be a "sequence" or a "choice" allowing
    either all or one of the named elements respectively. Those elements
    in turn are each described by a type. In addition to accessors
    for the type's structure, this class also offers access to metadata
    providing a description and deprecation status for the type.

    Each :class:`SchemaElementDefinition` object is associated with a single
    :class:`SchemaTypeDefinition`; one :class:`SchemaTypeDefinition` may be
    used by zero, one, or many :class:`SchemaElementDefinition` objects.

    :class:`SchemaTypeDefinition` objects are read-only.

    Application clients need never create :class:`SchemaTypeDefinition`
    objects directly; applications will typically work with objects returned by
    other blpapi components.
    """

    def __init__(
        self,
        handle: BlpapiSchemaTypeDefinitionHandle,
        sessions: Set["typehints.AbstractSession"],
    ) -> None:
        self.__handle = handle
        self.__sessions = sessions

    def __str__(self) -> str:
        """x.__str__() <==> str(x)

        Return a string representation of this 'SchemaTypeDefinition'. It is
        equivalent to call of toString() with default parameters.

        """

        return self.toString()

    def datatype(self) -> int:
        """
        Returns:
            The data type of this :class:`SchemaTypeDefinition`.

        The possible return values are enumerated in :class:`DataType`.
        """

        return internals.blpapi_SchemaTypeDefinition_datatype(self.__handle)

    def name(self) -> Name:
        """
        Returns:
            The name of this :class:`SchemaTypeDefinition`.
        """
        return Name._createInternally(
            internals.blpapi_SchemaTypeDefinition_name(self.__handle)
        )

    def description(self) -> str:
        """
        Returns:
            Human readable description of this :class:`SchemaTypeDefinition`.
        """
        return internals.blpapi_SchemaTypeDefinition_description(self.__handle)

    def status(self) -> int:
        """
        Returns:
            The deprecation status of this :class:`SchemaTypeDefinition`.

        The possible return values are enumerated in :class:`SchemaStatus`.
        """

        return internals.blpapi_SchemaTypeDefinition_status(self.__handle)

    def numElementDefinitions(self) -> int:
        """
        Returns:
            The number of :class:`SchemaElementDefinition` objects.

        If this :class:`SchemaTypeDefinition` is neither a choice nor a
        sequence this will return ``0``.
        """

        return internals.blpapi_SchemaTypeDefinition_numElementDefinitions(
            self.__handle
        )

    def isComplexType(self) -> bool:
        """
        Returns:
            ``True`` if this :class:`SchemaTypeDefinition` represents a
            sequence or choice type.
        """

        return bool(
            internals.blpapi_SchemaTypeDefinition_isComplexType(self.__handle)
        )

    def isSimpleType(self) -> bool:
        """
        Returns:
            ``True`` if this :class:`SchemaTypeDefinition` represents neither
            a sequence nor a choice type.
        """

        return bool(
            internals.blpapi_SchemaTypeDefinition_isSimpleType(self.__handle)
        )

    def isEnumerationType(self) -> bool:
        """
        Returns:
            ``True`` if this :class:`SchemaTypeDefinition` represents an
            enumeration type, ``False`` otherwise.
        """

        return bool(
            internals.blpapi_SchemaTypeDefinition_isEnumerationType(
                self.__handle
            )
        )

    def hasElementDefinition(self, name: Name) -> bool:
        """
        Args:
            name: Item identifier

        Returns:
            ``True`` if this object contains an item with the
            specified ``name``, ``False`` otherwise

        Raises:
            Exception: If ``name`` is neither a :class:`Name` nor a string.

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``name``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """

        namepair = getNamePair(name)
        return bool(
            internals.blpapi_SchemaTypeDefinition_hasElementDefinition(
                self.__handle, namepair[0], namepair[1]
            )
        )

    def getElementDefinition(
        self, nameOrIndex: BlpapiNameOrIndex
    ) -> SchemaElementDefinition:
        """
        Args:
            nameOrIndex: Name or index of the element

        Returns:
            The definition of a specified element.

        Raises:
            NotFoundException: If ``nameOrIndex`` is a string and
                ``hasElement(nameOrIndex) != True``.
            IndexOutOfRangeException: If ``nameOrIndex`` is an integer and
                ``nameOrIndex >= numElementDefinitions()``

        Note:
            **Please use** :class:`Name` **over** :class:`str` **where possible for**
            ``nameOrIndex``. :class:`Name` **objects should be initialized
            once and then reused** in order to minimize lookup cost.
        """

        if not isinstance(nameOrIndex, int):
            name = nameOrIndex
            names = getNamePair(name)
            res = internals.blpapi_SchemaTypeDefinition_getElementDefinition(
                self.__handle, names[0], names[1]
            )
            if res is None:
                errMessage = (
                    f"Name '{name!s}' not a sub-element of element "
                    f" '{self.name()!s}'."
                )
                raise NotFoundException(errMessage, 0)
            return SchemaElementDefinition(res, self.__sessions)
        position = nameOrIndex
        res = internals.blpapi_SchemaTypeDefinition_getElementDefinitionAt(
            self.__handle, position
        )
        if res is None:
            errMessage = f"Index '{position}' out of bounds."
            raise IndexOutOfRangeException(errMessage, 0)
        return SchemaElementDefinition(res, self.__sessions)

    def elementDefinitions(self) -> IteratorType[SchemaElementDefinition]:
        r"""
        Returns:
            Iterator over :class:`SchemaElementDefinition`\s defined by this
            :class:`SchemaTypeDefinition`.
        """

        return utils.Iterator(
            self,
            SchemaTypeDefinition.numElementDefinitions,
            SchemaTypeDefinition.getElementDefinition,
        )

    def enumeration(self) -> Optional["typehints.ConstantList"]:
        """
        Returns:
            All possible values of the enumeration defined by this type.
            ``None`` in case this :class:`SchemaTypeDefinition` is
            not a enumeration.
        """

        res = internals.blpapi_SchemaTypeDefinition_enumeration(self.__handle)
        return None if res is None else ConstantList(res, self.__sessions)

    def toString(self, level: int = 0, spacesPerLevel: int = 4) -> str:
        """
        Args:
            level: Indentation level
            spacesPerLevel: Number of spaces per indentation level for
                this and all nested objects

        Returns:
            This object formatted as a string

        If ``level`` is negative, suppress indentation of the first line. If
        ``spacesPerLevel`` is negative, format the entire output on one line,
        suppressing all but the initial indentation (as governed by ``level``).
        """

        return internals.blpapi_SchemaTypeDefinition_printHelper(
            self.__handle, level, spacesPerLevel
        )

    def _sessions(self) -> Set["typehints.AbstractSession"]:
        """Return session(s) this object is related to. For internal use."""
        return self.__sessions


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
