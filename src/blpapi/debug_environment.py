"""
Print various potentially useful information to debug environment setup
related issues
"""

import platform
import sys
import os
import pkgutil
import functools
from typing import Callable
from locale import getpreferredencoding

from ctypes import util
from io import StringIO


def _path_diagnostics(print_to_str: Callable[[str], None]) -> None:
    # Information for PATH related issues
    print_to_str(
        "blpapi 64-bit will be loaded from:"
        f' "{util.find_library("blpapi3_64")}"'
    )
    print_to_str(
        "blpapi 32-bit will be loaded from:"
        f' "{util.find_library("blpapi3_32")}"'
    )
    print_to_str("System PATH: (* marks locations where blpapi was found)")
    for p in os.environ["PATH"].split(os.pathsep):
        if p:  # Skip empty entries
            dll_32 = os.path.join(p, "blpapi3_32.dll")
            dll_64 = os.path.join(p, "blpapi3_64.dll")
            found_blpapi_dll = os.path.isfile(dll_32) or os.path.isfile(dll_64)
            print_to_str(f'  {"*" if found_blpapi_dll else " "} "{p}"')
    print_to_str("")


def _add_dll_directory_diagnostics(
    print_to_str: Callable[[str], None]
) -> None:
    print_to_str("This Python version does not use PATH to find dlls")


def get_env_diagnostics() -> str:
    """
    Get various potentially useful information to debug environment setup
    related issues
    """

    strIO = StringIO()
    print_to_str = functools.partial(print, file=strIO)

    # General information about the platform
    print_to_str("Platform:", platform.platform())
    print_to_str("Architecture:", platform.architecture())
    print_to_str("Python:", sys.version)
    print_to_str("Python implementation:", platform.python_implementation())
    print_to_str()

    if "add_dll_directory" not in dir(os):
        _path_diagnostics(print_to_str)
    else:
        _add_dll_directory_diagnostics(print_to_str)
    # Check if the blpapi package has been installed. If not,
    # include information about the current python environment
    blpapi_package_found = False
    for i in pkgutil.iter_modules():
        if i[1] == "blpapi":
            # some modules don't have a .path (e.g. MetaPathFinder)
            print_to_str(f'blpapi package at: "{i[0].path}"')  # type: ignore
            blpapi_package_found = True

    if not blpapi_package_found:
        print_to_str("ERROR: Failed to find the blpapi package")
        print_to_str(f'Python prefix: "{sys.prefix}"')
        print_to_str("Python path:")
        for p in sys.path:
            print_to_str(f'    "{p}"')
    print_to_str()

    # There is currently a known issue where attempting to import blpapi
    # from the local directory (e.g. if trying to run a script in the root
    # of our repository) will fail. Check that this is not the case.
    print_to_str(f'Current directory: "{os.getcwd()}"')
    if os.path.isfile(os.path.join(".", "blpapi", "__init__.py")):
        print_to_str("WARNING: Using the blpapi module from current path")
        print_to_str(
            "    CWD files:",
            ", ".join([x for x in os.listdir(".") if os.path.isfile(x)]),
        )
        print_to_str(
            "    CWD dirs:",
            ", ".join([x for x in os.listdir(".") if not os.path.isfile(x)]),
        )

    return strIO.getvalue()


if __name__ == "__main__":
    env_diagnostics = get_env_diagnostics()

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding=getpreferredencoding()) as f:
            print(env_diagnostics, file=f)
    else:
        print(env_diagnostics)
