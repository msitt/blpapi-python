#!/usr/bin/env python

"""
setup.py file for Bloomberg Python SDK
"""

from distutils.core import setup, Extension
import os
import platform as plat
from sys import version
from sys import platform

if version < '2.6':
    raise Exception(
        "Python versions before 2.6 are not supported (current version is " +
	version + ")")
if version >= '3.0':
    raise Exception(
        "Python 3 is not supported (current version is " + version +
        ")")

if not ('BLPAPI_ROOT' in os.environ):
    raise Exception("BLPAPI_ROOT environment variable isn't defined")

is64bit = plat.architecture()[0] == '64bit'
if is64bit:
    blpapiLibraryName = 'blpapi3_64'
else:
    blpapiLibraryName = 'blpapi3_32'

blpapiRoot = os.environ['BLPAPI_ROOT']
blpapiIncludes = os.path.join(blpapiRoot, 'include')

if platform == 'win32':
    blpapiLibraryPath = os.path.join(blpapiRoot, 'lib')
    extraLinkArgs = ['/MANIFEST']

    # Handle the very frequent case when user need to use Visual C++ 2010
    # with Python that wants to use Visual C++ 2008.
    if plat.python_compiler().startswith('MSC v.1500'):
        if (not ('VS90COMNTOOLS' in os.environ)) and \
                ('VS100COMNTOOLS' in os.environ):
            os.environ['VS90COMNTOOLS'] = os.environ['VS100COMNTOOLS']
elif platform == 'linux2':
    blpapiLibraryPath = os.path.join(blpapiRoot, 'Linux')
    extraLinkArgs = []
elif platform == 'darwin':
    blpapiLibraryPath = os.path.join(blpapiRoot, 'Darwin')
    extraLinkArgs = []
else:
    raise Exception("Platform '" + platform + "' isn't supported")

blpapi_wrap = Extension(
    'blpapi._internals',
    sources=['blpapi/internals_wrap.cxx'],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_link_args=extraLinkArgs
)

setup(
    name='blpapi',
    version='3.5.5',
    author='Bloomberg L.P.',
    description='Python SDK for Bloomberg BLPAPI (3.5.5)',
    ext_modules=[blpapi_wrap],
    url='http://open.bloomberg.com/',
    packages=["blpapi"],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: Other/Proprietary License',
        'Topic :: Office/Business :: Financial',
    ],
)
