# utils.py

"""Internal utils."""

from .compat import Sequence, str_typelist
import functools
import warnings

MIN_32BIT_INT = -(2**31)
MAX_32BIT_INT = 2**31 - 1
MIN_64BIT_INT = -(2**63)
MAX_64BIT_INT = 2**63 - 1


# pylint: disable=too-few-public-methods, useless-object-inheritance
class Iterator(object):
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

    def __init__(self, objToIterate, numFunc, getFunc):
        self.__obj = objToIterate
        self.__index = 0
        self.__num = numFunc(objToIterate)
        self.__getter = getFunc

    def __iter__(self):
        return self

    def __next__(self):
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
        """Raise this on attempt to change value of an enumeration constant.
        """

    def __setattr__(cls, name, value):
        """Change the value of an attribute if it is not an enum.

        Raise EnumError exception otherwise.
        """
        if name.isupper() and name in cls.__dict__:
            raise cls.EnumError("Can't change value of enum %s" % name)
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        """Unbind the attribute if it is not an enum.

        Raise EnumError exception otherwise.
        """
        if name.isupper() and name in cls.__dict__:
            raise cls.EnumError("Can't unbind enum %s" % name)
        type.__delattr__(cls, name)

def get_handle(thing):
    """Returns the result of thing._handle() or None if thing is None"""
    return None if thing is None else thing._handle() #pylint: disable=protected-access

def invoke_if_valid(cb, value):
    """Returns the result of cb(value) if cb is callable, else -- just value"""
    if cb is None or not callable(cb):
        return value
    return cb(value)

def deprecated(func_or_reason):
    '''
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
    '''

    is_func = callable(func_or_reason)
    message = "see docstring for details." if is_func else func_or_reason

    def decorate(func):

        @functools.wraps(func)
        def wrap_func(*args, **kwargs):
            warnings.warn(
                "%s is deprecated, %s." % (func.__name__, message),
                category=DeprecationWarning,
                stacklevel=2)
            return func(*args, **kwargs)

        return wrap_func

    if is_func:
        return decorate(func_or_reason)

    return decorate


# NOTE: `isNonScalarSequence` is used to determine whether `obj` is a
# `Sequence` but does not behave like a scalar. Useful for `Element` and
# `Event` formatting.
# pylint: disable=deprecated-class,no-name-in-module
def isNonScalarSequence(obj):
    scalarTypes = str_typelist + (bytearray, memoryview)
    return isinstance(obj, Sequence) and not isinstance(obj, scalarTypes)


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
