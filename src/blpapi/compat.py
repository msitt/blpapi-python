""" Different compatibility tools. Needed to support both
2.x and 3.x python versions."""

import sys

# pylint: disable=undefined-variable

def with_metaclass(metaclass):
    """Python 2 and 3 different metaclass syntax workaround.
    Should be used as a decorator."""
    def wrapper(cls):
        """ decorator """
        lvars = cls.__dict__.copy()
        slots = lvars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                lvars.pop(slots_var)
        lvars.pop('__dict__', None)
        lvars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, lvars)
    return wrapper

# NOTE: this function should be used to convert integer values to long
# values in both python2 and 3.

if sys.version.startswith('2'):
    def tolong(val):
        return long(val)
else:
    def tolong(val):
        return int(val)

# NOTE: python2 wrapper uses byte strings (str type) to pass strings
# to C-functions, unicode type is not supported so we need to encode
# all strings first. On the other hand, python3 wrapper uses unicode strings
# (str type) for this so we need to decode byte-strings first to get unicode
# strings. Rule of thumb: to pass string to any wrapper function convert
# it using `conv2str` function first, to check that type of the string
# is correct - use `isstr` function.

if sys.version.startswith('2'):
    def conv2str(s):
        """Convert unicode string to byte string."""
        if isinstance(s, str):
            return s
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return None

    def isstr(s):
        if isinstance(s, (str, unicode)):
            return True
        return False
else:
    def conv2str(s):
        """Convert byte string to unicode string."""
        if isinstance(s, bytes):
            return s.decode()
        if isinstance(s, str):
            return s
        return None

    def isstr(s):
        if isinstance(s, (bytes, str)):
            return True
        return False

# NOTE: integer typelist for different python versions
# to use with isinstance builtin function
if sys.version.startswith('2'):
    int_typelist = (int, long)
else:
    int_typelist = (int,)

# NOTE: string typelist for different python versions
# to use with isinstance builtin function
if sys.version.startswith('2'):
    str_typelist = (str, unicode)
else:
    str_typelist = (bytes, str)

# Helper import
# pylint: disable=deprecated-class,no-name-in-module
if sys.version.startswith('2'):
    from collections import Mapping as _Mapping, Sequence as _Sequence
else:
    from collections.abc import Mapping as _Mapping, Sequence as _Sequence
Mapping = _Mapping
Sequence = _Sequence
