# coding: utf-8

"""@PURPOSE: Provide a C call to register a call back for logging

@DESCRIPTION: This component provides a function that is used to
 register a callback for logging"""
import atexit

from typing import Callable, List, Optional, Tuple
from blpapi import internals
from datetime import datetime
from . import utils
from .datetime import _DatetimeUtil
from .typehints import AnyPythonDatetime
from inspect import signature


class Logger(metaclass=utils.MetaClassForClassesWithEnums):
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

    # needed for temp. ref. holding
    loggerCallbacksLocal: List[Tuple[Callable, Callable]] = []

    @staticmethod
    def registerCallback(
        callback: Optional[
            Callable[[int, int, AnyPythonDatetime, str, str], None]
        ],
        thresholdSeverity: int = SEVERITY_INFO,
    ) -> None:
        """Register the specified 'callback' that will be called for all log
        messages with severity greater than or equal to the specified
        'thresholdSeverity'.  The callback needs to be registered before the
        start of all sessions.  If this function is called multiple times, only
        the last registered callback will take effect. An exception of type
        'RuntimeError' will be thrown if 'callback' cannot be registered.
        If callback is None, any existing callback shall be removed."""

        callbackRef = None
        if callback is not None:
            sign = signature(callback)
            # we expect 5 named parameters
            if len(sign.parameters) < 5:
                raise TypeError("Wrong type of callback for logging")

            def callbackWrapper(
                threadId: int,
                severity: int,
                ts: datetime,
                category: bytes,
                message: bytes,
            ) -> None:
                dt = _DatetimeUtil.convertToNativeNotHighPrecision(ts)
                callback(
                    threadId, severity, dt, category.decode(), message.decode()
                )

            callbackRef = callbackWrapper

        err_code, proxy = internals.blpapi_Logging_registerCallback(
            callbackRef, thresholdSeverity
        )

        if err_code == -1:
            raise ValueError("parameter must be a function")
        if err_code == -2:
            raise RuntimeError("unable to register callback")

        # we store a reference to callbackWrapper (that binds callback)
        # for as long as it may be needed, i.e. until gc or re-register
        if callbackRef is not None:
            Logger.loggerCallbacksLocal.append((callbackRef, proxy))

        if len(Logger.loggerCallbacksLocal) > 1:
            # we have a new cb now, let the previous one go
            Logger.loggerCallbacksLocal.pop(0)

        def _deregister_last() -> None:
            Logger.registerCallback(None)

        # we can't possibly keep the python callback alive
        # when the interpreter is dying
        atexit.register(_deregister_last)

    @staticmethod
    def logTestMessage(severity: int) -> None:
        """Log a test message at the specified 'severity'.
        Note that this function is intended for testing
        of the logging configuration only."""
        internals.blpapi_Logging_logTestMessage(severity)
