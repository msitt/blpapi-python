# __init__.py

# pylint: disable=missing-docstring,redefined-builtin,wildcard-import
# pylint: disable=raise-missing-from

# pylint: disable=no-member
import platform
if platform.system().lower() == 'windows':
    import glob
    import os

    blpapi_dir = os.path.abspath(os.path.dirname(__file__))
    is_64bit = platform.architecture()[0].startswith("64")
    dll_glob = "*64.dll" if is_64bit else "*32.dll"

    # Attempt to read dlls at the root of blpapi installation
    # We do not copy the dlls for the source distribution so they are not
    # guaranteed to be there.
    # In that case, the next block is going to be skipped entirely.
    for filename in glob.glob(os.path.join(blpapi_dir, dll_glob)):
        from ctypes import CDLL
        CDLL(os.path.abspath(filename))

try:
    from .internals import CorrelationId
except ImportError as error:
    # The most likely reason for a failure here is a failure to locate the
    # shared object for the C++ library. Provide a meaningful error message.
    from .debug import debug_load_error
    raise debug_load_error(error)

from .abstractsession import AbstractSession
from .auth import AuthOptions, AuthUser
from .constant import Constant, ConstantList
from .datatype import DataType
from .datetime import FixedOffset
from .element import Element
from .event import Event, EventQueue
from .eventdispatcher import EventDispatcher
from .eventformatter import EventFormatter
from .exception import *
from .identity import Identity
from .logging import Logger
from .message import Message
from .name import Name
from .names import Names
from .providersession import ProviderSession, ServiceRegistrationOptions
from .request import Request
from .requesttemplate import RequestTemplate
from .resolutionlist import ResolutionList
from .schema import SchemaElementDefinition, SchemaStatus, SchemaTypeDefinition
from .service import Service, Operation
from .session import Session
from .sessionoptions import SessionOptions, TlsOptions
from .subscriptionlist import SubscriptionList
from .topic import Topic
from .topiclist import TopicList
from .zfputil import ZfpUtil
from .version import __version__, version, cpp_sdk_version, print_version

# blpapi.test module
from .test import *

__copyright__ = """
Copyright 2012. Bloomberg Finance L.P.

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
