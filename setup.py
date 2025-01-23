#!/usr/bin/env python

"""
setup.py file for Bloomberg Python SDK
"""

import os
import platform as plat
import re
import codecs
from sys import argv
from shutil import copyfile
from setuptools import setup, Extension


def override_get_tag():
    from wheel.bdist_wheel import bdist_wheel

    # bdist_wheel upon seeing an extension module will (wrongly) assume
    # that not only platform needs to be fixed, but also interpreter.
    # This makes sure we create no-py-specific wheel
    class BDistWheel(bdist_wheel):
        def get_tag(self):
            return (self.python_tag, "none", self.plat_name.replace("-", "_"))

    return {"bdist_wheel": BDistWheel}


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


package_data = {}
cmdclass = {}
if "bdist_wheel" in argv:
    libpath = os.getenv("BLPAPI_DEPENDENCY")
    if libpath:
        libname = os.path.basename(libpath)
        assert os.path.exists(
            libpath
        ), f"Could not find blpapi library at {libpath}"
        # copy, as package_data only supports local files
        copyfile(libpath, f"./src/blpapi/{libname}")
        package_data = {"blpapi": [libname, "py.typed"]}
    else:
        print("BLPAPI_DEPENDENCY environment variable isn't defined")
    cmdclass = override_get_tag()

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

    packages.append("blpapi.internalutils")
# INTERNAL ONLY END


def lib_in_release():
    """Returns the right library folder name for each platform"""
    if platform == "windows":
        return "lib"
    if platform == "linux":
        return "Linux"
    if platform == "darwin":
        return "Darwin"
    raise Exception("Platform '" + platform + "' isn't supported")


blpapiRoot = os.environ.get("BLPAPI_ROOT", ".")
blpapiIncludesVar = os.environ.get("BLPAPI_INCDIR")
blpapiLibVar = os.environ.get("BLPAPI_LIBDIR")

assert blpapiRoot or (blpapiIncludesVar and blpapiLibVar), (
    "BLPAPI_ROOT (or BLPAPI_INCDIR/BLPAPI_LIBDIR) "
    + "environment variable isn't defined"
)
blpapiLibraryPath = blpapiLibVar or os.path.join(blpapiRoot, lib_in_release())
blpapiIncludes = blpapiIncludesVar or os.path.join(blpapiRoot, "include")
is64bit = plat.architecture()[0] == "64bit"
if is64bit:
    blpapiLibraryName = "blpapi3_64"
else:
    blpapiLibraryName = "blpapi3_32"
extraLinkArgs = ["/MANIFEST"] if platform == "windows" else []
blpapi_wrap = Extension(
    "blpapi.ffiutils",
    sources=["src/blpapi/ffi_utils.c"],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_compile_args=[],
    extra_link_args=extraLinkArgs,
)
extensions = [blpapi_wrap]

setup(
    name="blpapi",
    version=find_version_number(),
    author="Bloomberg L.P.",
    author_email="open-tech@bloomberg.net",
    cmdclass=cmdclass,
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
