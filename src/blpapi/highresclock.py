# coding: utf-8
"""Support highres clock"""

from blpapi import internals
from blpapi.datetime import _DatetimeUtil, UTC
import datetime


def now(tzinfo: datetime.tzinfo = UTC) -> datetime.datetime:
    """Return the current time using the same clock as is used to measure the
    'timeReceived' value on incoming messages; note that this is *not*
    necessarily the same clock as is accessed by calls to 'datetime.now'. The
    resulting datetime will be represented using the specified 'tzinfo'.
    """
    err_code, time_point = internals.blpapi_HighResolutionClock_now()
    if err_code != 0:
        raise RuntimeError("High resolution clock error")
    original = internals.blpapi_HighPrecisionDatetime_fromTimePoint_wrapper(
        time_point
    )
    native = _DatetimeUtil.convertToNative(original)
    return native.astimezone(tzinfo)  # type: ignore
