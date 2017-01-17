# datetime.py

"""Utilities that deal with blpapi.Datetime data type"""

from __future__ import absolute_import

from . import internals
from . import utils

import datetime as _dt


class FixedOffset(_dt.tzinfo):
    """Time zone information.

    Represents time zone information to be used with Python standard library
    datetime classes.

    FixedOffset(offsetInMinutes) creates an object that implements
    datetime.tzinfo interface and represents a timezone with the specified
    'offsetInMinutes' from UTC.

    This class is intended to be used as 'tzinfo' for Python standard library
    datetime.datetime and datetime.time classes. These classes are accepted by
    the blpapi package to set DATE, TIME or DATETIME elements. For example, the
    DATETIME element of a request could be set as:

        value = datetime.datetime(1941, 6, 22, 4, 0, tzinfo=FixedOffset(4*60))
        request.getElement("last_trade").setValue(value)

    The TIME element could be set in a similar way:

        value = datetime.time(9, 0, 1, tzinfo=FixedOffset(-5*60))
        request.getElement("session_open").setValue(value)

    Note that you could use any other implementations of datetime.tzinfo with
    BLPAPI-Py, for example the widely used 'pytz' package
    (http://pypi.python.org/pypi/pytz/).

    For more details see datetime module documentation at
    http://docs.python.org/library/datetime.html

    """

    def __init__(self, offsetInMinutes=0):
        _dt.tzinfo.__init__(self)
        self.__offset = _dt.timedelta(minutes=offsetInMinutes)

    def utcoffset(self, unused):
        return self.__offset

    def dst(self, unused):
        return FixedOffset._dt.timedelta(0)

    def getOffsetInMinutes(self):
        return self.__offset.days * 24 * 60 + self.__offset.seconds / 60

    def __hash__(self):
        """x.__hash__() <==> hash(x)"""
        return self.getOffsetInMinutes()

    def __cmp__(self, other):
        """Let the comparison operations work based on the time delta."""
        return cmp(self.getOffsetInMinutes(), other.getOffsetInMinutes())

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums


class _DatetimeUtil(object):
    """Utility methods that deal with BLPAPI dates and times."""
    @staticmethod
    def convertToNative(blpapiDatetime):
        """Convert BLPAPI Datetime object to a suitable Python object."""
        parts = blpapiDatetime.parts
        hasDate = parts & internals.DATETIME_DATE_PART == \
            internals.DATETIME_DATE_PART
        hasTime = parts & internals.DATETIME_TIME_PART == \
            internals.DATETIME_TIME_PART
        mlsecs = blpapiDatetime.milliSeconds * 1000 if parts & \
            internals.DATETIME_MILLISECONDS_PART else 0
        tzinfo = FixedOffset(blpapiDatetime.offset) if parts & \
            internals.DATETIME_OFFSET_PART else None
        if hasDate:
            if hasTime:
                return _dt.datetime(blpapiDatetime.year,
                                    blpapiDatetime.month,
                                    blpapiDatetime.day,
                                    blpapiDatetime.hours,
                                    blpapiDatetime.minutes,
                                    blpapiDatetime.seconds,
                                    mlsecs,
                                    tzinfo)
            else:
                # Skip an offset, because it's not informative in case of
                # there is a date without the time
                return _dt.date(blpapiDatetime.year,
                                blpapiDatetime.month,
                                blpapiDatetime.day)
        else:
            if not hasTime:
                raise ValueError("Datetime object misses both time and date \
parts", blpapiDatetime)
            return _dt.time(blpapiDatetime.hours,
                            blpapiDatetime.minutes,
                            blpapiDatetime.seconds,
                            mlsecs,
                            tzinfo)

    @staticmethod
    def isDatetime(dtime):
        """Return True if the parameter is one of Python date/time objects."""
        return isinstance(dtime, (_dt.datetime, _dt.date, _dt.time))

    @staticmethod
    def convertToBlpapi(dtime):
        "Convert a Python date/time object to a BLPAPI Datetime object."""
        res = internals.blpapi_Datetime_tag()
        offset = None
        if isinstance(dtime, _dt.datetime):
            offset = dtime.utcoffset()
            res.year = dtime.year
            res.month = dtime.month
            res.day = dtime.day
            res.hours = dtime.hour
            res.minutes = dtime.minute
            res.seconds = dtime.second
            res.milliSeconds = dtime.microsecond / 1000
            res.parts = internals.DATETIME_DATE_PART | \
                internals.DATETIME_TIMEMILLI_PART
        elif isinstance(dtime, _dt.date):
            res.year = dtime.year
            res.month = dtime.month
            res.day = dtime.day
            res.parts = internals.DATETIME_DATE_PART
        elif isinstance(dtime, _dt.time):
            offset = dtime.utcoffset()
            res.hours = dtime.hour
            res.minutes = dtime.minute
            res.seconds = dtime.second
            res.milliSeconds = dtime.microsecond / 1000
            res.parts = internals.DATETIME_TIMEMILLI_PART
        else:
            raise TypeError("Datetime could be created only from \
datetime.datetime, datetime.date or datetime.time")
        if offset is not None:
            res.offset = offset.seconds // 60
            res.parts |= internals.DATETIME_OFFSET_PART
        return res

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
