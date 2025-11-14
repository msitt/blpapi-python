# version.py

"""Provide BLPAPI SDK versions"""

from . import internals

__version__ = "3.25.10.1"
__expected_cpp_sdk_version__ = "3.25.10"


def print_version() -> None:
    """Print version information of BLPAPI python module and blpapi C++ SDK"""
    print("Python BLPAPI SDK version: ", version())
    print("C++ BLPAPI SDK version:    ", cpp_sdk_version())
    print("Expected C++ SDK version >= ", expected_cpp_sdk_version())


def version() -> str:
    """
    Returns:
        str: BLPAPI Python module version
    """
    return __version__


def cpp_sdk_version() -> str:
    """
    Returns:
        str: BLPAPI C++ SDK dependency version
    """
    return internals.blpapi_getVersionInfo()


def expected_cpp_sdk_version() -> str:
    """
    Returns:
        str: Expected (minimum compatible) BLPAPI C++ SDK dependency version
    """
    return __expected_cpp_sdk_version__
