# exception.py

"""Defines Exceptions that can be raised by the blpapi library.

This file defines various exceptions that blpapi can raise.
"""

from __future__ import absolute_import

from __builtin__ import Exception as _StandardException
from . import internals


class Exception(_StandardException):
    "This is the base class for exceptions used by blpapi."
    def __init__(self, description, errorCode):
        _StandardException.__init__(self, description, errorCode)

    def __str__(self):
        return "{0} ({1:#010x})".format(self.args[0], self.args[1])


class DuplicateCorrelationIdException(Exception):
    """Duplicate CorrelationId exception."""
    pass


class InvalidStateException(Exception):
    """Invalid state exception."""
    pass


class InvalidArgumentException(Exception):
    """Invalid argument exception."""
    pass


class InvalidConversionException(Exception):
    """Invalid conversion exception."""
    pass


class IndexOutOfRangeException(Exception):
    """Index out of range exception."""
    pass


class NotFoundException(Exception):
    """Not found exception."""
    pass


class FieldNotFoundException(Exception):
    """Field not found exception."""
    pass


class UnsupportedOperationException(Exception):
    """Unsupported operation exception."""
    pass


class UnknownErrorException(Exception):
    """Unknown error exception."""
    pass


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
        if errorCode == internals.ERROR_DUPLICATE_CORRELATIONID:
            return DuplicateCorrelationIdException
        errorClass = errorCode & 0xff0000
        return _ExceptionUtil.__errorClasses.get(errorClass,
                                                 UnknownErrorException)

    @staticmethod
    def raiseException(errorCode, description=None):
        if description is None:
            description = internals.blpapi_getLastErrorDescription(errorCode)
            if not description:
                description = "Unknown"
        errorClass = _ExceptionUtil.__getErrorClass(errorCode)
        raise errorClass(description, errorCode)

    @staticmethod
    def raiseOnError(errorCode, description=None):
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
