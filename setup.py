#!/usr/bin/env python

"""
setup.py file for Bloomberg Python SDK
"""

import os
import platform as plat
import re
import codecs

from sys import argv
from setuptools import setup, Extension

os.chdir(os.path.dirname(os.path.realpath(__file__)))
platform = plat.system().lower()


def find_version_number():
    """Load the version number from blpapi/version.py"""
    version_path = os.path.abspath(os.path.join("src", "blpapi", "version.py"))
    version_file = None
    with codecs.open(version_path, "r") as fp:
        version_file = fp.read()

    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def lib_in_release():
    """Returns the right library folder name for each platform"""
    if platform == "windows":
        return "lib"
    if platform == "linux":
        return "Linux"
    if platform == "darwin":
        return "Darwin"
    raise Exception("Platform '" + platform + "' isn't supported")


blpapiRoot = os.environ.get("BLPAPI_ROOT")
blpapiIncludesVar = os.environ.get("BLPAPI_INCDIR")
blpapiLibVar = os.environ.get("BLPAPI_LIBDIR")

assert blpapiRoot or (blpapiIncludesVar and blpapiLibVar), (
    "BLPAPI_ROOT (or BLPAPI_INCDIR/BLPAPI_LIBDIR) "
    + "environment variable isn't defined"
)

is64bit = plat.architecture()[0] == "64bit"
if is64bit:
    blpapiLibraryName = "blpapi3_64"
else:
    blpapiLibraryName = "blpapi3_32"

extraCompileArgs = []
extraLinkArgs = []
package_data = {}
if platform == "linux":
    extraCompileArgs = ["-Werror=implicit-function-declaration"]
elif platform == "windows":
    extraLinkArgs = ["/MANIFEST"]

    # Handle the very frequent case when user need to use Visual C++ 2010
    # with Python that wants to use Visual C++ 2008.
    if plat.python_compiler().startswith("MSC v.1500"):
        if (not "VS90COMNTOOLS" in os.environ) and (
            "VS100COMNTOOLS" in os.environ
        ):
            os.environ["VS90COMNTOOLS"] = os.environ["VS100COMNTOOLS"]

    if "bdist_wheel" in argv:
        # get src/blpapi/*.dll
        package_data = {
            "blpapi": ["blpapi3_64.dll" if is64bit else "blpapi3_32.dll"]
        }

blpapiLibraryPath = blpapiLibVar or os.path.join(blpapiRoot, lib_in_release())
blpapiIncludes = blpapiIncludesVar or os.path.join(blpapiRoot, "include")

blpapi_wrap = Extension(
    "blpapi._internals",
    sources=["src/blpapi/internals_wrap.c"],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_compile_args=extraCompileArgs,
    extra_link_args=extraLinkArgs,
)

versionhelper_wrap = Extension(
    "blpapi._versionhelper",
    sources=["src/blpapi/versionhelper_wrap.c"],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_compile_args=extraCompileArgs,
    extra_link_args=extraLinkArgs,
)

extensions = [blpapi_wrap, versionhelper_wrap]
packages = ["blpapi", "blpapi.test"]

# INTERNAL ONLY START
# see automation/prepare_release.py
internal_build = os.environ.get("BLPAPI_PY_INTERNAL_BUILD", False)
if internal_build:
    internalutils_path = "src/blpapi/internalutils"
    if not (
        os.path.exists(internalutils_path)
        and os.path.isdir(internalutils_path)
    ):
        error_msg = """Tried to build the internal Bloomberg build of the
BLPAPI Python SDK, but failed to find the internalutils subdirectory.

If you are not a Bloomberg developer, this will not work, and you should unset
the BLPAPI_PY_INTERNAL_BUILD environment variable to continue. internalutils
provide some default configurations for use only within Bloomberg networks.

If you are a Bloomberg developer, either unset the BLPAPI_PY_INTERNAL_BUILD
environment variable to build the public release, or ensure the internalutils
subdirectory is present.
"""
        raise ImportError(error_msg)

    internalutils_wrap = Extension(
        "blpapi.internalutils._bindings",
        sources=["src/blpapi/internalutils/bindings_wrap.c"],
        include_dirs=[blpapiIncludes],
        library_dirs=[blpapiLibraryPath],
        libraries=[blpapiLibraryName],
        extra_compile_args=extraCompileArgs,
        extra_link_args=extraLinkArgs,
    )
    extensions.append(internalutils_wrap)
    packages.append("blpapi.internalutils")
# INTERNAL ONLY END

setup(
    name="blpapi",
    version=find_version_number(),
    author="Bloomberg L.P.",
    author_email="open-tech@bloomberg.net",
    description="Python SDK for Bloomberg BLPAPI",
    ext_modules=extensions,
    url="http://www.bloomberglabs.com/api/",
    packages=packages,
    package_dir={"": "src"},
    package_data=package_data,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: Other/Proprietary License",
        "Topic :: Office/Business :: Financial",
    ],
)
