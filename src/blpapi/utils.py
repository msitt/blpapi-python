# utils.py

"""Internal utils."""

from collections.abc import Iterator as IteratorABC, Sequence
from typing import Any, Callable, Union, Optional
from typing import Iterator as IteratorType
import functools
import warnings

from .chandle import CHandle


STR_TYPES = (bytes, str)

MIN_32BIT_INT = -(2**31)
MAX_32BIT_INT = 2**31 - 1
MIN_64BIT_INT = -(2**63)
MAX_64BIT_INT = 2**63 - 1


# pylint: disable=too-few-public-methods
class Iterator(IteratorABC):
    """Universal iterator for many of BLPAPI objects.

    It can be used to iterate any sub-items in an item which has
    the following methods:
        * method returning the number of sub-items
        * method returning the 'index'ed sub-item

    For example, it is currently used as an iterator for Service's event
    definition in the following way:

        class Service(object):
            ...
            # Return an iterator over this Service's event definitions.
            def eventDefinitions(self):
                return utils.Iterator(
                    self,
                    Service.numEventDefinitions,
                    Service.getEventDefinitionAt)

            ...

    """

    def __init__(
        self,
        objToIterate: Any,
        numFunc: Callable[[Any], int],
        getFunc: Callable[[Any, int], Any],
    ) -> None:
        self.__obj = objToIterate
        self.__index = 0
        self.__num = numFunc(objToIterate)
        self.__getter = getFunc

    def __iter__(self) -> IteratorType:
        return self

    def __next__(self) -> Any:
        if self.__index == self.__num:
            raise StopIteration()
        res = self.__getter(self.__obj, self.__index)
        self.__index += 1
        return res

    next = __next__


class MetaClassForClassesWithEnums(type):
    """This meta class protects enums from changes.

    This meta class does not let change values of class members with names in
    uppercase (a typical naming convention for enums).

    """

    class EnumError(TypeError):
        """Raise this on attempt to change value of an enumeration constant."""

    def __setattr__(cls, name: str, value: Any) -> None:
        """Change the value of an attribute if it is not an enum.

        Raise EnumError exception otherwise.
        """
        if name.isupper() and name in cls.__dict__:
            raise cls.EnumError(f"Can't change value of enum {name}")
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name: str) -> None:
        """Unbind the attribute if it is not an enum.

        Raise EnumError exception otherwise.
        """
        if name.isupper() and name in cls.__dict__:
            raise cls.EnumError(f"Can't unbind enum {name}")
        type.__delattr__(cls, name)


def get_handle(thing: Optional[CHandle]) -> Any:
    """Returns the result of thing._handle() or None if thing is None"""
    # pylint: disable=protected-access
    return None if thing is None else thing._handle()


def invoke_if_valid(cb: Any, value: Any) -> Any:
    """Returns the result of cb(value) if cb is callable, else -- just value"""
    if cb is None or not callable(cb):
        return value
    return cb(value)


def deprecated(func_or_reason: Union[Callable, str]) -> Callable:
    """
    This is a decorator which can be used to mark classes or functions
    as deprecated. It results in a warning being emitted when the class or the
    function is called.

    To use this, decorate the deprecated class or function with
    **@deprecated** with or without a message:

        code-block:: python

        from blpapi.util import deprecated

        @deprecated
        def old_function(msg):
            print(msg)

        @deprecated
        class OldClass:

            @deprecated("use another function")
            def old_function(self, msg);
                print(msg)
    """

    is_func = callable(func_or_reason)
    message = "see docstring for details." if is_func else func_or_reason

    def decorate(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrap_func(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(
                f"{func.__name__} is deprecated, {message}.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrap_func

    if is_func:
        return decorate(func_or_reason)  # type: ignore

    return decorate


# NOTE: `isNonScalarSequence` is used to determine whether `obj` is a
# `Sequence` but does not behave like a scalar. Useful for `Element` and
# `Event` formatting.
# pylint: disable=deprecated-class,no-name-in-module
def isNonScalarSequence(obj: Any) -> bool:
    scalarTypes = STR_TYPES + (bytearray, memoryview)
    return isinstance(obj, Sequence) and not isinstance(obj, scalarTypes)


# NOTE: Our Python3 wrapper uses unicode strings (str type) for passing
# strings to C-functions so we need to decode byte-strings first to get unicode
# strings. Rule of thumb: to pass string to any wrapper function convert
# it using `conv2str` function first, to check that type of the string
# is correct - use `isstr` function.
def conv2str(s: Union[bytes, str]) -> str:
    """Convert byte string to unicode string."""
    if isinstance(s, bytes):
        return s.decode()
    if isinstance(s, str):
        return s
    return None


def isstr(s: Any) -> bool:
    if isinstance(s, STR_TYPES):
        return True
    return False


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
