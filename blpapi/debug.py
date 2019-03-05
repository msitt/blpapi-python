# debug.py

"""Provide debugging information for import errors"""

import platform

def debug_load_error(error):
    """Called when the module fails to import "internals".
    Returns ImportError with some debugging message.
    """
    # Try to load just the version.py
    try:
        from .version import version, cpp_sdk_version
    except ImportError as version_error:
        return _version_load_error(version_error)

    # If the version loading succeeds, the most likely reason for a failure
    # is a mismatch between C++ and Python SDKs.
    return _version_mismatch_error(error, version(), cpp_sdk_version())

def _linker_env():
    """Return the name of the right environment variable for linking in the
    current platform.
    """
    s = platform.system()
    if s == 'Windows':
        env = 'PATH'
    elif s == 'Darwin':
        env = 'DYLD_LIBRARY_PATH'
    else:
        env = 'LD_LIBRARY_PATH'
    return env

def _version_load_error(error):
    """Called when the module fails to import "versionhelper".
    Returns ImportError with some debugging message.
    """
    msg = """%s

Could not open the C++ SDK library.

Download and install the latest C++ SDK from:

    http://www.bloomberg.com/professional/api-library

If the C++ SDK is already installed, please ensure that the path to the library
was added to %s before entering the interpreter.

""" % (str(error), _linker_env())
    return ImportError(msg)


def _version_mismatch_error(error, py_version, cpp_version):
    """Called when "import version" succeeds after "import internals" fails
    Returns ImportError with some debugging message.
    """
    msg = """%s

Mismatch between C++ and Python SDK libraries.

Python SDK version    %s
Found C++ SDK version %s

Download and install the latest C++ SDK from:

    http://www.bloomberg.com/professional/api-library

If a recent version of the C++ SDK is already installed, please ensure that the
path to the library is added to %s before entering the interpreter.

""" % (str(error), py_version, cpp_version, _linker_env())
    return ImportError(msg)
