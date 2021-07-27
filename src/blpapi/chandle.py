# chandle.py

"""A module which defines base class for blpapi classes.

This file defines a 'CHandle' class.
It handles the life of an object with a handle from C layer.
"""

# pylint: disable=useless-object-inheritance

class CHandle(object):
    """A base class for objects that rely on C handles"""

    def __init__(self, handle, dtor):
        """ Set the handle and the dtor """
        self.__handle = handle
        self._dtor = dtor

    def __del__(self):
        """ Destroy the object """
        try:
            self.destroy()
        except (NameError, AttributeError):
            pass

    def destroy(self):
        """ Destroy the handle using stored dtor """
        if self.__handle:
            self._dtor(self.__handle)
            self.__handle = None

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle

__copyright__ = """
Copyright 2020. Bloomberg Finance L.P.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, co, modify, merge, publish, distribute, sublicense, and/or
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
