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

from . import utils
from . import internals
from .compat import with_metaclass
from .exception import _ExceptionUtil
from .sessionoptions import SessionOptions

# pylint: disable=too-few-public-methods,useless-object-inheritance

@with_metaclass(utils.MetaClassForClassesWithEnums)
class ZfpUtil(object):
    """Wrapper for Zero Footprint utilities"""

    REMOTE_8194 = internals.ZFPUTIL_REMOTE_8194
    REMOTE_8196 = internals.ZFPUTIL_REMOTE_8196

    @staticmethod
    def getZfpOptionsForLeasedLines(remote, tlsOptions):
        """Creates a SessionOptions object for applications that leverages
        private leased lines to Bloomberg network. The SessionOptions
        object is only valid for private leased line connectivity. On failure
        (e.g. connectivity issues), an exception is raised.

        This is a costly operation that is preferably called once per
        application.
        """
        sessionOptions = SessionOptions()
        err = internals.blpapi_ZfpUtil_getOptionsForLeasedLines(
            utils.get_handle(sessionOptions),
            utils.get_handle(tlsOptions),
            remote)
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
