# debug.py

"""Provide debugging information for import errors"""

import platform
import os
from locale import getpreferredencoding

from .debug_environment import get_env_diagnostics

def debug_load_error(error):
    """Called when the module fails to import "internals".
    Returns ImportError with some debugging message.
    """
    # Try to load just the version.py
    version_imported = True
    try:
        from .version import version, cpp_sdk_version
    except ImportError as version_error:
        import_error = _version_load_error(version_error)
        version_imported = False

    if version_imported:
        # If the version loading succeeds, the most likely reason for a failure
        # is a mismatch between C++ and Python SDKs.
        import_error = _version_mismatch_error(
            error, version(), cpp_sdk_version())

    # Environment diagnostics currently only works for windows
    if platform.system().lower() == "windows":
        env_diagnostics = get_env_diagnostics()

        full_error_msg = """
---------------------------- ENVIRONMENT -----------------------------
%s
----------------------------------------------------------------------
%s
""" % (env_diagnostics, import_error)
    else:
        full_error_msg = import_error

    # Also output the error message to a file if BLPAPI_DIAGNOSTICS is set
    diagnostics_path_env_var = "BLPAPI_DIAGNOSTICS"
    if diagnostics_path_env_var in os.environ:
        diagnostics_path = os.environ[diagnostics_path_env_var]
        try:
            with open(diagnostics_path, "w", encoding=getpreferredencoding()) as f:
                f.write(full_error_msg)
        except IOError:
            print("Failed to write to path defined by %s: \"%s\"" \
                % (diagnostics_path_env_var, diagnostics_path))

    return ImportError(full_error_msg)


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
""" % str(error)

    if 'add_dll_directory' in dir(os):
        msg += """
If the C++ SDK is already installed, Python 3.8+ on Windows requires that the
path to the library is added to 'add_dll_directory', i.e.:

    with os.add_dll_directory('<path to blpapi dlls>'):
        import blpapi
"""
    else:
        msg += """
If the C++ SDK is already installed, please ensure that the path to the library
was added to %s before entering the interpreter.

""" % _linker_env()
    return msg


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
    return msg
