# coding: utf-8

"""@PURPOSE: Provide a C call to register a call back for logging

@DESCRIPTION: This component provides a function that is used to
 register a callback for logging"""

from typing import Callable, List
from blpapi import internals
from datetime import datetime
from . import utils
from .datetime import _DatetimeUtil
from .typehints import AnyPythonDatetime

class Logger(metaclass=utils.MetaClassForClassesWithEnums):
    """This utility class provides a namespace for functions to test the
    logging configuration."""

    # Different logging levels
    SEVERITY_OFF = internals.blpapi_Logging_SEVERITY_OFF # type: ignore
    SEVERITY_FATAL = internals.blpapi_Logging_SEVERITY_FATAL # type: ignore
    SEVERITY_ERROR = internals.blpapi_Logging_SEVERITY_ERROR # type: ignore
    SEVERITY_WARN = internals.blpapi_Logging_SEVERITY_WARN # type: ignore
    SEVERITY_INFO = internals.blpapi_Logging_SEVERITY_INFO # type: ignore
    SEVERITY_DEBUG = internals.blpapi_Logging_SEVERITY_DEBUG # type: ignore
    SEVERITY_TRACE = internals.blpapi_Logging_SEVERITY_TRACE # type: ignore

    loggerCallbacksLocal: List[Callable] = [] # needed for temp. ref. holding

    @staticmethod
    def registerCallback(callback:
                         Callable[[int, int, AnyPythonDatetime, str, str], None],
                         thresholdSeverity: int = SEVERITY_INFO) -> None:
        """Register the specified 'callback' that will be called for all log
        messages with severity greater than or equal to the specified
        'thresholdSeverity'.  The callback needs to be registered before the
        start of all sessions.  If this function is called multiple times, only
        the last registered callback will take effect. An exception of type
        'RuntimeError' will be thrown if 'callback' cannot be registered.
        If callback is None, any existing callback shall be removed."""
        def callbackWrapper(threadId: int,
                            severity: int,
                            ts: datetime,
                            category: str,
                            message: str):
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
    def logTestMessage(severity: int) -> None:
        """Log a test message at the specified 'severity'.
        Note that this function is intended for testing
        of the logging configuration only."""
        internals.blpapi_Logging_logTestMessage(severity)
