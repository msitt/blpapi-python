# debug.py

"""Provide debugging information for import errors"""

import platform
import os
from locale import getpreferredencoding

from .debug_environment import get_env_diagnostics


def debug_load_error(error: ImportError) -> ImportError:
    """Called when the module fails to import "internals".
    Returns ImportError with some debugging message.
    """
    # Try to load just the version.py
    version_imported = True
    import_error = ""
    try:
        from .version import version, cpp_sdk_version, expected_cpp_sdk_version
    except ImportError as version_error:
        import_error = _version_load_error(version_error)
        version_imported = False

    if version_imported:
        # If the version loading succeeds, the most likely reason for a failure
        # is a mismatch between C++ and Python SDKs.
        import_error = _version_mismatch_error(
            error, version(), cpp_sdk_version(), expected_cpp_sdk_version()
        )

    # Environment diagnostics currently only works for windows
    if platform.system().lower() == "windows":
        env_diagnostics = get_env_diagnostics()

        full_error_msg = f"""
---------------------------- ENVIRONMENT -----------------------------
{env_diagnostics}
----------------------------------------------------------------------
{import_error}
"""
    else:
        full_error_msg = import_error

    # Also output the error message to a file if BLPAPI_DIAGNOSTICS is set
    diagnostics_path_env_var = "BLPAPI_DIAGNOSTICS"
    if diagnostics_path_env_var in os.environ:
        diagnostics_path = os.environ[diagnostics_path_env_var]
        try:
            with open(
                diagnostics_path, "w", encoding=getpreferredencoding()
            ) as f:
                f.write(full_error_msg)
        except IOError:
            print(
                "Failed to write to path defined by"
                f' {diagnostics_path_env_var}: "{diagnostics_path}"'
            )

    return ImportError(full_error_msg)


def _linker_env() -> str:
    """Return the name of the right environment variable for linking in the
    current platform.
    """
    s = platform.system()
    if s == "Windows":
        env = "PATH"
    elif s == "Darwin":
        env = "DYLD_LIBRARY_PATH"
    else:
        env = "LD_LIBRARY_PATH"
    return env


def _version_load_error(error: ImportError) -> str:
    """Called when the module fails to import "versionhelper".
    Returns some debugging message.
    """
    msg = f"""{error}

Could not open the C++ SDK library.

Download and install the latest C++ SDK from:

    http://www.bloomberg.com/professional/api-library
"""

    if "add_dll_directory" in dir(os):
        msg += """
If the C++ SDK is already installed, Python 3.8+ on Windows requires that the
path to the library is added to 'add_dll_directory', i.e.:

    with os.add_dll_directory('<path to blpapi dlls>'):
        import blpapi
"""
    else:
        msg += f"""
If the C++ SDK is already installed, please ensure that the path to the library
was added to {_linker_env()} before entering the interpreter.

If you are trying to build and install from source, you may instead find it
easier to simply install the wheel directly from pip, which will come bundled
with a compatible version of the C++ SDK. Simply run:
`pip install blpapi --index-url=https://bcms.bloomberg.com/pip/simple`

"""
    return msg


def _version_mismatch_error(
    error: ImportError,
    py_version: str,
    cpp_version: str,
    expected_cpp_sdk_version: str,
) -> str:
    """Called when "import version" succeeds after "import internals" fails
    Returns some debugging message.
    """
    msg = f"""{error}

Mismatch between C++ and Python SDK libraries.

Python SDK version    {py_version}
Found C++ SDK version {cpp_version}
Expected C++ SDK version >= {expected_cpp_sdk_version}

Download and install the latest C++ SDK from:

    http://www.bloomberg.com/professional/api-library

If a recent version of the C++ SDK is already installed, please ensure that the
path to the library is added to {_linker_env()} before entering the interpreter.

If you are trying to build and install from source, you may instead find it
easier to simply install the wheel directly from pip, which will come bundled
with a compatible version of the C++ SDK. Simply run:
`pip install blpapi --index-url=https://bcms.bloomberg.com/pip/simple`

"""
    return msg
