# coding: utf-8

"""@PURPOSE: Provide a C call to register a call back for logging

@DESCRIPTION: This component provides a function that is used to
 register a callback for logging"""

from __future__ import absolute_import
from blpapi import internals
from . import utils
from .compat import with_metaclass
from .datetime import _DatetimeUtil

@with_metaclass(utils.MetaClassForClassesWithEnums)
class Logger:
    """This utility class provides a namespace for functions to test the
    logging configuration."""

    # Different logging levels
    SEVERITY_OFF = internals.blpapi_Logging_SEVERITY_OFF
    SEVERITY_FATAL = internals.blpapi_Logging_SEVERITY_FATAL
    SEVERITY_ERROR = internals.blpapi_Logging_SEVERITY_ERROR
    SEVERITY_WARN = internals.blpapi_Logging_SEVERITY_WARN
    SEVERITY_INFO = internals.blpapi_Logging_SEVERITY_INFO
    SEVERITY_DEBUG = internals.blpapi_Logging_SEVERITY_DEBUG
    SEVERITY_TRACE = internals.blpapi_Logging_SEVERITY_TRACE

    loggerCallbacksLocal = [] # needed for temporary ref. holding

    @staticmethod
    def registerCallback(callback, thresholdSeverity=SEVERITY_INFO):
        """Register the specified 'callback' that will be called for all log
        messages with severity greater than or equal to the specified
        'thresholdSeverity'.  The callback needs to be registered before the
        start of all sessions.  If this function is called multiple times, only
        the last registered callback will take effect. An exception of type
        'RuntimeError' will be thrown if 'callback' cannot be registered.
        If callback is None, any existing callback shall be removed."""
        def callbackWrapper(threadId, severity, ts, category, message):
            dt = _DatetimeUtil.convertToNativeNotHighPrecision(ts)
            callback(threadId, severity, dt, category, message)

        callbackRef = None if callback is None else callbackWrapper
        # we store a reference to callbackWrapper (that binds callback)
        # for as long as it may be needed, i.e. until gc or re-register
        Logger.loggerCallbacksLocal.append(callbackRef)
        err_code = internals.setLoggerCallbackWrapper(
            callbackRef, thresholdSeverity)

        if len(Logger.loggerCallbacksLocal) > 1:
            # we have a new cb now, let the previous one go
            Logger.loggerCallbacksLocal.pop(0)

        if err_code == -1:
            raise ValueError("parameter must be a function")
        if err_code == -2:
            raise RuntimeError("unable to register callback")

    @staticmethod
    def logTestMessage(severity):
        """Log a test message at the specified 'severity'.
        Note that this function is intended for testing
        of the logging configuration only."""
        internals.blpapi_Logging_logTestMessage(severity)
