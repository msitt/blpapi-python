# datetime.py

"""Utilities that deal with blpapi.Datetime data type"""

import datetime as _dt
from typing import Any, Optional

from .typehints import AnyPythonDatetime, BlpapiDatetime
from . import internals
from . import utils
from . import typehints  # pylint: disable=unused-import


# pylint: disable=no-member
class FixedOffset(_dt.tzinfo, metaclass=utils.MetaClassForClassesWithEnums):
    """Time zone information.

    Represents time zone information to be used with Python standard library
    datetime classes.

    This class is intended to be used as ``tzinfo`` for Python standard library
    :class:`datetime.datetime` and :class:`datetime.time` classes. These
    classes are accepted by the blpapi package to set :attr:`~DataType.DATE`,
    :attr:`~DataType.TIME` or :attr:`~DataType.DATETIME` elements. For example,
    the :attr:`~DataType.DATETIME` element of a request could be set as::

        value = datetime.datetime(1941, 6, 22, 4, 0, tzinfo=FixedOffset(4*60))
        request.getElement("last_trade").setValue(value)

    The :attr:`~DataType.TIME` element could be set in a similar way::

        value = datetime.time(9, 0, 1, tzinfo=FixedOffset(-5*60))
        request.getElement("session_open").setValue(value)

    Note that you could use any other implementations of
    :class:`datetime.tzinfo` with BLPAPI-Py, for example the widely used
    ``pytz`` package (https://pypi.python.org/pypi/pytz/).

    For more details see datetime module documentation at
    https://docs.python.org/library/datetime.html
    """

    def __init__(self, offsetInMinutes: int = 0) -> None:
        """
        Args:
            offsetInMinutes: Offset from UTC in minutes

        Creates an object that implements :class:`datetime.tzinfo` interface
        and represents a timezone with the specified ``offsetInMinutes`` from
        UTC.
        """
        self.__offset = _dt.timedelta(minutes=offsetInMinutes)

    def utcoffset(self, dt: Optional[_dt.datetime]) -> _dt.timedelta:
        del dt
        return self.__offset

    def dst(
        self, dt: Optional[_dt.datetime]
    ) -> _dt.timedelta:  # pylint: disable=no-self-use
        del dt
        return _dt.timedelta(0)

    def tzname(self, dt: Optional[_dt.datetime]) -> _dt.timedelta:  # type: ignore # superclass returns str, but .__offset is a timedelta
        del dt
        return self.__offset

    def getOffsetInMinutes(self) -> int:
        """
        Returns:
            Offset from UTC in minutes
        """
        return self.__offset.days * 24 * 60 + self.__offset.seconds // 60

    def __hash__(self) -> int:
        """x.__hash__() <==> hash(x)"""
        return self.getOffsetInMinutes()

    def __eq__(self, other: "FixedOffset") -> bool:  # type: ignore # mypy wants us to accept arbitrary object and check isinstance()
        """Let the equality operator work based on the time delta."""
        return self.getOffsetInMinutes() == other.getOffsetInMinutes()

    def __lt__(self, other: "FixedOffset") -> bool:
        """Let the comparison operator work based on the time delta."""
        return self.getOffsetInMinutes() < other.getOffsetInMinutes()

    def __le__(self, other: "FixedOffset") -> bool:
        """Let the comparison operator work based on the time delta."""
        return self.getOffsetInMinutes() <= other.getOffsetInMinutes()


# UTC timezone
UTC = FixedOffset(0)


