# exception.py

"""Defines Exceptions that can be raised by the blpapi library.

This file defines various exceptions that blpapi can raise.
"""


try:
    from builtins import Exception as _StandardException
except ImportError:
    from __builtin__ import Exception as _StandardException
from . import internals


# pylint: disable=useless-object-inheritance, redefined-builtin

class Exception(_StandardException):
    """This class defines a base exception for blpapi operations.

    Objects of this class contain the error description for the exception.
    """
    def __init__(self, description, errorCode):
        """Create a blpapi exception

        Args:
            description (str): Description of the error
            errorCode (int): Code corresponding to the error
        """
        _StandardException.__init__(self, description, errorCode)

    def __str__(self):
        args_arr = list(self.args)
        return "{0} ({1:#010x})".format(args_arr[0], args_arr[1])


class DuplicateCorrelationIdException(Exception):
    """Duplicate CorrelationId exception.

    The class defines an exception for non unique :class:`CorrelationId`.
    """


class InvalidStateException(Exception):
    """Invalid state exception.

    This class defines an exception for calling methods on an object that is
    not in a valid state.
    """


class InvalidArgumentException(Exception):
    """Invalid argument exception.

    This class defines an exception for invalid arguments on method
    invocations.
    """


class InvalidConversionException(Exception):
    """Invalid conversion exception.

    This class defines an exception for invalid conversion of data.
    """


class IndexOutOfRangeException(Exception):
    """Index out of range exception.

    This class defines an exception to capture the error when an invalid index
    is used for an operation that needs index.
    """


class NotFoundException(Exception):
    """Not found exception.

    This class defines an exception to capture the error when an item is not
    found for an operation.

    """


class FieldNotFoundException(Exception):
    """Field not found exception.

    This class defines an exception to capture the error when an invalid field
    is used for operation.

    **DEPRECATED**
    """


class UnsupportedOperationException(Exception):
    """Unsupported operation exception.

    This class defines an exception for unsupported operations.
    """


class UnknownErrorException(Exception):
    """Unknown error exception.

    This class defines an exception for errors that do not fall in any
    predefined category.
    """


class _ExceptionUtil(object):
    """Internal exception generating class."""
    __errorClasses = {
        internals.INVALIDSTATE_CLASS: InvalidStateException,
        internals.INVALIDARG_CLASS: InvalidArgumentException,
        internals.CNVERROR_CLASS: InvalidConversionException,
        internals.BOUNDSERROR_CLASS: IndexOutOfRangeException,
        internals.NOTFOUND_CLASS: NotFoundException,
        internals.FLDNOTFOUND_CLASS: FieldNotFoundException,
        internals.UNSUPPORTED_CLASS: UnsupportedOperationException
    }

    @staticmethod
    def __getErrorClass(errorCode):
        """ returns proper error class for the code """
        if errorCode == internals.ERROR_DUPLICATE_CORRELATIONID:
            return DuplicateCorrelationIdException
        errorClass = errorCode & 0xff0000
        return _ExceptionUtil.__errorClasses.get(errorClass,
                                                 UnknownErrorException)

    @staticmethod
    def raiseException(errorCode, description=None):
        """Throw the appropriate exception for the specified 'errorCode'."""
        if description is None:
            description = internals.blpapi_getLastErrorDescription(errorCode)
            if not description:
                description = "Unknown"
        errorClass = _ExceptionUtil.__getErrorClass(errorCode)
        raise errorClass(description, errorCode)

    @staticmethod
    def raiseOnError(errorCode, description=None):
        """Throw the appropriate exception for the specified 'errorCode' if the
        'errorCode != 0'.
        """
        if errorCode:
            _ExceptionUtil.raiseException(errorCode, description)

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
