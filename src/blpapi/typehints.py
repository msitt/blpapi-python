# typehints.py

"""Type definitions for common type hints"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blpapi import AbstractSession
    from blpapi import AuthOptions
    from blpapi import ConstantList
    from blpapi import CorrelationId
    from blpapi import Element
    from blpapi import Event
    from blpapi import EventDispatcher
    from blpapi import EventQueue
    from blpapi import Message
    from blpapi import Name
    from blpapi import Identity
    from blpapi import ResolutionList
    from blpapi import Request
    from blpapi import SchemaElementDefinition
    from blpapi import Service
    from blpapi import Session
    from blpapi import SessionOptions
    from blpapi import SubscriptionList
    from blpapi import TlsOptions
    from blpapi import Topic
    from blpapi import TopicList

import datetime
from typing import Union, Any

AnyPythonDatetime = Union[datetime.datetime, datetime.date, datetime.time]
BlpapiNameOrIndex = Union["Name", int]
SupportedElementTypes = Union[
    "Name", str, bytes, bool, int, float, AnyPythonDatetime, None
]
# placeholders for opaque handles
BlpapiAbstractSessionHandle = Any
BlpapiAuthOptionsHandle = Any
BlpapiAuthAppHandle = Any
BlpapiAuthTokenHandle = Any
BlpapiAuthUserHandle = Any
BlpapiConstantHandle = Any
BlpapiConstantListHandle = Any
BlpapiDatetime = Union[Any, "blpapi_HighPrecisionDatetime_tag"]  # type: ignore
BlpapiElementHandle = Any
BlpapiEventHandle = Any
BlpapiIdentityHandle = Any
BlpapiMessageHandle = Any
BlpapiMessageFormatterHandle = Any
BlpapiMessagePropertiesHandle = Any
BlpapiNameHandle = Any
BlpapiOperationHandle = Any
BlpapiProviderSessionHandle = Any
BlpapiRequestHandle = Any
BlpapiRequestTemplateHandle = Any
BlpapiSchemaHandle = Any
BlpapiSchemaElementDefinitionHandle = Any
BlpapiSchemaTypeDefinitionHandle = Any
BlpapiServiceHandle = Any
BlpapiSessionHandle = Any
BlpapiTlsOptionsHandle = Any
BlpapiTopicHandle = Any
