# compat.py

import sys

""" Different compatibility tools. Needed to support both
2.x and 3.x python versions."""

def with_metaclass(metaclass):
    """Python 2 and 3 different metaclass syntax workaround. Should be used as a decorator."""
    def wrapper(cls):
        vars = cls.__dict__.copy()
        slots = vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                vars.pop(slots_var)
        vars.pop('__dict__', None)
        vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, vars)
    return wrapper

# NOTE: this function should be used to convert integer values to long
# values in both python2 and 3.

if sys.version.startswith('2'):
    def tolong(val):
        return long(val)
else:
    def tolong(val):
        return int(val)

# NOTE: python2 wrapper uses byte strings (str type) to pass strings to C-functions,
# unicode type is not supported so we need to encode all strings first.
# On the other hand, python3 wrapper uses unicode strings (str type) for this so we need
# to decode byte-strings first to get unicode strings. Rule of thumb: to pass string to any
# wrapper function convert it using `conv2str` function first, to check that type of the
# string is correct - use `isstr` function.

if sys.version.startswith('2'):
    def conv2str(s):
        """Convert unicode string to byte string."""
        if isinstance(s, str):
            return s
        elif isinstance(s, unicode):
            return s.encode('utf-8')
        else:
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
        elif isinstance(s, str):
            return s
        else:
            return None

    def isstr(s):
        if isinstance(s, (bytes, str)):
            return True
        return False

# NOTE: integer typelist for different python versions to use with isinstance builtin function
if sys.version.startswith('2'):
    int_typelist = (int, long)
else:
    int_typelist = (int,)
