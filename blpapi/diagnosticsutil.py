"""@PURPOSE: Provide api to access diagnostics information
on the blpapi library
@DESCRIPTION: This component provide a collection of functions which give
access to various sets of diagnostics information on the 'blpapi' library."""

from . import internals

def memoryInfo():
    """Return the string describing the 'blpapi' library's memory usage; the
    format of the string is platform-specific."""
    return internals.blpapi_DiagnosticsUtil_memoryInfo_wrapper()
