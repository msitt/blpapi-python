# __init__.py

from __future__ import absolute_import

from .internals import CorrelationId

from .abstractsession import AbstractSession
from .constant import Constant, ConstantList
from .datetime import FixedOffset
from .datatype import DataType
from .element import Element
from .event import Event, EventQueue
from .eventdispatcher import EventDispatcher
from .eventformatter import EventFormatter
from .exception import *
from .identity import Identity
from .message import Message
from .name import Name
from .providersession import ProviderSession, ServiceRegistrationOptions
from .request import Request
from .resolutionlist import ResolutionList
from .schema import SchemaElementDefinition, SchemaStatus, SchemaTypeDefinition
from .service import Service
from .session import Session
from .sessionoptions import SessionOptions
from .subscriptionlist import SubscriptionList
from .topic import Topic
from .topiclist import TopicList

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
