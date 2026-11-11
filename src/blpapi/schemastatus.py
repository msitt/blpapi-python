# schemastatus.py

"""Provide an enumeration of the deprecation statuses used by a schema.

This file defines these classes:
    'SchemaStatus' - the version status of a schema

It lives in its own module so that both 'schema' and 'constant' can use it
without importing each other.
"""

from . import internals
from .utils import BlpapiIntEnum


class SchemaStatus(BlpapiIntEnum):
    """The possible deprecation statuses of a schema element or type."""

    # pylint: disable=invalid-enum-extension

    ACTIVE = internals.STATUS_ACTIVE
    """This item is current and may appear in Messages"""
    DEPRECATED = internals.STATUS_DEPRECATED
    """This item is current and may appear in Messages but will be removed in
    due course"""
    INACTIVE = internals.STATUS_INACTIVE
    """This item is not current and will not appear in Messages"""
    PENDING_DEPRECATION = internals.STATUS_PENDING_DEPRECATION
    """This item is expected to be deprecated in the future; clients are
    advised to migrate away from use of this item."""


__copyright__ = """
Copyright 2026. Bloomberg Finance L.P.

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
