# zfputil.py

"""Provide utilities designed for the Zero Footprint solution clients that
leverage private leased lines to the Bloomberg network.

This file defines a 'ZfpUtil' class which is used to prepare session options
for private leased lines.

Usage
----

The following snippet shows how to use ZfpUtil to start a Session.

tlsOptions = blpapi.TlsOptions.createFromFiles( ... )
sessionOptions = blpapi.ZfpUtil.getZfpOptionsForLeasedLines(
    blpapi.ZfpUtil.REMOTE_8194,
    tlsOptions)

sessionOptions.setAuthenticationOptions( ... )

session = blpapi.Session(sessionOptions)
session.start()
"""
import os
import sys
from . import utils
from . import internals
from . import typehints  # pylint: disable=unused-import
from .exception import _ExceptionUtil
from .sessionoptions import SessionOptions
from .version import version


# pylint: disable=too-few-public-methods
class ZfpUtil(metaclass=utils.MetaClassForClassesWithEnums):
    """Utility used to prepare :class:`SessionOptions` for private leased
    lines.

    The following snippet shows how to use :class:`ZfpUtil` to start a
    ``Session``::

        tlsOptions = blpapi.TlsOptions.createFromFiles( ... )
        sessionOptions = blpapi.ZfpUtil.getZfpOptionsForLeasedLines(
            blpapi.ZfpUtil.REMOTE_8194,
            tlsOptions)

        sessionOptions.setAuthenticationOptions( ... )

        session = blpapi.Session(sessionOptions)
        session.start()
    """

    REMOTE_8194 = internals.ZFPUTIL_REMOTE_8194
    REMOTE_8196 = internals.ZFPUTIL_REMOTE_8196

    @staticmethod
    def getZfpOptionsForLeasedLines(
        remote: int, tlsOptions: "typehints.TlsOptions"
    ) -> "typehints.SessionOptions":
        """Creates a :class:`SessionOptions` object for applications that
        leverage private leased lines to the Bloomberg network.

        Args:
            remote (int): Type of the remote to connect to
            tlsOptions (TlsOptions): Tls options to use when connecting

        Returns:
            SessionOptions: :class:`SessionOptions` object for applications
            that leverage private leased lines to the Bloomberg network.

        Raises:
            Exception: If failed to obtain the session options

        Note:
            The :class:`SessionOptions` object is only valid for private leased
            line connectivity.

        Note:
            This is a costly operation that is preferably called once per
            application.
        """
        # https://docs.python.org/3/library/sys.html#sys.argv
        # argv[0] is the script name (it is operating system dependent whether
        # this is a full pathname or not). If the command was executed using
        # the -c command line option to the interpreter, argv[0] is set to the
        # string '-c'. If no script name was passed to the Python interpreter,
        # argv[0] is the empty string.
        taskName = os.path.basename(sys.argv[0])
        if taskName and taskName != "-c":
            internals.blpapi_UserAgentInfo_setUserTaskName(taskName)
        internals.blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion(
            "Python", version()
        )

        sessionOptions = SessionOptions()
        err = internals.blpapi_ZfpUtil_getOptionsForLeasedLines(
            utils.get_handle(sessionOptions),
            utils.get_handle(tlsOptions),
            remote,
        )
        _ExceptionUtil.raiseOnError(err)

        return sessionOptions


__copyright__ = """
Copyright 2019. Bloomberg Finance L.P.

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