class _DatetimeUtil(object):
    """Utility methods that deal with BLPAPI dates and times."""

    @staticmethod
    def convertToNative(
        blpapiDatetimeObj: BlpapiDatetime,
    ) -> AnyPythonDatetime:
        """Convert BLPAPI Datetime object to a suitable Python object."""

        isHighPrecision = isinstance(
            blpapiDatetimeObj, internals.blpapi_HighPrecisionDatetime_tag
        )

        if not isHighPrecision:
            raise ValueError(
                "Datetime object is not high precision", blpapiDatetimeObj
            )

        blpapiDatetime = blpapiDatetimeObj.datetime
        parts = blpapiDatetime.parts
        hasDate = (
            parts & internals.DATETIME_DATE_PART
            == internals.DATETIME_DATE_PART
        )
        hasTime = parts & internals.DATETIME_TIMEFRACSECONDS_PART != 0
        microsecs = (
            (
                blpapiDatetime.milliSeconds * 1000
                + blpapiDatetimeObj.picoseconds // 1000 // 1000
            )
            if parts & internals.DATETIME_FRACSECONDS_PART
            else 0
        )

        return _DatetimeUtil._convertToNativeTypeHelper(
            hasDate, hasTime, blpapiDatetime, microsecs
        )

    @staticmethod
    def convertToNativeNotHighPrecision(
        blpapiDatetime: BlpapiDatetime,
    ) -> AnyPythonDatetime:
        """Convert BLPAPI Datetime object to a suitable Python object.
        This version should only be used for logging callback which does not
        provide a high precision datetime alternative."""

        parts = blpapiDatetime.parts
        hasDate = (
            parts & internals.DATETIME_DATE_PART
            == internals.DATETIME_DATE_PART
        )
        hasTime = (
            parts & internals.DATETIME_TIME_PART
            == internals.DATETIME_TIME_PART
        )
        microsecs = (
            blpapiDatetime.milliSeconds * 1000
            if parts & internals.DATETIME_MILLISECONDS_PART
            else 0
        )
        return _DatetimeUtil._convertToNativeTypeHelper(
            hasDate, hasTime, blpapiDatetime, microsecs
        )

    @staticmethod
    def _convertToNativeTypeHelper(
        hasDate: bool,
        hasTime: bool,
        blpapiDatetime: BlpapiDatetime,
        microsecs: int,
    ) -> AnyPythonDatetime:
        parts = blpapiDatetime.parts
        tzinfo = (
            FixedOffset(blpapiDatetime.offset)
            if parts & internals.DATETIME_OFFSET_PART
            else None
        )

        if hasDate and hasTime:
            return _dt.datetime(
                blpapiDatetime.year,
                blpapiDatetime.month,
                blpapiDatetime.day,
                blpapiDatetime.hours,
                blpapiDatetime.minutes,
                blpapiDatetime.seconds,
                microsecs,
                tzinfo,
            )
        elif hasDate:
            # Skip an offset, because it's not informative if there is a
            # date without time
            return _dt.date(
                blpapiDatetime.year, blpapiDatetime.month, blpapiDatetime.day
            )
        elif hasTime:
            return _dt.time(
                blpapiDatetime.hours,
                blpapiDatetime.minutes,
                blpapiDatetime.seconds,
                microsecs,
                tzinfo,
            )

        raise ValueError(
            "Blpapi datetime object is invalid: missing"
            " both date and time parts"
        )

    @staticmethod
    def isDatetime(dtime: Any) -> bool:
        """Return True if the parameter is one of Python date/time objects."""
        return isinstance(dtime, (_dt.datetime, _dt.date, _dt.time))

    @staticmethod
    def convertToBlpapi(dtime: AnyPythonDatetime) -> BlpapiDatetime:
        "Convert a Python date/time object to a BLPAPI Datetime object." ""
        highPrecDatetime = internals.blpapi_HighPrecisionDatetime_tag()
        res = highPrecDatetime.datetime
        offset = None
        if isinstance(dtime, _dt.datetime):
            offset = dtime.utcoffset()
            res.year = dtime.year
            res.month = dtime.month
            res.day = dtime.day
            res.hours = dtime.hour
            res.minutes = dtime.minute
            res.seconds = dtime.second
            (res.milliSeconds, highPrecDatetime.picoseconds) = divmod(
                dtime.microsecond, 1000
            )
            highPrecDatetime.picoseconds *= 1000 * 1000
            res.parts = (
                internals.DATETIME_DATE_PART
                | internals.DATETIME_TIMEFRACSECONDS_PART
            )
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
            (res.milliSeconds, highPrecDatetime.picoseconds) = divmod(
                dtime.microsecond, 1000
            )
            highPrecDatetime.picoseconds *= 1000 * 1000
            res.parts = internals.DATETIME_TIMEFRACSECONDS_PART
        else:
            raise TypeError(
                "Datetime can be created only from \
datetime.datetime, datetime.date or datetime.time"
            )
        if offset is not None:
            offsetInMinutes = int(offset.total_seconds() // 60)
            res.offset = offsetInMinutes
            res.parts |= internals.DATETIME_OFFSET_PART
        return highPrecDatetime


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
