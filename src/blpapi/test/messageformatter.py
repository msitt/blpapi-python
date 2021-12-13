# messageformatter.py

""" Class for formatting mock messages. """

# pylint: disable=function-redefined,ungrouped-imports,no-name-in-module

import sys
from functools import update_wrapper
from datetime import date, time, datetime
from json import dumps

from blpapi import internals, Name
from blpapi.datetime import _DatetimeUtil
from blpapi.compat import conv2str, int_typelist, isstr, str_typelist
from blpapi.exception import _ExceptionUtil
from blpapi.utils import \
        get_handle, \
        MAX_32BIT_INT, \
        MIN_32BIT_INT, \
        MIN_64BIT_INT, \
        MAX_64BIT_INT

if sys.version_info >= (3, 4):
    from functools import singledispatch
else:
    def singledispatch(func):
        """ Transform a function into a single-dispatch generic function.

        This function is intended to provide a basic implementation of
        `functools.singledispatch` found in Python >= 3.4. No caching
        optimizations are performed. Types are matched naively: there is no
        support for inherited types.
        """

        registry = {}
        funcname = getattr(func, "__name__", "singledispatch function")

        def dispatch(cls):
            """ Return the function registered to `cls`. If there is no
            function associated with `cls`, return `func`.
            """

            # Return `func` instead of `None` because the native
            # python implementation ultimately ends up doing this for
            # types whose closest match in the registry is type
            # `object`
            return registry.get(cls, func)

        def register(cls, func=None):
            """ Register a new function `func` for the given `cls`. """

            # Return a lambda so that `register` can be used as a decorator
            if func is None:
                return lambda f: register(cls, f)

            registry[cls] = func

            return func

        def wrapper(*args, **kw):
            """ Wrap the provided `func` from `singledispatch` to provide
            additional functionality without modifying `func` directly.
            """
            if not args:
                raise TypeError("{} requires at least 1 positional argument"
                                .format(funcname))

            return dispatch(args[0].__class__)(*args, **kw)

        wrapper.register = register
        wrapper.dispatch = dispatch
        wrapper.registry = registry
        update_wrapper(wrapper, func)
        return wrapper

def _singledispatchmethod(arg_index):
    """ Decorator to implement singledispatch on a class method.
    `arg_index` indicates the argument whose type will be used to determine
    the function to which to dispatch.
    """

    def _singleDispatchMethodImpl(func):
        """ Implementation of `_singledispatchmethod`. """
        dispatcher = singledispatch(func)
        # `dispatcher` is `func` wrapped by singledispatch
        # `dispatcher` has an attribute `register()`, which is a decorator,
        # which registers the typed funcs to call based on the arg passed to
        # `func`
        def _wrapper(*args, **kw):
            # singledispatch bases the type on the first arg, which is `self`
            # in a method. Instead, we need the 3rd argument, skipping over
            # `self` and `name` in `setElement(self, name, value)`
            return dispatcher.dispatch(args[arg_index].__class__)(*args, **kw)
        # give `_wrapper` a `.register()` attribute
        _wrapper.register = dispatcher.register
        # makes `_wrapper` look like `func` with regards to metadata and
        # attributes
        update_wrapper(_wrapper, func)
        return _wrapper

    return _singleDispatchMethodImpl

