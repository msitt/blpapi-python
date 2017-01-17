# coding: utf-8

from __future__ import absolute_import
from blpapi import internals
from blpapi.datetime import _DatetimeUtil, UTC

def now(tzinfo=UTC):
    """Return the current time using the same clock as is used to measure the
    'timeReceived' value on incoming messages; note that this is *not*
    necessarily the same clock as is accessed by calls to 'datetime.now'. The
    resulting datetime will be represented using the specified 'tzinfo'.
    """
    original = internals.blpapi_HighResolutionClock_now_wrapper()
    native = _DatetimeUtil.convertToNative(original)
    return native.astimezone(tzinfo)