class MessageFormatter():
    """ :class:`MessageFormatter` is used to populate/format a message. It
    supports writing only once to each field. Attempting to set an already set
    element will fail.

    Note that the behavior is undefined if:

    * A message is formatted with :meth:`formatMessageJson` or
      :meth:`formatMessageXml` or :meth:`formatMessageDict` is further
      formatted.

    * A message formatted with `set*()` or `append*()` is further formatted
      using :meth:`formatMessageJson` or :meth:`formatMessageXml` or
      :meth:`formatMessageDict`.

    Currently, the JSON and XML formatting methods have some known limitations:

    * The parsers can not differentiate complex field types
      (sequences, choices, arrays) that are empty with complex field types that
      are missing / null. These fields are dropped and absent in the message
      contents.

    * Enumerations of type "Datetime", or any "Datetime" element with timezone
      offset or sub-microsecond precision (e.g. nanoseconds) are not supported.
    """

    def __init__(self, handle):
        """ For internal use only. """
        self.__handle = handle

    def _handle(self):
        return self.__handle

    def setElement(self, name, value):
        """ Set the element with the specified ``name`` to the specified
        ``value`` in the current :class:`blpapi.Message` referenced by this
        :class:`MessageFormatter`.

        Args:
            name (blpapi.Name or str): Identifies the element which will be set
                to ``value``.
            value (bool or str or int or float or datetime.date or \
                   datetime.time or datetime.datetime or blpapi.Name or None):
                The value to assign to the specified element.

        Raises:
            Exception: An exception is raised if any of the following are true:
                - The ``name`` is invalid for the current message
                - The element identified by ``name`` has already been set
                - The ``value`` cannot be assigned to the element identified by
                    ``name``
        """
        if isstr(name):
            name = Name(conv2str(name))
        self._setElement(name, value)

    # pylint: disable=unused-argument,no-self-use
    @_singledispatchmethod(2)
    def _setElement(self, name, value):
        """ Implementation for :meth:`setElement`.

        Args:
            name (Name): Identifies the element which will be set to ``value``
            value (bool or str or int or float or date or time or
                datetime or Name or None):
                The value to assign to the specified element.

        Raises:
            Exception: An exception is raised if any of the following are true:
                - The ``name`` is invalid for the current message
                - The element identified by ``name`` has already been set
                - The ``value`` cannot be assigned to the element identified by
                    ``name``
        """
        raise TypeError("The type of value {} is not supported. Type is {}."
                        .format(value, type(value))
                        + " Please refer to the documentation for the"
                        + " supported types.")

    @_setElement.register(bool)
    def _(self, name, value):
        """ Dispatch method for setting `bool` types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_setValueBool(
                self.__handle,
                get_handle(name),
                value))

    @_setElement.register(datetime)
    @_setElement.register(date)
    @_setElement.register(time)
    def _(self, name, value):
        """ Dispatch method for setting time types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_setValueHighPrecisionDatetime(
                self.__handle,
                get_handle(name),
                _DatetimeUtil.convertToBlpapi(value)))

    def _setElementInt(self, name, value):
        """ Dispatch method for setting integer types. """
        if MIN_32BIT_INT <= value <= MAX_32BIT_INT:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_MessageFormatter_setValueInt32(
                    self.__handle,
                    get_handle(name),
                    value))
        elif MIN_64BIT_INT <= value <= MAX_64BIT_INT:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_MessageFormatter_setValueInt64(
                    self.__handle,
                    get_handle(name),
                    value))
        else:
            raise ValueError("Value is out of element's supported range")
    for _int_type in int_typelist:
        _setElement.register(_int_type, _setElementInt)

    @_setElement.register(float)
    def _(self, name, value):
        """ Dispatch method for setting `float` types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_setValueFloat(
                self.__handle,
                get_handle(name),
                value))

    @_setElement.register(Name)
    def _(self, name, value):
        """ Dispatch method for setting `Name` types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_setValueFromName(
                self.__handle,
                get_handle(name),
                get_handle(value)))

    @_setElement.register(type(None))
    def _(self, name, _):
        """ Dispatch method for setting `None` types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_setValueNull(
                self.__handle,
                get_handle(name)))

    def _setElementStr(self, name, value):
        """ Dispatch method for setting string types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_setValueString(
                self.__handle,
                get_handle(name),
                conv2str(value)))
    for _str_type in str_typelist:
        _setElement.register(_str_type, _setElementStr)

    def pushElement(self, name):
        """ Change the level at which this :class:`MessageFormatter` is
        operating to the element specified by ``name``.

        After this returns, the context of the :class:`MessageFormatter` is set
        to the element specified by ``name`` in the schema and any calls to
        :meth:`setElement` or meth:`pushElement` are applied at that level.

        If ``name`` represents an array of scalars then :meth:`appendValue`
        must be used to add values.

        If ``name`` represents an array of complex types then
        :meth:`appendElement()` must be used.

        Args:
            name (blpapi.Name or str): Specifies the :class:`blpapi.Element` on
                which to operate. The element must identify either a choice, a
                sequence or an array at the current level of the schema or the
                behavior is undefined.

        Raises:
            Exception: If the ``name`` is invalid for the current message or if
                the element identified by ``name`` has already been set.
        """
        if isstr(name):
            name = Name(conv2str(name))
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_pushElement(
                self.__handle,
                get_handle(name)))

    def popElement(self):
        """ Undo the most recent call to :meth:`pushElement` or
        :meth:`appendElement` on this :class:`MessageFormatter` and return the
        context of the :class:`MessageFormatter` to where it was before the
        call to :meth:`pushElement` or :meth:`appendElement`. Once
        :meth:`popElement` has been called, it is invalid to attempt to
        re-visit the same context.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_popElement(self.__handle))

    @_singledispatchmethod(1)
    def appendValue(self, value):
        """ Append the specified ``value`` to the element on which this
        :class:`MessageFormatter` is operating.

        Args:
            value (bool or str or int or float or datetime.date or \
                   datetime.time or datetime.datetime or blpapi.Name):
                The value to append.

        Raises:
            Exception: If the schema of the message is flat or the current
                element to which ``value`` is appended is not an array.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_appendValueString(
                self.__handle,
                value))

    @appendValue.register(bool)
    def _(self, value):
        """ Dispatch method for appending `bool` types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_appendValueBool(
                self.__handle,
                value))

    @appendValue.register(datetime)
    @appendValue.register(date)
    @appendValue.register(time)
    def _(self, value):
        """ Dispatch method for appending time types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_appendValueHighPrecisionDatetime(
                self.__handle,
                _DatetimeUtil.convertToBlpapi(value)))

    def _appendValueInt(self, value):
        """ Dispatch method for appending integer types. """
        if MIN_32BIT_INT <= value <= MAX_32BIT_INT:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_MessageFormatter_appendValueInt32(
                    self.__handle,
                    value))
        elif MIN_64BIT_INT <= value <= MAX_64BIT_INT:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_MessageFormatter_appendValueInt64(
                    self.__handle,
                    value))
        else:
            raise ValueError("Value is out of element's supported range")
    for _int_type in int_typelist:
        appendValue.register(_int_type, _appendValueInt)

    @appendValue.register(float)
    def _(self, value):
        """ Dispatch method for appending `float` types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_appendValueFloat(
                self.__handle,
                value))

    @appendValue.register(Name)
    def _(self, value):
        """ Dispatch method for appending `Name` types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_appendValueFromName(
                self.__handle,
                get_handle(value)))

    def _appendValueStr(self, value):
        """ Dispatch method for appending string types. """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_appendValueString(
                self.__handle,
                conv2str(value)))
    for _str_type in str_typelist:
        appendValue.register(_str_type, _appendValueStr)

    def appendElement(self):
        """ Create an array :class:`blpapi.Element` and append it to the
        :class:`blpapi.Element` on which this :class:`MessageFormatter` is
        operating.

        Raises:
            Exception: If the schema of the :class:`blpapi.Message` is flat or
                the current :class:`blpapi.Element` to which this new
                :class:`blpapi.Element` is being appended is not an array, a
                sequence or a choice.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_appendElement(self.__handle))

    def formatMessageJson(self, jsonMessage):
        """ Format the :class:`blpapi.Message` from its ``JSON`` representation.

        Args:
            jsonMessage (str): A ``JSON``-formatted ``str`` representing the
                content used to format the message.

        Raises:
            Exception: If the method fails to format the
                :class:`blpapi.Message`.

        The behavior is undefined if further formatting is done using
        this :class:`MessageFormatter`.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_FormatMessageJson(
                self.__handle,
                jsonMessage))

    def formatMessageXml(self, xmlMessage):
        """ Format the :class:`blpapi.Message` from its ``XML`` representation.

        Args:
            xmlMessage (str): An ``XML``-formatted ``str`` representing the
                content used to format the message.

        Raises:
            Exception: If the method fails to format the
                :class:`blpapi.Message`.

        The behavior is undefined if further formatting is done using
        this :class:`MessageFormatter`.
        """
        _ExceptionUtil.raiseOnError(
            internals.blpapi_MessageFormatter_FormatMessageXml(
                self.__handle,
                xmlMessage))

    def formatMessageDict(self, dictMessage):
        """ Format the :class:`blpapi.Message` from its ``dict`` representation.

        Args:
            dictMessage (dict): A dictionary representing the content used to
                format the message.

        Raises:
            Exception: If the method fails to format the
                :class:`blpapi.Message`.

        The behavior is undefined if further formatting is done using
        this :class:`MessageFormatter`.
        """
        self.formatMessageJson(dumps(dictMessage))


__copyright__ = """
Copyright 2020. Bloomberg Finance L.P.

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
