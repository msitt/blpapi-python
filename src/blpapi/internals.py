"""
This module defines C-wrappers for BLPAPI

Copyright 2023. Bloomberg Finance L.P.
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

import platform
import glob
import os
from typing import Optional, List, Callable, Any

# Note: all functions here assume we are given an opaque handle,
# not the python wrapper object, even though paramter names don't have "handle" suffix

from ctypes import (
    CDLL,
    PyDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    byref,
    cast,
    c_char,
    c_char_p,
    c_double,
    c_float,
    c_int,
    c_int16,
    c_int64,
    c_size_t,
    c_uint,
    c_uint16,
    c_uint32,
    c_uint64,
    c_uint8,
    c_void_p,
    create_string_buffer,
    pointer,
    py_object,
)
from ctypes import Union as CUnion
from io import StringIO

from .ctypesutils import (
    charPtrWithSizeFromPyStr,
    charPtrFromPyStr,
    getHandleFromPtr,
    getHandleFromOutput,
    getSizedStrFromOutput,
    getStrFromC,
    getStrFromOutput,
    getPODFromOutput,
    getStructFromOutput,
    getSizedStrFromBuffer,
    getSizedBytesFromOutput,
    voidFromPyObject,
    voidFromPyFunction,
)


# ============= Library loading
def _loadLibrary() -> Any:
    """Load blpapi  shared library/dll"""
    bitness = "64" if platform.architecture()[0].startswith("64") else "32"
    prefix = "" if platform.system().lower() == "windows" else "lib"
    libsuffix = ".dll" if platform.system().lower() == "windows" else ".so"
    topysuffix = ".pyd" if platform.system().lower() == "windows" else ".so"
    libname = f"{prefix}blpapi3_{bitness}{libsuffix}"

    # it is either next to this file (we are in wheel)
    # or the usual locations (including set LD_LIBRARY_PATH)
    try:
        libpath = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), libname
        )
        lib = CDLL(libpath)
    except OSError:
        lib = CDLL(libname)

    for filename in glob.glob(
        os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "ffiutils.*" + topysuffix,
        )
    ):
        toPy = PyDLL(filename)
        break
    return lib, toPy


libblpapict, libffastcalls = _loadLibrary()
libffastcalls.blpapi_Element_toPy.restype = py_object

libffastcalls.incref.argtypes = [py_object]
incref = libffastcalls.incref

libffastcalls.setmptr.argtypes = [c_void_p]
setmptr = libffastcalls.setmptr

libffastcalls.is_known_obj.restype = c_int
libffastcalls.is_known_obj.argtypes = [c_void_p]
is_known_obj = libffastcalls.is_known_obj

from .pycbhelpers import (
    any_printer,
    anySessionEventHandlerWrapper,
    anySessionSubErrorHandlerWrapper,
    StreamWrapper,
)


class BDatetime(Structure):
    _fields_ = [
        ("parts", c_uint8),
        ("hours", c_uint8),
        ("minutes", c_uint8),
        ("seconds", c_uint8),
        ("milliSeconds", c_uint16),
        ("month", c_uint8),
        ("day", c_uint8),
        ("year", c_uint16),
        ("offset", c_int16),
    ]


class HighPrecisionDatetime(Structure):
    _fields_ = [
        ("datetime", BDatetime),
        ("picoseconds", c_uint32),
    ]


class TimePoint(Structure):
    _fields_ = [
        ("d_value", c_int64),
    ]


class CidFlags(Structure):
    _fields_ = [
        ("size", c_uint, 8),
        ("valueType", c_uint, 4),
        ("classId", c_uint, 16),
        ("internalClassId", c_uint, 4),
    ]

    def __str__(self) -> str:
        return f"[valtype: {self.valueType}, classid: {self.classId}, sz: {self.size}]"


class ManagedPtrData(CUnion):
    _fields_ = [("intValue", c_int), ("ptr", c_void_p)]


ManagedPtr_ManagerFunction_t = CFUNCTYPE(c_int, c_void_p, c_void_p, c_int)
blpapi_StreamWriter_t = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)


class ManagedPtr(Structure):
    _fields_ = [
        ("pointer", c_void_p),
        ("userData", ManagedPtrData * 4),
        ("manager", ManagedPtr_ManagerFunction_t),
    ]

    COPY = 1
    DESTROY = -1

    def __str__(self) -> str:
        return f"[ptr: {hex(self.pointer)}, ud[0]: {hex(self.userData[0].ptr)},  ud[1]: {hex(self.userData[1].ptr)},  ud[2]: {self.userData[2].ptr},  ud[3]: {self.userData[3].ptr}, mgr: {cast(self.manager, c_void_p)}]"


class CidValue(CUnion):
    _fields_ = [("intValue", c_uint64), ("ptrValue", ManagedPtr)]

    def __str__(self) -> str:
        return f"[int: {self.intValue}, ptr: {self.ptrValue}]"


class CidStruct(Structure):
    _fields_ = [("flags", CidFlags), ("rawvalue", CidValue)]

    empty_arr = (ManagedPtrData * 4)()  # empty value


def cidValueForObj(pyobj: Optional[Any]) -> CidValue:
    ptr = c_void_p(id(pyobj))
    mptr = ManagedPtr(
        pointer=ptr,
        userData=CidStruct.empty_arr,
        manager=ManagedPtr_ManagerFunction_t(),
    )
    setmptr(byref(mptr))

    # we always bump here, as we don't know how it is to be used
    # could use ptrValue.manager as well at this point
    incref(pyobj)

    # DANGER ZONE: since we decoupled the lifecycle of CidStruct
    # and CorrelationId, if this CidValue isn't used by a CorrelationId
    # then we WILL leak pyobj as nothing will decref it.
    return CidValue(ptrValue=mptr)


##################### Constants

UNKNOWN_CLASS = 0x00000
INVALIDSTATE_CLASS = 0x10000
INVALIDARG_CLASS = 0x20000
IOERROR_CLASS = 0x30000
CNVERROR_CLASS = 0x40000
BOUNDSERROR_CLASS = 0x50000
NOTFOUND_CLASS = 0x60000
FLDNOTFOUND_CLASS = 0x70000
UNSUPPORTED_CLASS = 0x80000

ERROR_UNKNOWN = UNKNOWN_CLASS | 1
ERROR_ILLEGAL_ARG = INVALIDARG_CLASS | 2
ERROR_ILLEGAL_ACCESS = UNSUPPORTED_CLASS | 3
ERROR_INVALID_SESSION = INVALIDARG_CLASS | 4
ERROR_DUPLICATE_CORRELATIONID = INVALIDARG_CLASS | 5
ERROR_INTERNAL_ERROR = UNKNOWN_CLASS | 6
ERROR_RESOLVE_FAILED = IOERROR_CLASS | 7
ERROR_CONNECT_FAILED = IOERROR_CLASS | 8
ERROR_ILLEGAL_STATE = INVALIDSTATE_CLASS | 9
ERROR_CODEC_FAILURE = UNKNOWN_CLASS | 10
ERROR_INDEX_OUT_OF_RANGE = BOUNDSERROR_CLASS | 11
ERROR_INVALID_CONVERSION = CNVERROR_CLASS | 12
ERROR_ITEM_NOT_FOUND = NOTFOUND_CLASS | 13
ERROR_IO_ERROR = IOERROR_CLASS | 14
ERROR_CORRELATION_NOT_FOUND = NOTFOUND_CLASS | 15
ERROR_SERVICE_NOT_FOUND = NOTFOUND_CLASS | 16
ERROR_LOGON_LOOKUP_FAILED = UNKNOWN_CLASS | 17
ERROR_DS_LOOKUP_FAILED = UNKNOWN_CLASS | 18
ERROR_UNSUPPORTED_OPERATION = UNSUPPORTED_CLASS | 19
ERROR_DS_PROPERTY_NOT_FOUND = NOTFOUND_CLASS | 20
ERROR_MSG_TOO_LARGE = INVALIDARG_CLASS | 21

CLIENTMODE_AUTO = 0
CLIENTMODE_DAPI = 1
CLIENTMODE_SAPI = 2
CLIENTMODE_COMPAT_33X = 16

CORRELATION_TYPE_UNSET = 0
CORRELATION_TYPE_INT = 1
CORRELATION_TYPE_POINTER = 2
CORRELATION_TYPE_AUTOGEN = 3
CORRELATION_MAX_CLASS_ID = 65535
CORRELATION_INTERNAL_CLASS_FOREIGN_OBJECT = 1

DATATYPE_BOOL = 1  # Bool
DATATYPE_CHAR = 2  # Char
DATATYPE_BYTE = 3  # Unsigned 8 bit value
DATATYPE_INT32 = 4  # 32 bit Integer
DATATYPE_INT64 = 5  # 64 bit Integer
DATATYPE_FLOAT32 = 6  # 32 bit Floating point - IEEE
DATATYPE_FLOAT64 = 7  # 64 bit Floating point - IEEE
DATATYPE_STRING = 8  # ASCIIZ string
DATATYPE_BYTEARRAY = 9  # Opaque binary data
DATATYPE_DATE = 10  # Date
DATATYPE_TIME = 11  # Timestamp
DATATYPE_DECIMAL = 12  #
DATATYPE_DATETIME = 13  # Date and time
DATATYPE_ENUMERATION = 14  # An opaque enumeration
DATATYPE_SEQUENCE = 15  # Sequence type
DATATYPE_CHOICE = 16  # Choice type
DATATYPE_CORRELATION_ID = 17  # Used for some internal messages

DATETIME_YEAR_PART = 0x1
DATETIME_MONTH_PART = 0x2
DATETIME_DAY_PART = 0x4
DATETIME_OFFSET_PART = 0x8
DATETIME_HOURS_PART = 0x10
DATETIME_MINUTES_PART = 0x20
DATETIME_SECONDS_PART = 0x40
DATETIME_MILLISECONDS_PART = 0x80
DATETIME_FRACSECONDS_PART = 0x80
DATETIME_DATE_PART = (
    DATETIME_YEAR_PART | DATETIME_MONTH_PART | DATETIME_DAY_PART
)
DATETIME_TIME_PART = (
    DATETIME_HOURS_PART | DATETIME_MINUTES_PART | DATETIME_SECONDS_PART
)
DATETIME_TIMEMILLI_PART = DATETIME_TIME_PART | DATETIME_MILLISECONDS_PART
DATETIME_TIMEFRACSECONDS_PART = DATETIME_TIME_PART | DATETIME_FRACSECONDS_PART

ELEMENTDEFINITION_UNBOUNDED = -1
ELEMENT_INDEX_END = 0xFFFFFFFF

EVENTTYPE_ADMIN = 1
EVENTTYPE_SESSION_STATUS = 2
EVENTTYPE_SUBSCRIPTION_STATUS = 3
EVENTTYPE_REQUEST_STATUS = 4
EVENTTYPE_RESPONSE = 5
EVENTTYPE_PARTIAL_RESPONSE = 6
EVENTTYPE_SUBSCRIPTION_DATA = 8
EVENTTYPE_SERVICE_STATUS = 9
EVENTTYPE_TIMEOUT = 10
EVENTTYPE_AUTHORIZATION_STATUS = 11
EVENTTYPE_RESOLUTION_STATUS = 12
EVENTTYPE_TOPIC_STATUS = 13
EVENTTYPE_TOKEN_STATUS = 14
EVENTTYPE_REQUEST = 15

MESSAGE_FRAGMENT_NONE = 0
MESSAGE_FRAGMENT_START = 1
MESSAGE_FRAGMENT_INTERMEDIATE = 2
MESSAGE_FRAGMENT_END = 3
MESSAGE_RECAPTYPE_NONE = 0
MESSAGE_RECAPTYPE_SOLICITED = 1
MESSAGE_RECAPTYPE_UNSOLICITED = 2

REGISTRATIONPARTS_DEFAULT = 0x1
REGISTRATIONPARTS_PUBLISHING = 0x2
REGISTRATIONPARTS_OPERATIONS = 0x4
REGISTRATIONPARTS_SUBSCRIBER_RESOLUTION = 0x8
REGISTRATIONPARTS_PUBLISHER_RESOLUTION = 0x10

RESOLVEMODE_DONT_REGISTER_SERVICES = 0
RESOLVEMODE_AUTO_REGISTER_SERVICES = 1

RESOLUTIONLIST_UNRESOLVED = 0
RESOLUTIONLIST_RESOLVED = 1
RESOLUTIONLIST_RESOLUTION_FAILURE_BAD_SERVICE = 2
RESOLUTIONLIST_RESOLUTION_FAILURE_SERVICE_AUTHORIZATION_FAILED = 3
RESOLUTIONLIST_RESOLUTION_FAILURE_BAD_TOPIC = 4
RESOLUTIONLIST_RESOLUTION_FAILURE_TOPIC_AUTHORIZATION_FAILED = 5

SEATTYPE_INVALID_SEAT = -1
SEATTYPE_BPS = 0
SEATTYPE_NONBPS = 1

_INT_MAX = 2147483647
SERVICEREGISTRATIONOPTIONS_PRIORITY_LOW = 0
SERVICEREGISTRATIONOPTIONS_PRIORITY_MEDIUM = _INT_MAX // 2
SERVICEREGISTRATIONOPTIONS_PRIORITY_HIGH = _INT_MAX

# schema status
STATUS_ACTIVE = 0
STATUS_DEPRECATED = 1
STATUS_INACTIVE = 2
STATUS_PENDING_DEPRECATION = 3

SUBSCRIPTIONSTATUS_UNSUBSCRIBED = 0
SUBSCRIPTIONSTATUS_SUBSCRIBING = 1
SUBSCRIPTIONSTATUS_SUBSCRIBED = 2
SUBSCRIPTIONSTATUS_CANCELLED = 3
SUBSCRIPTIONSTATUS_PENDING_CANCELLATION = 4

SUBSCRIPTIONPREPROCESS_INVALID_SUBSCRIPTION_STRING = 1
SUBSCRIPTIONPREPROCESS_CORRELATIONID_ERROR = 2

TOPICLIST_NOT_CREATED = 0
TOPICLIST_CREATED = 1
TOPICLIST_FAILURE = 2

ZFPUTIL_REMOTE_8194 = 8194
ZFPUTIL_REMOTE_8196 = 8196

blpapi_Logging_SEVERITY_OFF = 0
blpapi_Logging_SEVERITY_FATAL = 1
blpapi_Logging_SEVERITY_ERROR = 2
blpapi_Logging_SEVERITY_WARN = 3
blpapi_Logging_SEVERITY_INFO = 4
blpapi_Logging_SEVERITY_DEBUG = 5
blpapi_Logging_SEVERITY_TRACE = 6

##################### Functions

l_blpapi_AbstractSession_cancel = (
    libblpapict.blpapi_AbstractSession_cancel
)  # int
l_blpapi_AbstractSession_cancel.argtypes = [
    c_void_p,
    c_void_p,
    c_size_t,
    c_char_p,
    c_int,
]
l_blpapi_AbstractSession_createIdentity = (
    libblpapict.blpapi_AbstractSession_createIdentity
)
l_blpapi_AbstractSession_createIdentity.restype = c_void_p
l_blpapi_AbstractSession_generateAuthorizedIdentityAsync = (
    libblpapict.blpapi_AbstractSession_generateAuthorizedIdentityAsync
)  # int
l_blpapi_AbstractSession_generateToken = (
    libblpapict.blpapi_AbstractSession_generateToken
)  # int
l_blpapi_AbstractSession_generateManualToken = (
    libblpapict.blpapi_AbstractSession_generateManualToken
)  # int
l_blpapi_AbstractSession_getAuthorizedIdentity = (
    libblpapict.blpapi_AbstractSession_getAuthorizedIdentity
)  # int
l_blpapi_AbstractSession_openService = (
    libblpapict.blpapi_AbstractSession_openService
)  # int
l_blpapi_AbstractSession_openServiceAsync = (
    libblpapict.blpapi_AbstractSession_openServiceAsync
)  # int
l_blpapi_AbstractSession_getService = (
    libblpapict.blpapi_AbstractSession_getService
)  # int
l_blpapi_AbstractSession_sendAuthorizationRequest = (
    libblpapict.blpapi_AbstractSession_sendAuthorizationRequest
)  # int
l_blpapi_AbstractSession_sessionName = (
    libblpapict.blpapi_AbstractSession_sessionName
)  # int

l_blpapi_AuthApplication_create = (
    libblpapict.blpapi_AuthApplication_create
)  # int
l_blpapi_AuthApplication_destroy = libblpapict.blpapi_AuthApplication_destroy
l_blpapi_AuthApplication_destroy.restype = None

l_blpapi_AuthOptions_create_default = (
    libblpapict.blpapi_AuthOptions_create_default
)  # int
l_blpapi_AuthOptions_create_forAppMode = (
    libblpapict.blpapi_AuthOptions_create_forAppMode
)  # int
l_blpapi_AuthOptions_create_forToken = (
    libblpapict.blpapi_AuthOptions_create_forToken
)  # int
l_blpapi_AuthOptions_create_forUserAndAppMode = (
    libblpapict.blpapi_AuthOptions_create_forUserAndAppMode
)  # int
l_blpapi_AuthOptions_create_forUserMode = (
    libblpapict.blpapi_AuthOptions_create_forUserMode
)  # int
l_blpapi_AuthOptions_destroy = libblpapict.blpapi_AuthOptions_destroy
l_blpapi_AuthOptions_destroy.restype = None

l_blpapi_AuthToken_create = libblpapict.blpapi_AuthToken_create  # int
l_blpapi_AuthToken_destroy = libblpapict.blpapi_AuthToken_destroy
l_blpapi_AuthToken_destroy.restype = None

l_blpapi_AuthUser_createWithActiveDirectoryProperty = (
    libblpapict.blpapi_AuthUser_createWithActiveDirectoryProperty
)  # int
l_blpapi_AuthUser_createWithLogonName = (
    libblpapict.blpapi_AuthUser_createWithLogonName
)  # int
l_blpapi_AuthUser_createWithManualOptions = (
    libblpapict.blpapi_AuthUser_createWithManualOptions
)  # int
l_blpapi_AuthUser_destroy = libblpapict.blpapi_AuthUser_destroy
l_blpapi_AuthUser_destroy.restype = None

l_blpapi_Constant_datatype = libblpapict.blpapi_Constant_datatype  # int
l_blpapi_Constant_description = libblpapict.blpapi_Constant_description
l_blpapi_Constant_description.restype = c_char_p
l_blpapi_Constant_getValueAsChar = (
    libblpapict.blpapi_Constant_getValueAsChar
)  # int
l_blpapi_Constant_getValueAsDatetime = (
    libblpapict.blpapi_Constant_getValueAsDatetime
)  # int
l_blpapi_Constant_getValueAsFloat32 = (
    libblpapict.blpapi_Constant_getValueAsFloat32
)  # int
l_blpapi_Constant_getValueAsFloat64 = (
    libblpapict.blpapi_Constant_getValueAsFloat64
)  # int
l_blpapi_Constant_getValueAsInt32 = (
    libblpapict.blpapi_Constant_getValueAsInt32
)  # int
l_blpapi_Constant_getValueAsInt64 = (
    libblpapict.blpapi_Constant_getValueAsInt64
)  # int
l_blpapi_Constant_getValueAsString = (
    libblpapict.blpapi_Constant_getValueAsString
)  # int
l_blpapi_Constant_name = libblpapict.blpapi_Constant_name
l_blpapi_Constant_name.restype = c_void_p
l_blpapi_Constant_status = libblpapict.blpapi_Constant_status  # int

l_blpapi_ConstantList_datatype = (
    libblpapict.blpapi_ConstantList_datatype
)  # int
l_blpapi_ConstantList_description = libblpapict.blpapi_ConstantList_description
l_blpapi_ConstantList_description.restype = c_char_p
l_blpapi_ConstantList_getConstant = libblpapict.blpapi_ConstantList_getConstant
l_blpapi_ConstantList_getConstant.restype = c_void_p
l_blpapi_ConstantList_getConstantAt = (
    libblpapict.blpapi_ConstantList_getConstantAt
)
l_blpapi_ConstantList_getConstantAt.restype = c_void_p
l_blpapi_ConstantList_name = libblpapict.blpapi_ConstantList_name
l_blpapi_ConstantList_name.restype = c_void_p
l_blpapi_ConstantList_numConstants = (
    libblpapict.blpapi_ConstantList_numConstants
)  # int
l_blpapi_ConstantList_status = libblpapict.blpapi_ConstantList_status  # int

l_blpapi_DiagnosticsUtil_memoryInfo = (
    libblpapict.blpapi_DiagnosticsUtil_memoryInfo
)  # int

l_blpapi_Element_appendElement = (
    libblpapict.blpapi_Element_appendElement
)  # int
l_blpapi_Element_datatype = libblpapict.blpapi_Element_datatype  # int
l_blpapi_Element_definition = libblpapict.blpapi_Element_definition
l_blpapi_Element_definition.restype = c_void_p
l_blpapi_Element_getChoice = libblpapict.blpapi_Element_getChoice  # int
l_blpapi_Element_getElement = libblpapict.blpapi_Element_getElement  # int
l_blpapi_Element_getElementAt = libblpapict.blpapi_Element_getElementAt  # int
l_blpapi_Element_getValueAsBool = (
    libblpapict.blpapi_Element_getValueAsBool
)  # int
l_blpapi_Element_getValueAsBytes = (
    libblpapict.blpapi_Element_getValueAsBytes
)  # int
l_blpapi_Element_getValueAsChar = (
    libblpapict.blpapi_Element_getValueAsChar
)  # int
l_blpapi_Element_getValueAsElement = (
    libblpapict.blpapi_Element_getValueAsElement
)  # int
l_blpapi_Element_getValueAsFloat32 = (
    libblpapict.blpapi_Element_getValueAsFloat32
)  # int
l_blpapi_Element_getValueAsFloat64 = (
    libblpapict.blpapi_Element_getValueAsFloat64
)  # int
l_blpapi_Element_getValueAsHighPrecisionDatetime = (
    libblpapict.blpapi_Element_getValueAsHighPrecisionDatetime
)  # int
l_blpapi_Element_getValueAsInt32 = (
    libblpapict.blpapi_Element_getValueAsInt32
)  # int
l_blpapi_Element_getValueAsInt64 = (
    libblpapict.blpapi_Element_getValueAsInt64
)  # int
l_blpapi_Element_getValueAsName = (
    libblpapict.blpapi_Element_getValueAsName
)  # int
l_blpapi_Element_getValueAsString = (
    libblpapict.blpapi_Element_getValueAsString
)  # int
l_blpapi_Element_hasElementEx = libblpapict.blpapi_Element_hasElementEx  # int
l_blpapi_Element_isArray = libblpapict.blpapi_Element_isArray  # int
l_blpapi_Element_isComplexType = (
    libblpapict.blpapi_Element_isComplexType
)  # int
l_blpapi_Element_isNull = libblpapict.blpapi_Element_isNull  # int
l_blpapi_Element_isNullValue = libblpapict.blpapi_Element_isNullValue  # int
l_blpapi_Element_isReadOnly = libblpapict.blpapi_Element_isReadOnly  # int
l_blpapi_Element_name = libblpapict.blpapi_Element_name
l_blpapi_Element_name.restype = c_void_p
l_blpapi_Element_numElements = libblpapict.blpapi_Element_numElements
l_blpapi_Element_numElements.restype = c_size_t
l_blpapi_Element_numValues = libblpapict.blpapi_Element_numValues
l_blpapi_Element_numValues.restype = c_size_t
l_blpapi_Element_print = libblpapict.blpapi_Element_print  # int
l_blpapi_Element_setChoice = libblpapict.blpapi_Element_setChoice  # int
l_blpapi_Element_setElementBool = (
    libblpapict.blpapi_Element_setElementBool
)  # int
l_blpapi_Element_setElementBytes = (
    libblpapict.blpapi_Element_setElementBytes
)  # int
l_blpapi_Element_setElementFloat32 = (
    libblpapict.blpapi_Element_setElementFloat32
)  # int
l_blpapi_Element_setElementFloat64 = (
    libblpapict.blpapi_Element_setElementFloat64
)  # int
l_blpapi_Element_setElementFromName = (
    libblpapict.blpapi_Element_setElementFromName
)  # int
l_blpapi_Element_setElementHighPrecisionDatetime = (
    libblpapict.blpapi_Element_setElementHighPrecisionDatetime
)  # int
l_blpapi_Element_setElementInt32 = (
    libblpapict.blpapi_Element_setElementInt32
)  # int
l_blpapi_Element_setElementInt64 = (
    libblpapict.blpapi_Element_setElementInt64
)  # int
l_blpapi_Element_setElementString = (
    libblpapict.blpapi_Element_setElementString
)  # int
l_blpapi_Element_setValueBool = libblpapict.blpapi_Element_setValueBool  # int
l_blpapi_Element_setValueBytes = (
    libblpapict.blpapi_Element_setValueBytes
)  # int
l_blpapi_Element_setValueFloat32 = (
    libblpapict.blpapi_Element_setValueFloat32
)  # int
l_blpapi_Element_setValueFloat64 = (
    libblpapict.blpapi_Element_setValueFloat64
)  # int
l_blpapi_Element_setValueFromName = (
    libblpapict.blpapi_Element_setValueFromName
)  # int
l_blpapi_Element_setValueHighPrecisionDatetime = (
    libblpapict.blpapi_Element_setValueHighPrecisionDatetime
)  # int
l_blpapi_Element_setValueInt32 = (
    libblpapict.blpapi_Element_setValueInt32
)  # int
l_blpapi_Element_setValueInt64 = (
    libblpapict.blpapi_Element_setValueInt64
)  # int
l_blpapi_Element_setValueString = (
    libblpapict.blpapi_Element_setValueString
)  # int
l_blpapi_Element_toJson = libblpapict.blpapi_Element_toJson  # int
l_blpapi_Element_toJson.argtypes = [c_void_p, blpapi_StreamWriter_t, c_void_p]
l_blpapi_Element_toJson.restype = c_int
l_blpapi_Element_fromJson = libblpapict.blpapi_Element_fromJson  # int
l_blpapi_Element_fromJson.argtypes = [c_void_p, c_char_p]
l_blpapi_Element_fromJson.restype = c_int

l_blpapi_Event_eventType = libblpapict.blpapi_Event_eventType  # int
l_blpapi_Event_release = libblpapict.blpapi_Event_release  # int

l_blpapi_EventDispatcher_create = libblpapict.blpapi_EventDispatcher_create
l_blpapi_EventDispatcher_create.restype = c_void_p
l_blpapi_EventDispatcher_destroy = libblpapict.blpapi_EventDispatcher_destroy
l_blpapi_EventDispatcher_destroy.restype = None
l_blpapi_EventDispatcher_start = (
    libblpapict.blpapi_EventDispatcher_start
)  # int
l_blpapi_EventDispatcher_stop = libblpapict.blpapi_EventDispatcher_stop  # int

l_blpapi_EventFormatter_appendElement = (
    libblpapict.blpapi_EventFormatter_appendElement
)  # int
l_blpapi_EventFormatter_appendFragmentedRecapMessage = (
    libblpapict.blpapi_EventFormatter_appendFragmentedRecapMessage
)  # int
l_blpapi_EventFormatter_appendFragmentedRecapMessage.argtypes = [
    c_void_p,
    c_char_p,
    c_void_p,
    c_void_p,
    c_void_p,
    c_int,
]
l_blpapi_EventFormatter_appendFragmentedRecapMessageSeq = (
    libblpapict.blpapi_EventFormatter_appendFragmentedRecapMessageSeq
)  # int
l_blpapi_EventFormatter_appendFragmentedRecapMessageSeq.argtypes = [
    c_void_p,
    c_char_p,
    c_void_p,
    c_void_p,
    c_int,
    c_uint,
]
l_blpapi_EventFormatter_appendMessage = (
    libblpapict.blpapi_EventFormatter_appendMessage
)  # int
l_blpapi_EventFormatter_appendMessageSeq = (
    libblpapict.blpapi_EventFormatter_appendMessageSeq
)  # int
l_blpapi_EventFormatter_appendRecapMessage = (
    libblpapict.blpapi_EventFormatter_appendRecapMessage
)  # int
l_blpapi_EventFormatter_appendRecapMessageSeq = (
    libblpapict.blpapi_EventFormatter_appendRecapMessageSeq
)  # int
l_blpapi_EventFormatter_appendResponse = (
    libblpapict.blpapi_EventFormatter_appendResponse
)  # int
l_blpapi_EventFormatter_appendValueBool = (
    libblpapict.blpapi_EventFormatter_appendValueBool
)  # int
l_blpapi_EventFormatter_appendValueChar = (
    libblpapict.blpapi_EventFormatter_appendValueChar
)  # int
l_blpapi_EventFormatter_appendValueDatetime = (
    libblpapict.blpapi_EventFormatter_appendValueDatetime
)  # int
l_blpapi_EventFormatter_appendValueFloat32 = (
    libblpapict.blpapi_EventFormatter_appendValueFloat32
)  # int
l_blpapi_EventFormatter_appendValueFloat64 = (
    libblpapict.blpapi_EventFormatter_appendValueFloat64
)  # int
l_blpapi_EventFormatter_appendValueFromName = (
    libblpapict.blpapi_EventFormatter_appendValueFromName
)  # int
l_blpapi_EventFormatter_appendValueInt32 = (
    libblpapict.blpapi_EventFormatter_appendValueInt32
)  # int
l_blpapi_EventFormatter_appendValueInt64 = (
    libblpapict.blpapi_EventFormatter_appendValueInt64
)  # int
l_blpapi_EventFormatter_appendValueString = (
    libblpapict.blpapi_EventFormatter_appendValueString
)  # int
l_blpapi_EventFormatter_create = libblpapict.blpapi_EventFormatter_create
l_blpapi_EventFormatter_create.restype = c_void_p
l_blpapi_EventFormatter_destroy = libblpapict.blpapi_EventFormatter_destroy
l_blpapi_EventFormatter_destroy.restype = None
l_blpapi_EventFormatter_popElement = (
    libblpapict.blpapi_EventFormatter_popElement
)  # int
l_blpapi_EventFormatter_pushElement = (
    libblpapict.blpapi_EventFormatter_pushElement
)  # int
l_blpapi_EventFormatter_setValueBool = (
    libblpapict.blpapi_EventFormatter_setValueBool
)  # int
l_blpapi_EventFormatter_setValueBytes = (
    libblpapict.blpapi_EventFormatter_setValueBytes
)  # int
l_blpapi_EventFormatter_setValueChar = (
    libblpapict.blpapi_EventFormatter_setValueChar
)  # int
l_blpapi_EventFormatter_setValueDatetime = (
    libblpapict.blpapi_EventFormatter_setValueDatetime
)  # int
l_blpapi_EventFormatter_setValueFloat32 = (
    libblpapict.blpapi_EventFormatter_setValueFloat32
)  # int
l_blpapi_EventFormatter_setValueFloat64 = (
    libblpapict.blpapi_EventFormatter_setValueFloat64
)  # int
l_blpapi_EventFormatter_setValueFromName = (
    libblpapict.blpapi_EventFormatter_setValueFromName
)  # int
l_blpapi_EventFormatter_setValueHighPrecisionDatetime = (
    libblpapict.blpapi_EventFormatter_setValueHighPrecisionDatetime
)  # int
l_blpapi_EventFormatter_appendValueHighPrecisionDatetime = (
    libblpapict.blpapi_EventFormatter_appendValueHighPrecisionDatetime
)  # int
l_blpapi_EventFormatter_setValueInt32 = (
    libblpapict.blpapi_EventFormatter_setValueInt32
)  # int
l_blpapi_EventFormatter_setValueInt64 = (
    libblpapict.blpapi_EventFormatter_setValueInt64
)  # int
l_blpapi_EventFormatter_setValueNull = (
    libblpapict.blpapi_EventFormatter_setValueNull
)  # int
l_blpapi_EventFormatter_setValueString = (
    libblpapict.blpapi_EventFormatter_setValueString
)  # int
l_blpapi_EventFormatter_getElement = (
    libblpapict.blpapi_EventFormatter_getElement
)  # int

l_blpapi_EventQueue_create = libblpapict.blpapi_EventQueue_create
l_blpapi_EventQueue_create.restype = c_void_p
l_blpapi_EventQueue_destroy = libblpapict.blpapi_EventQueue_destroy  # int
l_blpapi_EventQueue_nextEvent = libblpapict.blpapi_EventQueue_nextEvent
l_blpapi_EventQueue_nextEvent.restype = c_void_p
l_blpapi_EventQueue_purge = libblpapict.blpapi_EventQueue_purge  # int
l_blpapi_EventQueue_tryNextEvent = (
    libblpapict.blpapi_EventQueue_tryNextEvent
)  # int

l_blpapi_HighPrecisionDatetime_fromTimePoint = (
    libblpapict.blpapi_HighPrecisionDatetime_fromTimePoint
)  # int

l_blpapi_HighResolutionClock_now = (
    libblpapict.blpapi_HighResolutionClock_now
)  # int

l_blpapi_Identity_getSeatType = libblpapict.blpapi_Identity_getSeatType  # int
l_blpapi_Identity_hasEntitlements = (
    libblpapict.blpapi_Identity_hasEntitlements
)  # int
l_blpapi_Identity_isAuthorized = (
    libblpapict.blpapi_Identity_isAuthorized
)  # int
l_blpapi_Identity_release = libblpapict.blpapi_Identity_release
l_blpapi_Identity_release.restype = None

l_blpapi_Logging_logTestMessage = libblpapict.blpapi_Logging_logTestMessage
l_blpapi_Logging_logTestMessage.restype = None
l_blpapi_Logging_registerCallback = (
    libblpapict.blpapi_Logging_registerCallback
)  # int

l_blpapi_MessageFormatter_FormatMessageJson = (
    libblpapict.blpapi_MessageFormatter_FormatMessageJson
)  # int
l_blpapi_MessageFormatter_FormatMessageXml = (
    libblpapict.blpapi_MessageFormatter_FormatMessageXml
)  # int
l_blpapi_MessageFormatter_appendElement = (
    libblpapict.blpapi_MessageFormatter_appendElement
)  # int
l_blpapi_MessageFormatter_appendValueBool = (
    libblpapict.blpapi_MessageFormatter_appendValueBool
)  # int
l_blpapi_MessageFormatter_appendValueChar = (
    libblpapict.blpapi_MessageFormatter_appendValueChar
)  # int
l_blpapi_MessageFormatter_appendValueDatetime = (
    libblpapict.blpapi_MessageFormatter_appendValueDatetime
)  # int
l_blpapi_MessageFormatter_appendValueFloat32 = (
    libblpapict.blpapi_MessageFormatter_appendValueFloat32
)  # int
l_blpapi_MessageFormatter_appendValueFloat64 = (
    libblpapict.blpapi_MessageFormatter_appendValueFloat64
)  # int
l_blpapi_MessageFormatter_appendValueFromName = (
    libblpapict.blpapi_MessageFormatter_appendValueFromName
)  # int
l_blpapi_MessageFormatter_appendValueHighPrecisionDatetime = (
    libblpapict.blpapi_MessageFormatter_appendValueHighPrecisionDatetime
)  # int
l_blpapi_MessageFormatter_appendValueInt32 = (
    libblpapict.blpapi_MessageFormatter_appendValueInt32
)  # int
l_blpapi_MessageFormatter_appendValueInt64 = (
    libblpapict.blpapi_MessageFormatter_appendValueInt64
)  # int
l_blpapi_MessageFormatter_appendValueString = (
    libblpapict.blpapi_MessageFormatter_appendValueString
)  # int
l_blpapi_MessageFormatter_destroy = (
    libblpapict.blpapi_MessageFormatter_destroy
)  # int
l_blpapi_MessageFormatter_popElement = (
    libblpapict.blpapi_MessageFormatter_popElement
)  # int
l_blpapi_MessageFormatter_pushElement = (
    libblpapict.blpapi_MessageFormatter_pushElement
)  # int
l_blpapi_MessageFormatter_setValueBool = (
    libblpapict.blpapi_MessageFormatter_setValueBool
)  # int
l_blpapi_MessageFormatter_setValueBytes = (
    libblpapict.blpapi_MessageFormatter_setValueBytes
)  # int
l_blpapi_MessageFormatter_setValueChar = (
    libblpapict.blpapi_MessageFormatter_setValueBool
)  # int
l_blpapi_MessageFormatter_setValueDatetime = (
    libblpapict.blpapi_MessageFormatter_setValueDatetime
)  # int
l_blpapi_MessageFormatter_setValueFloat32 = (
    libblpapict.blpapi_MessageFormatter_setValueFloat32
)  # int
l_blpapi_MessageFormatter_setValueFloat64 = (
    libblpapict.blpapi_MessageFormatter_setValueFloat64
)  # int
l_blpapi_MessageFormatter_setValueFromName = (
    libblpapict.blpapi_MessageFormatter_setValueFromName
)  # int
l_blpapi_MessageFormatter_setValueHighPrecisionDatetime = (
    libblpapict.blpapi_MessageFormatter_setValueHighPrecisionDatetime
)  # int
l_blpapi_MessageFormatter_setValueInt32 = (
    libblpapict.blpapi_MessageFormatter_setValueInt32
)  # int
l_blpapi_MessageFormatter_setValueInt64 = (
    libblpapict.blpapi_MessageFormatter_setValueInt64
)  # int
l_blpapi_MessageFormatter_setValueNull = (
    libblpapict.blpapi_MessageFormatter_setValueNull
)  # int
l_blpapi_MessageFormatter_setValueString = (
    libblpapict.blpapi_MessageFormatter_setValueString
)  # int
l_blpapi_MessageFormatter_getElement = (
    libblpapict.blpapi_MessageFormatter_getElement
)  # int

l_blpapi_MessageIterator_create = libblpapict.blpapi_MessageIterator_create
l_blpapi_MessageIterator_create.restype = c_void_p
l_blpapi_MessageIterator_destroy = libblpapict.blpapi_MessageIterator_destroy
l_blpapi_MessageIterator_destroy.restype = None
l_blpapi_MessageIterator_next = libblpapict.blpapi_MessageIterator_next  # int

l_blpapi_Message_addRef = libblpapict.blpapi_Message_addRef  # int
l_blpapi_Message_correlationId = libblpapict.blpapi_Message_correlationId
l_blpapi_Message_correlationId.restype = CidStruct
l_blpapi_Message_elements = libblpapict.blpapi_Message_elements
l_blpapi_Message_elements.restype = c_void_p
l_blpapi_Message_fragmentType = libblpapict.blpapi_Message_fragmentType  # int
l_blpapi_Message_getRequestId = libblpapict.blpapi_Message_getRequestId  # int
l_blpapi_Message_messageType = libblpapict.blpapi_Message_messageType
l_blpapi_Message_messageType.restype = c_void_p
l_blpapi_Message_numCorrelationIds = (
    libblpapict.blpapi_Message_numCorrelationIds
)  # int
l_blpapi_Message_print = libblpapict.blpapi_Message_print  # int
l_blpapi_Message_recapType = libblpapict.blpapi_Message_recapType  # int
l_blpapi_Message_release = libblpapict.blpapi_Message_release  # int
l_blpapi_Message_service = libblpapict.blpapi_Message_service
l_blpapi_Message_service.restype = c_void_p
l_blpapi_Message_timeReceived = libblpapict.blpapi_Message_timeReceived  # int

l_blpapi_MessageProperties_create = (
    libblpapict.blpapi_MessageProperties_create
)  # int
l_blpapi_MessageProperties_destroy = (
    libblpapict.blpapi_MessageProperties_destroy
)
l_blpapi_MessageProperties_destroy.restype = None
l_blpapi_MessageProperties_setCorrelationIds = (
    libblpapict.blpapi_MessageProperties_setCorrelationIds
)  # int
l_blpapi_MessageProperties_setRecapType = (
    libblpapict.blpapi_MessageProperties_setRecapType
)  # int
l_blpapi_MessageProperties_setRequestId = (
    libblpapict.blpapi_MessageProperties_setRequestId
)  # int
l_blpapi_MessageProperties_setService = (
    libblpapict.blpapi_MessageProperties_setService
)  # int
l_blpapi_MessageProperties_setTimeReceived = (
    libblpapict.blpapi_MessageProperties_setTimeReceived
)  # int

l_blpapi_Name_create = libblpapict.blpapi_Name_create
l_blpapi_Name_create.restype = c_void_p
l_blpapi_Name_destroy = libblpapict.blpapi_Name_destroy
l_blpapi_Name_destroy.restype = None
l_blpapi_Name_equalsStr = libblpapict.blpapi_Name_equalsStr  # int
l_blpapi_Name_findName = libblpapict.blpapi_Name_findName
l_blpapi_Name_findName.restype = c_void_p
l_blpapi_Name_length = libblpapict.blpapi_Name_length
l_blpapi_Name_length.restype = c_size_t
l_blpapi_Name_string = libblpapict.blpapi_Name_string
l_blpapi_Name_string.restype = c_char_p

l_blpapi_Operation_description = libblpapict.blpapi_Operation_description
l_blpapi_Operation_description.restype = c_char_p
l_blpapi_Operation_name = libblpapict.blpapi_Operation_name
l_blpapi_Operation_name.restype = c_char_p
l_blpapi_Operation_numResponseDefinitions = (
    libblpapict.blpapi_Operation_numResponseDefinitions
)  # int
l_blpapi_Operation_requestDefinition = (
    libblpapict.blpapi_Operation_requestDefinition
)  # int
l_blpapi_Operation_responseDefinition = (
    libblpapict.blpapi_Operation_responseDefinition
)  # int

l_blpapi_ProviderSession_activateSubServiceCodeRange = (
    libblpapict.blpapi_ProviderSession_activateSubServiceCodeRange
)  # int
l_blpapi_ProviderSession_create = libblpapict.blpapi_ProviderSession_create
l_blpapi_ProviderSession_create.restype = c_void_p
l_blpapi_ProviderSession_createTopics = (
    libblpapict.blpapi_ProviderSession_createTopics
)  # int
l_blpapi_ProviderSession_createTopicsAsync = (
    libblpapict.blpapi_ProviderSession_createTopicsAsync
)  # int
l_blpapi_ProviderSession_createServiceStatusTopic = (
    libblpapict.blpapi_ProviderSession_createServiceStatusTopic
)  # int
l_blpapi_ProviderSession_deactivateSubServiceCodeRange = (
    libblpapict.blpapi_ProviderSession_deactivateSubServiceCodeRange
)  # int
l_blpapi_ProviderSession_deleteTopics = (
    libblpapict.blpapi_ProviderSession_deleteTopics
)  # int
l_blpapi_ProviderSession_deregisterService = (
    libblpapict.blpapi_ProviderSession_deregisterService
)  # int
l_blpapi_ProviderSession_destroy = libblpapict.blpapi_ProviderSession_destroy
l_blpapi_ProviderSession_destroy.restype = None
l_blpapi_ProviderSession_flushPublishedEvents = (
    libblpapict.blpapi_ProviderSession_flushPublishedEvents
)  # int
l_blpapi_ProviderSession_getAbstractSession = (
    libblpapict.blpapi_ProviderSession_getAbstractSession
)
l_blpapi_ProviderSession_getAbstractSession.restype = c_void_p
l_blpapi_ProviderSession_getTopic = (
    libblpapict.blpapi_ProviderSession_getTopic
)  # int
l_blpapi_ProviderSession_nextEvent = (
    libblpapict.blpapi_ProviderSession_nextEvent
)  # int
l_blpapi_ProviderSession_publish = (
    libblpapict.blpapi_ProviderSession_publish
)  # int
l_blpapi_ProviderSession_registerService = (
    libblpapict.blpapi_ProviderSession_registerService
)  # int
l_blpapi_ProviderSession_registerServiceAsync = (
    libblpapict.blpapi_ProviderSession_registerServiceAsync
)  # int
l_blpapi_ProviderSession_resolve = (
    libblpapict.blpapi_ProviderSession_resolve
)  # int
l_blpapi_ProviderSession_resolveAsync = (
    libblpapict.blpapi_ProviderSession_resolveAsync
)  # int
l_blpapi_ProviderSession_sendResponse = (
    libblpapict.blpapi_ProviderSession_sendResponse
)  # int
l_blpapi_ProviderSession_start = (
    libblpapict.blpapi_ProviderSession_start
)  # int
l_blpapi_ProviderSession_startAsync = (
    libblpapict.blpapi_ProviderSession_startAsync
)  # int
l_blpapi_ProviderSession_stop = libblpapict.blpapi_ProviderSession_stop  # int
l_blpapi_ProviderSession_stopAsync = (
    libblpapict.blpapi_ProviderSession_stopAsync
)  # int
l_blpapi_ProviderSession_terminateSubscriptionsOnTopics = (
    libblpapict.blpapi_ProviderSession_terminateSubscriptionsOnTopics
)  # int
l_blpapi_ProviderSession_tryNextEvent = (
    libblpapict.blpapi_ProviderSession_tryNextEvent
)  # int

l_blpapi_RequestTemplate_release = (
    libblpapict.blpapi_RequestTemplate_release
)  # int

l_blpapi_Request_destroy = libblpapict.blpapi_Request_destroy
l_blpapi_Request_destroy.restype = None
l_blpapi_Request_elements = libblpapict.blpapi_Request_elements
l_blpapi_Request_elements.restype = c_void_p
l_blpapi_Request_getRequestId = libblpapict.blpapi_Request_getRequestId  # int

l_blpapi_ResolutionList_extractAttributeFromResolutionSuccess = (
    libblpapict.blpapi_ResolutionList_extractAttributeFromResolutionSuccess
)
l_blpapi_ResolutionList_extractAttributeFromResolutionSuccess.restype = (
    c_void_p
)

l_blpapi_ResolutionList_create = libblpapict.blpapi_ResolutionList_create
l_blpapi_ResolutionList_create.restype = c_void_p

l_blpapi_ResolutionList_destroy = libblpapict.blpapi_ResolutionList_destroy
l_blpapi_ResolutionList_destroy.restype = None
l_blpapi_ResolutionList_add = libblpapict.blpapi_ResolutionList_add  # int
l_blpapi_ResolutionList_addFromMessage = (
    libblpapict.blpapi_ResolutionList_addFromMessage
)  # int
l_blpapi_ResolutionList_addAttribute = (
    libblpapict.blpapi_ResolutionList_addAttribute
)  # int
l_blpapi_ResolutionList_correlationIdAt = (
    libblpapict.blpapi_ResolutionList_correlationIdAt
)  # int
l_blpapi_ResolutionList_topicString = (
    libblpapict.blpapi_ResolutionList_topicString
)  # int
l_blpapi_ResolutionList_topicStringAt = (
    libblpapict.blpapi_ResolutionList_topicStringAt
)  # int
l_blpapi_ResolutionList_status = (
    libblpapict.blpapi_ResolutionList_status
)  # int
l_blpapi_ResolutionList_statusAt = (
    libblpapict.blpapi_ResolutionList_statusAt
)  # int
l_blpapi_ResolutionList_attribute = (
    libblpapict.blpapi_ResolutionList_attribute
)  # int
l_blpapi_ResolutionList_attributeAt = (
    libblpapict.blpapi_ResolutionList_attributeAt
)  # int
l_blpapi_ResolutionList_message = (
    libblpapict.blpapi_ResolutionList_message
)  # int
l_blpapi_ResolutionList_messageAt = (
    libblpapict.blpapi_ResolutionList_messageAt
)  # int
l_blpapi_ResolutionList_size = libblpapict.blpapi_ResolutionList_size  # int

l_blpapi_SchemaElementDefinition_description = (
    libblpapict.blpapi_SchemaElementDefinition_description
)
l_blpapi_SchemaElementDefinition_description.restype = c_char_p
l_blpapi_SchemaElementDefinition_getAlternateName = (
    libblpapict.blpapi_SchemaElementDefinition_getAlternateName
)
l_blpapi_SchemaElementDefinition_getAlternateName.restype = c_void_p
l_blpapi_SchemaElementDefinition_name = (
    libblpapict.blpapi_SchemaElementDefinition_name
)
l_blpapi_SchemaElementDefinition_name.restype = c_void_p
l_blpapi_SchemaElementDefinition_print = (
    libblpapict.blpapi_SchemaElementDefinition_print
)  # int
l_blpapi_SchemaElementDefinition_status = (
    libblpapict.blpapi_SchemaElementDefinition_status
)  # int
l_blpapi_SchemaElementDefinition_type = (
    libblpapict.blpapi_SchemaElementDefinition_type
)
l_blpapi_SchemaElementDefinition_type.restype = c_void_p

l_blpapi_SchemaTypeDefinition_datatype = (
    libblpapict.blpapi_SchemaTypeDefinition_datatype
)  # int
l_blpapi_SchemaTypeDefinition_description = (
    libblpapict.blpapi_SchemaTypeDefinition_description
)
l_blpapi_SchemaTypeDefinition_description.restype = c_char_p
l_blpapi_SchemaTypeDefinition_isComplexType = (
    libblpapict.blpapi_SchemaTypeDefinition_isComplexType
)
l_blpapi_SchemaTypeDefinition_enumeration = (
    libblpapict.blpapi_SchemaTypeDefinition_enumeration
)
l_blpapi_SchemaTypeDefinition_enumeration.restype = c_void_p
l_blpapi_SchemaTypeDefinition_getElementDefinition = (
    libblpapict.blpapi_SchemaTypeDefinition_getElementDefinition
)
l_blpapi_SchemaTypeDefinition_getElementDefinition.restype = c_void_p
l_blpapi_SchemaTypeDefinition_getElementDefinitionAt = (
    libblpapict.blpapi_SchemaTypeDefinition_getElementDefinitionAt
)
l_blpapi_SchemaTypeDefinition_getElementDefinitionAt.restype = c_void_p
l_blpapi_SchemaTypeDefinition_isComplexType = (
    libblpapict.blpapi_SchemaTypeDefinition_isComplexType
)  # int
l_blpapi_SchemaTypeDefinition_isEnumerationType = (
    libblpapict.blpapi_SchemaTypeDefinition_isEnumerationType
)  # int
l_blpapi_SchemaTypeDefinition_isSimpleType = (
    libblpapict.blpapi_SchemaTypeDefinition_isSimpleType
)  # int
l_blpapi_SchemaElementDefinition_maxValues = (
    libblpapict.blpapi_SchemaElementDefinition_maxValues
)
l_blpapi_SchemaElementDefinition_maxValues.restype = c_size_t
l_blpapi_SchemaElementDefinition_minValues = (
    libblpapict.blpapi_SchemaElementDefinition_minValues
)
l_blpapi_SchemaElementDefinition_minValues.restype = c_size_t
l_blpapi_SchemaElementDefinition_numAlternateNames = (
    libblpapict.blpapi_SchemaElementDefinition_numAlternateNames
)
l_blpapi_SchemaElementDefinition_numAlternateNames.restype = c_size_t
l_blpapi_SchemaTypeDefinition_name = (
    libblpapict.blpapi_SchemaTypeDefinition_name
)
l_blpapi_SchemaTypeDefinition_name.restype = c_void_p
l_blpapi_SchemaTypeDefinition_numElementDefinitions = (
    libblpapict.blpapi_SchemaTypeDefinition_numElementDefinitions
)
l_blpapi_SchemaTypeDefinition_numElementDefinitions.restype = c_size_t
l_blpapi_SchemaTypeDefinition_print = (
    libblpapict.blpapi_SchemaTypeDefinition_print
)  # int
l_blpapi_SchemaTypeDefinition_status = (
    libblpapict.blpapi_SchemaTypeDefinition_status
)  # int

l_blpapi_Service_addRef = libblpapict.blpapi_Service_addRef  # int
l_blpapi_Service_authorizationServiceName = (
    libblpapict.blpapi_Service_authorizationServiceName
)
l_blpapi_Service_authorizationServiceName.restype = c_char_p
l_blpapi_Service_createAdminEvent = (
    libblpapict.blpapi_Service_createAdminEvent
)  # int
l_blpapi_Service_createAuthorizationRequest = (
    libblpapict.blpapi_Service_createAuthorizationRequest
)  # int
l_blpapi_Service_createPublishEvent = (
    libblpapict.blpapi_Service_createPublishEvent
)  # int
l_blpapi_Service_createRequest = (
    libblpapict.blpapi_Service_createRequest
)  # int
l_blpapi_Service_createResponseEvent = (
    libblpapict.blpapi_Service_createResponseEvent
)  # int
l_blpapi_Service_description = libblpapict.blpapi_Service_description
l_blpapi_Service_description.restype = c_char_p
l_blpapi_Service_getEventDefinition = (
    libblpapict.blpapi_Service_getEventDefinition
)  # int
l_blpapi_Service_getEventDefinitionAt = (
    libblpapict.blpapi_Service_getEventDefinitionAt
)  # int
l_blpapi_Service_getOperation = libblpapict.blpapi_Service_getOperation  # int
l_blpapi_Service_getOperationAt = (
    libblpapict.blpapi_Service_getOperationAt
)  # int
l_blpapi_Service_name = libblpapict.blpapi_Service_name
l_blpapi_Service_name.restype = c_char_p
l_blpapi_Service_numEventDefinitions = (
    libblpapict.blpapi_Service_numEventDefinitions
)  # int
l_blpapi_Service_numOperations = (
    libblpapict.blpapi_Service_numOperations
)  # int
l_blpapi_Service_print = libblpapict.blpapi_Service_print  # int
l_blpapi_Service_release = libblpapict.blpapi_Service_release
l_blpapi_Service_release.restype = None

l_blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange = (
    libblpapict.blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange
)  # int
l_blpapi_ServiceRegistrationOptions_create = (
    libblpapict.blpapi_ServiceRegistrationOptions_create
)
l_blpapi_ServiceRegistrationOptions_create.restype = c_void_p
l_blpapi_ServiceRegistrationOptions_destroy = (
    libblpapict.blpapi_ServiceRegistrationOptions_destroy
)
l_blpapi_ServiceRegistrationOptions_destroy.restype = None
l_blpapi_ServiceRegistrationOptions_getGroupId = (
    libblpapict.blpapi_ServiceRegistrationOptions_getGroupId
)  # int
l_blpapi_ServiceRegistrationOptions_getGroupId.argtypes = [
    c_void_p,
    c_char_p,
    POINTER(c_int),
]
l_blpapi_ServiceRegistrationOptions_getServicePriority = (
    libblpapict.blpapi_ServiceRegistrationOptions_getServicePriority
)  # int
l_blpapi_ServiceRegistrationOptions_setGroupId = (
    libblpapict.blpapi_ServiceRegistrationOptions_setGroupId
)
l_blpapi_ServiceRegistrationOptions_setGroupId.restype = None
l_blpapi_ServiceRegistrationOptions_getPartsToRegister = (
    libblpapict.blpapi_ServiceRegistrationOptions_getPartsToRegister
)  # int
l_blpapi_ServiceRegistrationOptions_setPartsToRegister = (
    libblpapict.blpapi_ServiceRegistrationOptions_setPartsToRegister
)
l_blpapi_ServiceRegistrationOptions_setPartsToRegister.restype = None
l_blpapi_ServiceRegistrationOptions_setServicePriority = (
    libblpapict.blpapi_ServiceRegistrationOptions_setServicePriority
)  # int
l_blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges = (
    libblpapict.blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges
)
l_blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges.restype = (
    None
)

l_blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg = (
    libblpapict.blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg
)  # int
l_blpapi_SessionOptions_applicationIdentityKey = (
    libblpapict.blpapi_SessionOptions_applicationIdentityKey
)  # int
l_blpapi_SessionOptions_authenticationOptions = (
    libblpapict.blpapi_SessionOptions_authenticationOptions
)
l_blpapi_SessionOptions_authenticationOptions.restype = c_char_p
l_blpapi_SessionOptions_autoRestartOnDisconnection = (
    libblpapict.blpapi_SessionOptions_autoRestartOnDisconnection
)  # int
l_blpapi_SessionOptions_bandwidthSaveModeDisabled = (
    libblpapict.blpapi_SessionOptions_bandwidthSaveModeDisabled
)  # int
l_blpapi_SessionOptions_clientMode = (
    libblpapict.blpapi_SessionOptions_clientMode
)  # int
l_blpapi_SessionOptions_connectTimeout = (
    libblpapict.blpapi_SessionOptions_connectTimeout
)
l_blpapi_SessionOptions_connectTimeout.restype = c_uint32
l_blpapi_SessionOptions_create = libblpapict.blpapi_SessionOptions_create
l_blpapi_SessionOptions_create.restype = c_void_p
l_blpapi_SessionOptions_defaultKeepAliveInactivityTime = (
    libblpapict.blpapi_SessionOptions_defaultKeepAliveInactivityTime
)  # int
l_blpapi_SessionOptions_defaultKeepAliveResponseTimeout = (
    libblpapict.blpapi_SessionOptions_defaultKeepAliveResponseTimeout
)  # int
l_blpapi_SessionOptions_defaultServices = (
    libblpapict.blpapi_SessionOptions_defaultServices
)
l_blpapi_SessionOptions_defaultServices.restype = c_char_p
l_blpapi_SessionOptions_defaultSubscriptionService = (
    libblpapict.blpapi_SessionOptions_defaultSubscriptionService
)
l_blpapi_SessionOptions_defaultSubscriptionService.restype = c_char_p
l_blpapi_SessionOptions_defaultTopicPrefix = (
    libblpapict.blpapi_SessionOptions_defaultTopicPrefix
)
l_blpapi_SessionOptions_defaultTopicPrefix.restype = c_char_p
l_blpapi_SessionOptions_destroy = libblpapict.blpapi_SessionOptions_destroy
l_blpapi_SessionOptions_destroy.restype = None
l_blpapi_SessionOptions_flushPublishedEventsTimeout = (
    libblpapict.blpapi_SessionOptions_flushPublishedEventsTimeout
)  # int
l_blpapi_SessionOptions_getServerAddressWithProxy = (
    libblpapict.blpapi_SessionOptions_getServerAddressWithProxy
)  # int
l_blpapi_SessionOptions_keepAliveEnabled = (
    libblpapict.blpapi_SessionOptions_keepAliveEnabled
)  # int
l_blpapi_SessionOptions_maxEventQueueSize = (
    libblpapict.blpapi_SessionOptions_maxEventQueueSize
)
l_blpapi_SessionOptions_maxEventQueueSize.restype = c_size_t
l_blpapi_SessionOptions_maxPendingRequests = (
    libblpapict.blpapi_SessionOptions_maxPendingRequests
)  # int
l_blpapi_SessionOptions_numServerAddresses = (
    libblpapict.blpapi_SessionOptions_numServerAddresses
)  # int
l_blpapi_SessionOptions_numStartAttempts = (
    libblpapict.blpapi_SessionOptions_numStartAttempts
)  # int
l_blpapi_SessionOptions_print = libblpapict.blpapi_SessionOptions_print  # int
l_blpapi_SessionOptions_print.argtypes = [
    c_void_p,
    c_void_p,
    c_void_p,  # as py_object it segfaults, we cast in any_printer instead
    c_int,
    c_int,
]
l_blpapi_SessionOptions_recordSubscriptionDataReceiveTimes = (
    libblpapict.blpapi_SessionOptions_recordSubscriptionDataReceiveTimes
)  # int
l_blpapi_SessionOptions_removeServerAddress = (
    libblpapict.blpapi_SessionOptions_removeServerAddress
)  # int
l_blpapi_SessionOptions_serverHost = (
    libblpapict.blpapi_SessionOptions_serverHost
)
l_blpapi_SessionOptions_serverHost.restype = c_char_p
l_blpapi_SessionOptions_serverPort = (
    libblpapict.blpapi_SessionOptions_serverPort
)
l_blpapi_SessionOptions_serverPort.restype = c_uint32
l_blpapi_SessionOptions_serviceCheckTimeout = (
    libblpapict.blpapi_SessionOptions_serviceCheckTimeout
)  # int
l_blpapi_SessionOptions_serviceDownloadTimeout = (
    libblpapict.blpapi_SessionOptions_serviceDownloadTimeout
)  # int
l_blpapi_SessionOptions_sessionName = (
    libblpapict.blpapi_SessionOptions_sessionName
)  # int
l_blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg = (
    libblpapict.blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg
)
l_blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg.restype = None
l_blpapi_SessionOptions_setApplicationIdentityKey = (
    libblpapict.blpapi_SessionOptions_setApplicationIdentityKey
)  # int
l_blpapi_SessionOptions_setAuthenticationOptions = (
    libblpapict.blpapi_SessionOptions_setAuthenticationOptions
)
l_blpapi_SessionOptions_setAuthenticationOptions.restype = None
l_blpapi_SessionOptions_setAutoRestartOnDisconnection = (
    libblpapict.blpapi_SessionOptions_setAutoRestartOnDisconnection
)
l_blpapi_SessionOptions_setAutoRestartOnDisconnection.restype = None
l_blpapi_SessionOptions_setBandwidthSaveModeDisabled = (
    libblpapict.blpapi_SessionOptions_setBandwidthSaveModeDisabled
)  # int
l_blpapi_SessionOptions_setClientMode = (
    libblpapict.blpapi_SessionOptions_setClientMode
)
l_blpapi_SessionOptions_setClientMode.restype = None
l_blpapi_SessionOptions_setConnectTimeout = (
    libblpapict.blpapi_SessionOptions_setConnectTimeout
)  # int
l_blpapi_SessionOptions_setDefaultKeepAliveInactivityTime = (
    libblpapict.blpapi_SessionOptions_setDefaultKeepAliveInactivityTime
)  # int
l_blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout = (
    libblpapict.blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout
)  # int
l_blpapi_SessionOptions_setDefaultServices = (
    libblpapict.blpapi_SessionOptions_setDefaultServices
)  # int
l_blpapi_SessionOptions_setDefaultSubscriptionService = (
    libblpapict.blpapi_SessionOptions_setDefaultSubscriptionService
)  # int
l_blpapi_SessionOptions_setDefaultTopicPrefix = (
    libblpapict.blpapi_SessionOptions_setDefaultTopicPrefix
)
l_blpapi_SessionOptions_setDefaultTopicPrefix.restype = None
l_blpapi_SessionOptions_setFlushPublishedEventsTimeout = (
    libblpapict.blpapi_SessionOptions_setFlushPublishedEventsTimeout
)  # int
l_blpapi_SessionOptions_setKeepAliveEnabled = (
    libblpapict.blpapi_SessionOptions_setKeepAliveEnabled
)  # int
l_blpapi_SessionOptions_setMaxEventQueueSize = (
    libblpapict.blpapi_SessionOptions_setMaxEventQueueSize
)
l_blpapi_SessionOptions_setMaxEventQueueSize.restype = None
l_blpapi_SessionOptions_setMaxPendingRequests = (
    libblpapict.blpapi_SessionOptions_setMaxPendingRequests
)
l_blpapi_SessionOptions_setMaxPendingRequests.restype = None
l_blpapi_SessionOptions_setNumStartAttempts = (
    libblpapict.blpapi_SessionOptions_setNumStartAttempts
)
l_blpapi_SessionOptions_setNumStartAttempts.restype = None
l_blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes = (
    libblpapict.blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes
)
l_blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes.restype = None
l_blpapi_SessionOptions_setServerAddress = (
    libblpapict.blpapi_SessionOptions_setServerAddress
)  # int
l_blpapi_SessionOptions_setServerAddressWithProxy = (
    libblpapict.blpapi_SessionOptions_setServerAddressWithProxy
)  # int
l_blpapi_SessionOptions_setServerHost = (
    libblpapict.blpapi_SessionOptions_setServerHost
)  # int
l_blpapi_SessionOptions_setServerPort = (
    libblpapict.blpapi_SessionOptions_setServerPort
)  # int
l_blpapi_SessionOptions_setServiceCheckTimeout = (
    libblpapict.blpapi_SessionOptions_setServiceCheckTimeout
)  # int
l_blpapi_SessionOptions_setServiceDownloadTimeout = (
    libblpapict.blpapi_SessionOptions_setServiceDownloadTimeout
)  # int
l_blpapi_SessionOptions_setSessionIdentityOptions = (
    libblpapict.blpapi_SessionOptions_setSessionIdentityOptions
)  # int
l_blpapi_SessionOptions_setSessionName = (
    libblpapict.blpapi_SessionOptions_setSessionName
)  # int
l_blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark = (
    libblpapict.blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark
)  # int
l_blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark = (
    libblpapict.blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark
)  # int
l_blpapi_SessionOptions_setTlsOptions = (
    libblpapict.blpapi_SessionOptions_setTlsOptions
)
l_blpapi_SessionOptions_setTlsOptions.restype = None
l_blpapi_SessionOptions_slowConsumerWarningHiWaterMark = (
    libblpapict.blpapi_SessionOptions_slowConsumerWarningHiWaterMark
)
l_blpapi_SessionOptions_slowConsumerWarningHiWaterMark.restype = c_float
l_blpapi_SessionOptions_slowConsumerWarningLoWaterMark = (
    libblpapict.blpapi_SessionOptions_slowConsumerWarningLoWaterMark
)
l_blpapi_SessionOptions_slowConsumerWarningLoWaterMark.restype = c_float

l_blpapi_Session_create = libblpapict.blpapi_Session_create
l_blpapi_Session_create.restype = c_void_p
l_blpapi_Session_createSnapshotRequestTemplate = (
    libblpapict.blpapi_Session_createSnapshotRequestTemplate
)  # int
l_blpapi_Session_createSnapshotRequestTemplate.argtypes = [
    c_void_p,
    c_void_p,
    c_char_p,
    c_void_p,
    c_void_p,
]
l_blpapi_Session_destroy = libblpapict.blpapi_Session_destroy
l_blpapi_Session_destroy.restype = None
l_blpapi_Session_getAbstractSession = (
    libblpapict.blpapi_Session_getAbstractSession
)
l_blpapi_Session_getAbstractSession.restype = c_void_p
l_blpapi_Session_nextEvent = libblpapict.blpapi_Session_nextEvent  # int
l_blpapi_Session_resubscribe = libblpapict.blpapi_Session_resubscribe  # int
l_blpapi_Session_resubscribeEx = (
    libblpapict.blpapi_Session_resubscribeEx
)  # int
l_blpapi_Session_resubscribeWithId = (
    libblpapict.blpapi_Session_resubscribeWithId
)  # int
l_blpapi_Session_resubscribeWithIdEx = (
    libblpapict.blpapi_Session_resubscribeWithIdEx
)  # int
l_blpapi_Session_sendRequest = libblpapict.blpapi_Session_sendRequest  # int
l_blpapi_Session_sendRequestTemplate = (
    libblpapict.blpapi_Session_sendRequestTemplate
)  # int
l_blpapi_Session_setStatusCorrelationId = (
    libblpapict.blpapi_Session_setStatusCorrelationId
)  # int
l_blpapi_Session_start = libblpapict.blpapi_Session_start  # int
l_blpapi_Session_startAsync = libblpapict.blpapi_Session_startAsync  # int
l_blpapi_Session_stop = libblpapict.blpapi_Session_stop  # int
l_blpapi_Session_stopAsync = libblpapict.blpapi_Session_stopAsync  # int
l_blpapi_Session_subscribe = libblpapict.blpapi_Session_subscribe  # int
l_blpapi_Session_subscribeEx = libblpapict.blpapi_Session_subscribeEx  # int
l_blpapi_Session_tryNextEvent = libblpapict.blpapi_Session_tryNextEvent  # int
l_blpapi_Session_unsubscribe = libblpapict.blpapi_Session_unsubscribe  # int

l_blpapi_Socks5Config_create = libblpapict.blpapi_Socks5Config_create
l_blpapi_Socks5Config_create.restype = c_void_p
l_blpapi_Socks5Config_destroy = libblpapict.blpapi_Socks5Config_destroy
l_blpapi_Socks5Config_destroy.restype = None
l_blpapi_Socks5Config_print = libblpapict.blpapi_Socks5Config_print  # int

l_blpapi_SubscriptionList_add = libblpapict.blpapi_SubscriptionList_add  # int
l_blpapi_SubscriptionList_add.argtypes = [
    c_void_p,
    c_char_p,
    c_void_p,
    c_void_p,
    c_void_p,
    c_size_t,
    c_size_t,
]
l_blpapi_SubscriptionList_addResolved = (
    libblpapict.blpapi_SubscriptionList_addResolved
)  # int
l_blpapi_SubscriptionList_append = (
    libblpapict.blpapi_SubscriptionList_append
)  # int
l_blpapi_SubscriptionList_clear = (
    libblpapict.blpapi_SubscriptionList_clear
)  # int
l_blpapi_SubscriptionList_correlationIdAt = (
    libblpapict.blpapi_SubscriptionList_correlationIdAt
)  # int
l_blpapi_SubscriptionList_create = libblpapict.blpapi_SubscriptionList_create
l_blpapi_SubscriptionList_create.restype = c_void_p
l_blpapi_SubscriptionList_destroy = libblpapict.blpapi_SubscriptionList_destroy
l_blpapi_SubscriptionList_destroy.restype = None
l_blpapi_SubscriptionList_isResolvedAt = (
    libblpapict.blpapi_SubscriptionList_isResolvedAt
)  # int
l_blpapi_SubscriptionList_size = (
    libblpapict.blpapi_SubscriptionList_size
)  # int
l_blpapi_SubscriptionList_topicStringAt = (
    libblpapict.blpapi_SubscriptionList_topicStringAt
)  # int

l_blpapi_TestUtil_appendMessage = (
    libblpapict.blpapi_TestUtil_appendMessage
)  # int
l_blpapi_TestUtil_createEvent = libblpapict.blpapi_TestUtil_createEvent  # int
l_blpapi_TestUtil_createTopic = libblpapict.blpapi_TestUtil_createTopic  # int
l_blpapi_TestUtil_deserializeService = (
    libblpapict.blpapi_TestUtil_deserializeService
)  # int
l_blpapi_TestUtil_getAdminMessageDefinition = (
    libblpapict.blpapi_TestUtil_getAdminMessageDefinition
)  # int
l_blpapi_TestUtil_serializeService = (
    libblpapict.blpapi_TestUtil_serializeService
)  # int

l_blpapi_TlsOptions_createFromBlobs = (
    libblpapict.blpapi_TlsOptions_createFromBlobs
)
l_blpapi_TlsOptions_createFromBlobs.restype = c_void_p
l_blpapi_TlsOptions_createFromFiles = (
    libblpapict.blpapi_TlsOptions_createFromFiles
)
l_blpapi_TlsOptions_createFromFiles.restype = c_void_p
l_blpapi_TlsOptions_destroy = libblpapict.blpapi_TlsOptions_destroy
l_blpapi_TlsOptions_destroy.restype = None
l_blpapi_TlsOptions_setCrlFetchTimeoutMs = (
    libblpapict.blpapi_TlsOptions_setCrlFetchTimeoutMs
)
l_blpapi_TlsOptions_setCrlFetchTimeoutMs.restype = None
l_blpapi_TlsOptions_setTlsHandshakeTimeoutMs = (
    libblpapict.blpapi_TlsOptions_setTlsHandshakeTimeoutMs
)
l_blpapi_TlsOptions_setTlsHandshakeTimeoutMs.restype = None

l_blpapi_Topic_compare = libblpapict.blpapi_Topic_compare  # int
l_blpapi_Topic_destroy = libblpapict.blpapi_Topic_destroy
l_blpapi_Topic_destroy.restype = None
l_blpapi_Topic_isActive = libblpapict.blpapi_Topic_isActive  # int
l_blpapi_Topic_service = libblpapict.blpapi_Topic_service
l_blpapi_Topic_service.restype = c_void_p

l_blpapi_TopicList_add = libblpapict.blpapi_TopicList_add  # int
l_blpapi_TopicList_addFromMessage = (
    libblpapict.blpapi_TopicList_addFromMessage
)  # int
l_blpapi_TopicList_correlationIdAt = (
    libblpapict.blpapi_TopicList_correlationIdAt
)  # int
l_blpapi_TopicList_correlationIdAt.argtypes = [c_void_p, c_void_p, c_size_t]
l_blpapi_TopicList_create = libblpapict.blpapi_TopicList_create
l_blpapi_TopicList_create.restype = c_void_p
l_blpapi_TopicList_destroy = libblpapict.blpapi_TopicList_destroy
l_blpapi_TopicList_destroy.restype = None
l_blpapi_TopicList_message = libblpapict.blpapi_TopicList_message  # int
l_blpapi_TopicList_messageAt = libblpapict.blpapi_TopicList_messageAt  # int
l_blpapi_TopicList_size = libblpapict.blpapi_TopicList_size  # int
l_blpapi_TopicList_status = libblpapict.blpapi_TopicList_status  # int
l_blpapi_TopicList_statusAt = libblpapict.blpapi_TopicList_statusAt  # int
l_blpapi_TopicList_topicString = (
    libblpapict.blpapi_TopicList_topicString
)  # int
l_blpapi_TopicList_topicStringAt = (
    libblpapict.blpapi_TopicList_topicStringAt
)  # int

l_blpapi_UserAgentInfo_setUserTaskName = (
    libblpapict.blpapi_UserAgentInfo_setUserTaskName
)  # int
l_blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion = (
    libblpapict.blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion
)  # int

l_blpapi_ZfpUtil_getOptionsForLeasedLines = (
    libblpapict.blpapi_ZfpUtil_getOptionsForLeasedLines
)  # int

l_blpapi_getLastErrorDescription = libblpapict.blpapi_getLastErrorDescription
l_blpapi_getLastErrorDescription.restype = c_char_p

l_blpapi_getVersionInfo = libblpapict.blpapi_getVersionInfo
l_blpapi_getVersionInfo.restype = None
l_blpapi_getVersionInfo.argtypes = [
    POINTER(c_int),
    POINTER(c_int),
    POINTER(c_int),
    POINTER(c_int),
]


# signature: int blpapi_AbstractSession_cancel(blpapi_AbstractSession_t *session,const blpapi_CorrelationId_t *correlationIds,size_t numCorrelationIds,const char *requestLabel,int requestLabelLen);
def _blpapi_AbstractSession_cancel(session, correlationIds, requestLabel):
    szcids = len(correlationIds)
    if szcids > 1:
        arraytype = CidStruct * szcids
        ptrs = arraytype(*[c.thestruct for c in correlationIds])
        oneptr = pointer(ptrs)
    elif szcids == 1:
        oneptr = byref(correlationIds[0].thestruct)
    else:
        oneptr = c_void_p()

    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    retCode = l_blpapi_AbstractSession_cancel(
        session,
        oneptr,
        c_size_t(szcids),
        label,
        sz,  # int
    )
    return retCode


# signature: blpapi_Identity_t *blpapi_AbstractSession_createIdentity(blpapi_AbstractSession_t *session);
def _blpapi_AbstractSession_createIdentity(session):
    return getHandleFromPtr(l_blpapi_AbstractSession_createIdentity(session))


# signature: int blpapi_AbstractSession_generateAuthorizedIdentityAsync(blpapi_AbstractSession_t *session,const blpapi_AuthOptions_t *authOptions,blpapi_CorrelationId_t *cid);
def _blpapi_AbstractSession_generateAuthorizedIdentityAsync(
    session, authOptions, cid
):
    # the C layer will OVERWRITE cid with autogen for unset
    cidp = pointer(cid.thestruct)

    return l_blpapi_AbstractSession_generateAuthorizedIdentityAsync(
        session, authOptions, cidp
    )


# signature: int blpapi_AbstractSession_generateManualToken(blpapi_AbstractSession_t *session,blpapi_CorrelationId_t *correlationId,const char *user,const char *manualIp,blpapi_EventQueue_t *eventQueue);
def _blpapi_AbstractSession_generateManualToken(
    session, correlationId, user, manualIp, eventQueue
):
    return l_blpapi_AbstractSession_generateManualToken(
        session,
        byref(correlationId.thestruct),
        charPtrFromPyStr(user),
        charPtrFromPyStr(manualIp),
        eventQueue,
    )


# signature: int blpapi_AbstractSession_generateToken(blpapi_AbstractSession_t *session,blpapi_CorrelationId_t *correlationId,blpapi_EventQueue_t *eventQueue);
def _blpapi_AbstractSession_generateToken(session, correlationId, eventQueue):
    return l_blpapi_AbstractSession_generateToken(
        session, byref(correlationId.thestruct), eventQueue
    )


# signature: int blpapi_AbstractSession_getAuthorizedIdentity(blpapi_AbstractSession_t *session,const blpapi_CorrelationId_t *cid,blpapi_Identity_t **identity);
def _blpapi_AbstractSession_getAuthorizedIdentity(session, cid):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AbstractSession_getAuthorizedIdentity(
        session, byref(cid.thestruct), outp
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AbstractSession_getService(blpapi_AbstractSession_t *session,blpapi_Service_t **service,const char *serviceIdentifier);
def _blpapi_AbstractSession_getService(session, serviceIdentifier):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AbstractSession_getService(
        session, outp, charPtrFromPyStr(serviceIdentifier)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AbstractSession_openService(blpapi_AbstractSession_t *session, const char *serviceIdentifier);
def _blpapi_AbstractSession_openService(session, serviceIdentifier):
    return l_blpapi_AbstractSession_openService(
        session, charPtrFromPyStr(serviceIdentifier)
    )


# signature: int blpapi_AbstractSession_openServiceAsync(blpapi_AbstractSession_t *session,const char *serviceIdentifier,blpapi_CorrelationId_t *correlationId);
def _blpapi_AbstractSession_openServiceAsync(
    session, serviceIdentifier, correlationId
):
    # the C layer will OVERWRITE cid with autogen for unset
    cidp = pointer(correlationId.thestruct)

    return l_blpapi_AbstractSession_openServiceAsync(
        session, charPtrFromPyStr(serviceIdentifier), cidp
    )


# signature: int blpapi_AbstractSession_sendAuthorizationRequest(...)
def _blpapi_AbstractSession_sendAuthorizationRequest(
    session, request, identity, correlationId, eventQueue, requestLabel
):
    # the C layer will OVERWRITE cid with autogen for unset
    cidp = pointer(correlationId.thestruct)

    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_AbstractSession_sendAuthorizationRequest(
        session, request, identity, cidp, eventQueue, label, sz  # int
    )


# signature: int blpapi_AbstractSession_sessionName(blpapi_AbstractSession_t *session,const char **sessionName,size_t *size);
def _blpapi_AbstractSession_sessionName(session):
    out = c_char_p()
    szout = c_size_t()
    outp = pointer(out)
    szoutp = pointer(szout)
    retCode = l_blpapi_AbstractSession_sessionName(session, outp, szoutp)
    return retCode, getSizedStrFromOutput(outp, szoutp, retCode)


# signature: int blpapi_AuthApplication_copy(blpapi_AuthApplication_t *lhs, const blpapi_AuthApplication_t *rhs);
def _blpapi_AuthApplication_copy(lhs, rhs):
    raise NotImplementedError("not called")


# signature: int blpapi_AuthApplication_create(blpapi_AuthApplication_t **app, const char *appName);
def _blpapi_AuthApplication_create(appName):
    authapphandle = c_void_p()
    outp = pointer(authapphandle)
    retCode = l_blpapi_AuthApplication_create(outp, charPtrFromPyStr(appName))
    return retCode, getHandleFromOutput(outp, retCode)


# signature: void blpapi_AuthApplication_destroy(blpapi_AuthApplication_t *app);
def _blpapi_AuthApplication_destroy(app):
    l_blpapi_AuthApplication_destroy(app)


# signature: int blpapi_AuthApplication_duplicate(blpapi_AuthApplication_t **app, const blpapi_AuthApplication_t *dup);
def _blpapi_AuthApplication_duplicate(dup):
    raise NotImplementedError("not called")


# signature: int blpapi_AuthOptions_copy(blpapi_AuthOptions_t *lhs, const blpapi_AuthOptions_t *rhs);
def _blpapi_AuthOptions_copy(lhs, rhs):
    raise NotImplementedError("not called")


# signature: int blpapi_AuthOptions_create_default(blpapi_AuthOptions_t **options);
def _blpapi_AuthOptions_create_default():
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthOptions_create_default(outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AuthOptions_create_forAppMode(blpapi_AuthOptions_t **options, const blpapi_AuthApplication_t *app);
def _blpapi_AuthOptions_create_forAppMode(app):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthOptions_create_forAppMode(outp, app)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AuthOptions_create_forToken(blpapi_AuthOptions_t **options, const blpapi_AuthToken_t *token);
def _blpapi_AuthOptions_create_forToken(token):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthOptions_create_forToken(outp, token)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AuthOptions_create_forUserAndAppMode(blpapi_AuthOptions_t **options,const blpapi_AuthUser_t *user,const blpapi_AuthApplication_t *app);
def _blpapi_AuthOptions_create_forUserAndAppMode(user, app):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthOptions_create_forUserAndAppMode(outp, user, app)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AuthOptions_create_forUserMode(blpapi_AuthOptions_t **options, const blpapi_AuthUser_t *user);
def _blpapi_AuthOptions_create_forUserMode(user):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthOptions_create_forUserMode(outp, user)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: void blpapi_AuthOptions_destroy(blpapi_AuthOptions_t *options);
def _blpapi_AuthOptions_destroy(options):
    l_blpapi_AuthOptions_destroy(options)


# signature: int blpapi_AuthOptions_duplicate(blpapi_AuthOptions_t **options, const blpapi_AuthOptions_t *dup);
def _blpapi_AuthOptions_duplicate(dup):
    raise NotImplementedError("not called")


# signature: int blpapi_AuthToken_copy(blpapi_AuthToken_t *lhs, const blpapi_AuthToken_t *rhs);
def _blpapi_AuthToken_copy(lhs, rhs):
    raise NotImplementedError("not called")


# signature: int blpapi_AuthToken_create(blpapi_AuthToken_t **token, const char *tokenStr);
def _blpapi_AuthToken_create(tokenStr):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthToken_create(outp, charPtrFromPyStr(tokenStr))
    return retCode, getHandleFromOutput(outp, retCode)


# signature: void blpapi_AuthToken_destroy(blpapi_AuthToken_t *token);
def _blpapi_AuthToken_destroy(token):
    l_blpapi_AuthToken_destroy(token)


# signature: int blpapi_AuthToken_duplicate(blpapi_AuthToken_t **token, const blpapi_AuthToken_t *dup);
def _blpapi_AuthToken_duplicate(dup):
    raise NotImplementedError("not called")


# signature: int blpapi_AuthUser_copy(blpapi_AuthUser_t *lhs, const blpapi_AuthUser_t *rhs);
def _blpapi_AuthUser_copy(lhs, rhs):
    raise NotImplementedError("not called")


# signature: int blpapi_AuthUser_createWithActiveDirectoryProperty(blpapi_AuthUser_t **user, const char *propertyName);
def _blpapi_AuthUser_createWithActiveDirectoryProperty(propertyName):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthUser_createWithActiveDirectoryProperty(
        outp, charPtrFromPyStr(propertyName)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AuthUser_createWithLogonName(blpapi_AuthUser_t **user);
def _blpapi_AuthUser_createWithLogonName():
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthUser_createWithLogonName(outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_AuthUser_createWithManualOptions(blpapi_AuthUser_t **user, const char *userId, const char *ipAddress);
def _blpapi_AuthUser_createWithManualOptions(userId, ipAddress):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_AuthUser_createWithManualOptions(
        outp, charPtrFromPyStr(userId), charPtrFromPyStr(ipAddress)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: void blpapi_AuthUser_destroy(blpapi_AuthUser_t *user);
def _blpapi_AuthUser_destroy(user):
    l_blpapi_AuthUser_destroy(user)


# signature: int blpapi_AuthUser_duplicate(blpapi_AuthUser_t **user, const blpapi_AuthUser_t *dup);
def _blpapi_AuthUser_duplicate(dup):
    raise NotImplementedError("not called")


# signature: int blpapi_ConstantList_datatype(const blpapi_ConstantList_t *constant);
def _blpapi_ConstantList_datatype(constant):
    return l_blpapi_ConstantList_datatype(constant)


# signature: const char *blpapi_ConstantList_description(const blpapi_ConstantList_t *list);
def _blpapi_ConstantList_description(clist):
    assert clist is not None and clist.value is not None
    return getStrFromC(l_blpapi_ConstantList_description(clist))


# signature: blpapi_Constant_t *blpapi_ConstantList_getConstant(const blpapi_ConstantList_t *constant,const char *nameString,const blpapi_Name_t *name);
def _blpapi_ConstantList_getConstant(constant, nameString, name):
    value = l_blpapi_ConstantList_getConstant(
        constant, charPtrFromPyStr(nameString), name
    )
    return getHandleFromPtr(value)


# signature: blpapi_Constant_t *blpapi_ConstantList_getConstantAt(const blpapi_ConstantList_t *constant, size_t index);
def _blpapi_ConstantList_getConstantAt(constant, index):
    return getHandleFromPtr(
        l_blpapi_ConstantList_getConstantAt(constant, c_size_t(index))
    )


# signature:
def _blpapi_ConstantList_hasConstant(slist, nameString, name):
    constant = _blpapi_ConstantList_getConstant(slist, nameString, name)
    return constant is not None and constant.value is not None


# signature: blpapi_Name_t *blpapi_ConstantList_name(const blpapi_ConstantList_t *list);
def _blpapi_ConstantList_name(clist):
    return getHandleFromPtr(l_blpapi_ConstantList_name(clist))


# signature: int blpapi_ConstantList_numConstants(const blpapi_ConstantList_t *list);
def _blpapi_ConstantList_numConstants(slist):
    return l_blpapi_ConstantList_numConstants(slist)


# signature: int blpapi_ConstantList_status(const blpapi_ConstantList_t *list);
def _blpapi_ConstantList_status(slist):
    return l_blpapi_ConstantList_status(slist)


# signature: int blpapi_Constant_datatype(const blpapi_Constant_t *constant);
def _blpapi_Constant_datatype(constant):
    return l_blpapi_Constant_datatype(constant)


# signature: const char *blpapi_Constant_description(const blpapi_Constant_t *constant);
def _blpapi_Constant_description(constant):
    return getStrFromC(l_blpapi_Constant_description(constant))


# signature: int blpapi_Constant_getValueAsChar(const blpapi_Constant_t *constant, blpapi_Char_t *buffer);
def _blpapi_Constant_getValueAsChar(constant):
    out = c_char()
    outp = pointer(out)
    retCode = l_blpapi_Constant_getValueAsChar(constant, outp)
    return retCode, getStrFromOutput(outp, retCode)


# signature: int blpapi_Constant_getValueAsDatetime(const blpapi_Constant_t *constant, blpapi_Datetime_t *buffer);
def _blpapi_Constant_getValueAsDatetime(constant):
    out = BDatetime()
    outp = pointer(out)
    retCode = l_blpapi_Constant_getValueAsDatetime(constant, outp)
    return retCode, out if retCode == 0 else None


# signature: int blpapi_Constant_getValueAsFloat32(const blpapi_Constant_t *constant, blpapi_Float32_t *buffer);
def _blpapi_Constant_getValueAsFloat32(constant):
    out = c_float()
    outp = pointer(out)
    retCode = l_blpapi_Constant_getValueAsFloat32(constant, outp)
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Constant_getValueAsFloat64(const blpapi_Constant_t *constant, blpapi_Float64_t *buffer);
def _blpapi_Constant_getValueAsFloat64(constant):
    out = c_double()
    outp = pointer(out)
    retCode = l_blpapi_Constant_getValueAsFloat64(constant, outp)
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Constant_getValueAsInt32(const blpapi_Constant_t *constant, blpapi_Int32_t *buffer);
def _blpapi_Constant_getValueAsInt32(constant):
    out = c_int()
    outp = pointer(out)
    retCode = l_blpapi_Constant_getValueAsInt32(constant, outp)
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Constant_getValueAsInt64(const blpapi_Constant_t *constant, blpapi_Int64_t *buffer);
def _blpapi_Constant_getValueAsInt64(constant):
    out = c_int64()
    outp = pointer(out)
    retCode = l_blpapi_Constant_getValueAsInt64(constant, outp)
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Constant_getValueAsString(const blpapi_Constant_t *constant, const char **buffer);
def _blpapi_Constant_getValueAsString(constant):
    out = c_char_p()
    outp = pointer(out)
    retCode = l_blpapi_Constant_getValueAsString(constant, outp)
    return retCode, getStrFromOutput(outp, retCode)


# signature: blpapi_Name_t *blpapi_Constant_name(const blpapi_Constant_t *constant);
def _blpapi_Constant_name(constant):
    return getHandleFromPtr(l_blpapi_Constant_name(constant))


# signature: int blpapi_Constant_status(const blpapi_Constant_t *constant);
def _blpapi_Constant_status(constant):
    return l_blpapi_Constant_status(constant)


# signature:
def _blpapi_DiagnosticsUtil_memoryInfo_wrapper():
    outp = c_void_p()
    sz = l_blpapi_DiagnosticsUtil_memoryInfo(outp, c_size_t(0))
    if sz < 0:
        return None
    sz += 1
    outp = create_string_buffer(sz)
    sz = l_blpapi_DiagnosticsUtil_memoryInfo(outp, c_size_t(sz))
    return getSizedStrFromBuffer(outp, sz) if sz >= 0 else None


# signature: int blpapi_Element_appendElement(blpapi_Element_t *element, blpapi_Element_t **appendedElement);
def _blpapi_Element_appendElement(element):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_appendElement(element, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature:  int blpapi_Element_datatype(const blpapi_Element_t *element);
def _blpapi_Element_datatype(element):
    return l_blpapi_Element_datatype(element)


# signature:  blpapi_SchemaElementDefinition_t *blpapi_Element_definition(const blpapi_Element_t *element);
def _blpapi_Element_definition(element):
    return getHandleFromPtr(l_blpapi_Element_definition(element))


# signature: int blpapi_Element_getChoice(const blpapi_Element_t *element, blpapi_Element_t **result);
def _blpapi_Element_getChoice(element):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_getChoice(element, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Element_getElementAt(const blpapi_Element_t *element,blpapi_Element_t **result,size_t position);
def _blpapi_Element_getElement(element, nameString, name):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_getElement(
        element, outp, charPtrFromPyStr(nameString), name
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Element_getElementAt(const blpapi_Element_t *element,blpapi_Element_t **result,size_t position);
def _blpapi_Element_getElementAt(element, position):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_getElementAt(element, outp, position)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsBool(const blpapi_Element_t *element, blpapi_Bool_t *buffer, size_t index);
def _blpapi_Element_getValueAsBool(element, index):
    out = c_int()  # int as boolean
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsBool(element, outp, c_size_t(index))
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsBytes(const blpapi_Element_t *element,const char **buffer,size_t *length,size_t index);
def _blpapi_Element_getValueAsBytes(element, index):
    out = c_char_p()
    outp = pointer(out)
    szout = c_size_t()
    szoutp = pointer(szout)
    retCode = l_blpapi_Element_getValueAsBytes(
        element, outp, szoutp, c_size_t(index)
    )
    return retCode, getSizedBytesFromOutput(outp, szoutp, retCode)


# signature: int blpapi_Element_getValueAsChar(const blpapi_Element_t *element, blpapi_Char_t *buffer, size_t index);
def _blpapi_Element_getValueAsChar(element, index):
    out = c_char()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsChar(element, outp, c_size_t(index))
    return retCode, getStrFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsDatetime(const blpapi_Element_t *element,blpapi_Datetime_t *buffer,size_t index);
def _blpapi_Element_getValueAsDatetime(element, index):
    raise NotImplementedError("not called")


# signature: int blpapi_Element_getValueAsElement(const blpapi_Element_t *element,blpapi_Element_t **buffer,size_t index);
def _blpapi_Element_getValueAsElement(element, index):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsElement(
        element, outp, c_size_t(index)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsFloat64(const blpapi_Element_t *element,blpapi_Float64_t *buffer,size_t index);
def _blpapi_Element_getValueAsFloat64(element, index):
    out = c_double()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsFloat64(
        element, outp, c_size_t(index)
    )
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsHighPrecisionDatetime(const blpapi_Element_t *element,blpapi_HighPrecisionDatetime_t *buffer,size_t index);
def _blpapi_Element_getValueAsHighPrecisionDatetime(element, index):
    out = HighPrecisionDatetime()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsHighPrecisionDatetime(
        element, outp, c_size_t(index)
    )
    return retCode, getStructFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsInt32(const blpapi_Element_t *element, blpapi_Int32_t *buffer, size_t index);
def _blpapi_Element_getValueAsInt32(element, index):
    out = c_int()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsInt32(element, outp, c_size_t(index))
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsInt64(const blpapi_Element_t *element, blpapi_Int64_t *buffer, size_t index);
def _blpapi_Element_getValueAsInt64(element, index):
    out = c_int64()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsInt64(element, outp, c_size_t(index))
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsName(const blpapi_Element_t *element, blpapi_Name_t **buffer, size_t index);
def _blpapi_Element_getValueAsName(element, index):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsName(element, outp, c_size_t(index))
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Element_getValueAsString(const blpapi_Element_t *element, const char **buffer, size_t index);
def _blpapi_Element_getValueAsString(element, index):
    out = c_char_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_getValueAsString(element, outp, c_size_t(index))
    return retCode, getStrFromOutput(outp, retCode)


# signature: int blpapi_Element_hasElementEx(const blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,int excludeNullElements,int reserved);
def _blpapi_Element_hasElementEx(
    element, nameString, name, excludeNullElements, reserved
):
    return l_blpapi_Element_hasElementEx(
        element,
        charPtrFromPyStr(nameString),
        name,
        excludeNullElements,
        reserved,
    )


# signature:  int blpapi_Element_isArray(const blpapi_Element_t *element);
def _blpapi_Element_isArray(element):
    return l_blpapi_Element_isArray(element)


# signature:  int blpapi_Element_isComplexType(const blpapi_Element_t *element);
def _blpapi_Element_isComplexType(element):
    return l_blpapi_Element_isComplexType(element)


# signature:  int blpapi_Element_isNullValue(const blpapi_Element_t *element, size_t position);
def _blpapi_Element_isNull(element):
    return l_blpapi_Element_isNull(element)


# signature:  int blpapi_Element_isNullValue(const blpapi_Element_t *element, size_t position);
def _blpapi_Element_isNullValue(element, position):
    return l_blpapi_Element_isNullValue(element, position)


# signature:  int blpapi_Element_isReadOnly(const blpapi_Element_t *element);
def _blpapi_Element_isReadOnly(element):
    return l_blpapi_Element_isReadOnly(element)


# signature:  blpapi_Name_t *blpapi_Element_name(const blpapi_Element_t *element);
def _blpapi_Element_name(element):
    return getHandleFromPtr(l_blpapi_Element_name(element))


# signature:  const char *blpapi_Element_nameString(const blpapi_Element_t *element);
def _blpapi_Element_nameString(element):
    raise NotImplementedError("not called")


# signature:  size_t blpapi_Element_numElements(const blpapi_Element_t *element);
def _blpapi_Element_numElements(element):
    return l_blpapi_Element_numElements(element)


# signature:  size_t blpapi_Element_numValues(const blpapi_Element_t *element);
def _blpapi_Element_numValues(element):
    return l_blpapi_Element_numValues(element)


# signature:
def _blpapi_Element_printHelper(element, level, spacesPerLevel):
    return any_printer(element, l_blpapi_Element_print, level, spacesPerLevel)


# signature: int blpapi_Element_setChoice(blpapi_Element_t *element,blpapi_Element_t **resultElement,const char *nameCstr,const blpapi_Name_t *name,size_t index);
def _blpapi_Element_setChoice(element, nameCstr, name, index):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Element_setChoice(
        element, outp, charPtrFromPyStr(nameCstr), name, c_size_t(index)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Element_setElementBool(blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,blpapi_Bool_t value);
def _blpapi_Element_setElementBool(element, nameString, name, value):
    return l_blpapi_Element_setElementBool(
        element, charPtrFromPyStr(nameString), name, c_int(value)
    )


# signature: int blpapi_Element_setElementBytes(blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,const char *value,size_t length);
def _blpapi_Element_setElementBytes(element, nameString, name, value):
    valuePtr, sz = charPtrWithSizeFromPyStr(value)
    return l_blpapi_Element_setElementBytes(
        element, charPtrFromPyStr(nameString), name, valuePtr, c_size_t(sz)
    )


# signature: int blpapi_Element_setElementFloat32(blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,blpapi_Float32_t value);
def _blpapi_Element_setElementFloat(element, nameString, name, value):
    # The C interface will not silently discard precision to store a 64-bit
    # float in a field whose schema type is 32-bit, however all Python floats
    # are 64-bit, so we explicitly allow narrowing to 32 bits if necessary.

    retCode, field = _blpapi_Element_getElement(element, nameString, name)
    if retCode == 0 and (field is not None and field.value is not None):
        # Able to get field, consider its datatype
        if l_blpapi_Element_datatype(field) == DATATYPE_FLOAT32:
            retCode = l_blpapi_Element_setElementFloat32(
                element, charPtrFromPyStr(nameString), name, c_float(value)
            )
        else:
            retCode = l_blpapi_Element_setElementFloat64(
                element, charPtrFromPyStr(nameString), name, c_double(value)
            )
        return retCode

    # Unable to get field. Try to set element anyway
    retCode = l_blpapi_Element_setElementFloat64(
        element, charPtrFromPyStr(nameString), name, c_double(value)
    )
    if retCode:
        retCode = l_blpapi_Element_setElementFloat32(
            element, charPtrFromPyStr(nameString), name, c_float(value)
        )
    return retCode


# signature: int blpapi_Element_setElementFromName(blpapi_Element_t *element,const char *elementName,const blpapi_Name_t *name,const blpapi_Name_t *buffer);
def _blpapi_Element_setElementFromName(element, elementName, name, buffer):
    return l_blpapi_Element_setElementFromName(
        element, charPtrFromPyStr(elementName), name, buffer
    )


# signature: int blpapi_Element_setElementHighPrecisionDatetime(blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,const blpapi_HighPrecisionDatetime_t *value);
def _blpapi_Element_setElementHighPrecisionDatetime(
    element, nameString, name, value
):
    return l_blpapi_Element_setElementHighPrecisionDatetime(
        element, charPtrFromPyStr(nameString), name, byref(value)
    )


# signature: int blpapi_Element_setElementInt32(blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,blpapi_Int32_t value);
def _blpapi_Element_setElementInt32(element, nameString, name, value):
    return l_blpapi_Element_setElementInt32(
        element, charPtrFromPyStr(nameString), name, c_int(value)
    )


# signature: int blpapi_Element_setElementInt64(blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,blpapi_Int64_t value);
def _blpapi_Element_setElementInt64(element, nameString, name, value):
    return l_blpapi_Element_setElementInt64(
        element, charPtrFromPyStr(nameString), name, c_int64(value)
    )


# signature: int blpapi_Element_setElementString(blpapi_Element_t *element,const char *nameString,const blpapi_Name_t *name,const char *value);
def _blpapi_Element_setElementString(element, nameString, name, value):
    return l_blpapi_Element_setElementString(
        element, charPtrFromPyStr(nameString), name, charPtrFromPyStr(value)
    )


# signature: int blpapi_Element_setValueBool(blpapi_Element_t *element, blpapi_Bool_t value, size_t index);
def _blpapi_Element_setValueBool(element, value, index):
    return l_blpapi_Element_setValueBool(
        element, c_int(value), c_size_t(index)
    )


# signature: int blpapi_Element_setValueBytes(blpapi_Element_t *element,const char *value,size_t length,size_t index);
def _blpapi_Element_setValueBytes(element, value, index):
    valuePtr, sz = charPtrWithSizeFromPyStr(value)
    return l_blpapi_Element_setValueBytes(
        element, valuePtr, c_size_t(sz), c_size_t(index)
    )


# signature: int blpapi_Element_setValueFloat32(blpapi_Element_t *element, blpapi_Float32_t value, size_t index);
def _blpapi_Element_setValueFloat(element, value, index):
    # The C interface will not silently discard precision to store a 64-bit
    # float in a field whose schema type is 32-bit, however all Python floats
    # are 64-bit, so we explicitly allow narrowing to 32 bits if necessary.

    # Consider field datatype
    if l_blpapi_Element_datatype(element) == DATATYPE_FLOAT32:
        retCode = l_blpapi_Element_setValueFloat32(
            element, c_float(value), c_size_t(index)
        )
    else:
        retCode = l_blpapi_Element_setValueFloat64(
            element, c_double(value), c_size_t(index)
        )
    return retCode


# signature: int blpapi_Element_setValueFromName(blpapi_Element_t *element, const blpapi_Name_t *value, size_t index);
def _blpapi_Element_setValueFromName(element, value, index):
    return l_blpapi_Element_setValueFromName(element, value, c_size_t(index))


# signature: int blpapi_Element_setValueHighPrecisionDatetime(blpapi_Element_t *element,const blpapi_HighPrecisionDatetime_t *value,size_t index);
def _blpapi_Element_setValueHighPrecisionDatetime(element, value, index):
    return l_blpapi_Element_setValueHighPrecisionDatetime(
        element, byref(value), c_size_t(index)
    )


# signature: int blpapi_Element_setValueInt32(blpapi_Element_t *element, blpapi_Int32_t value, size_t index);
def _blpapi_Element_setValueInt32(element, value, index):
    return l_blpapi_Element_setValueInt32(
        element, c_int(value), c_size_t(index)
    )


# signature: int blpapi_Element_setValueInt64(blpapi_Element_t *element, blpapi_Int64_t value, size_t index);
def _blpapi_Element_setValueInt64(element, value, index):
    return l_blpapi_Element_setValueInt64(
        element, c_int64(value), c_size_t(index)
    )


# signature: int blpapi_Element_setValueString(blpapi_Element_t *element, const char *value, size_t index);
def _blpapi_Element_setValueString(element, value, index):
    return l_blpapi_Element_setValueString(
        element, charPtrFromPyStr(value), c_size_t(index)
    )


# signature: int blpapi_Element_toJson(const blpapi_Element_t *element, blpapi_StreamWriter_t streamWriter, void *stream);
def _blpapi_Element_toJson(element, streamWriter, stream):
    return l_blpapi_Element_toJson(element, streamWriter, stream)


# signature: int blpapi_Element_fromJson(const blpapi_Element_t *element, char const *json);
def _blpapi_Element_fromJson(element, json):
    return l_blpapi_Element_fromJson(element, charPtrFromPyStr(json))


# signature:
def _blpapi_Element_toJsonHelper(element):
    """Convert element to JSON string"""
    out = StringIO()
    writer = StreamWrapper()
    outparam = voidFromPyObject(out)
    retCode = l_blpapi_Element_toJson(element, writer.get(), outparam)
    if retCode:
        return retCode, None
    out.seek(0)
    return retCode, out.read()


# signature:
def _blpapi_Element_toPy(element):
    return libffastcalls.blpapi_Element_toPy(element)


# signature: blpapi_EventDispatcher_t *blpapi_EventDispatcher_create(size_t numDispatcherThreads);
def _blpapi_EventDispatcher_create(numDispatcherThreads):
    return getHandleFromPtr(
        l_blpapi_EventDispatcher_create(c_size_t(numDispatcherThreads))
    )


# signature: void blpapi_EventDispatcher_destroy(blpapi_EventDispatcher_t *handle);
def _blpapi_EventDispatcher_destroy(handle):
    l_blpapi_EventDispatcher_destroy(handle)


# signature: int blpapi_EventDispatcher_start(blpapi_EventDispatcher_t *handle);
def _blpapi_EventDispatcher_start(handle):
    return l_blpapi_EventDispatcher_start(handle)


# signature: int blpapi_EventDispatcher_stop(blpapi_EventDispatcher_t *handle, int async);
def _blpapi_EventDispatcher_stop(handle, asynch):
    return l_blpapi_EventDispatcher_stop(handle, c_int(asynch))


# signature: int blpapi_EventFormatter_appendElement(blpapi_EventFormatter_t *formatter);
def _blpapi_EventFormatter_appendElement(formatter):
    return l_blpapi_EventFormatter_appendElement(formatter)


# signature: int blpapi_EventFormatter_appendFragmentedRecapMessage(blpapi_EventFormatter_t *formatter,const char *typeString,blpapi_Name_t *typeName,const blpapi_Topic_t *topic,const blpapi_CorrelationId_t *cid,int fragmentType);
def _blpapi_EventFormatter_appendFragmentedRecapMessage(
    formatter, typeString, typeName, topic, cid, fragmentType
):
    return l_blpapi_EventFormatter_appendFragmentedRecapMessage(
        formatter,
        charPtrFromPyStr(typeString),
        typeName,
        topic,
        byref(cid.thestruct) if cid is not None else None,
        fragmentType,
    )


# signature: int blpapi_EventFormatter_appendFragmentedRecapMessageSeq(blpapi_EventFormatter_t *formatter,const char *typeString,blpapi_Name_t *typeName,const blpapi_Topic_t *topic,int fragmentType,unsigned int sequenceNumber);
def _blpapi_EventFormatter_appendFragmentedRecapMessageSeq(
    formatter, typeString, typeName, topic, fragmentType, sequenceNumber
):
    return l_blpapi_EventFormatter_appendFragmentedRecapMessageSeq(
        formatter,
        charPtrFromPyStr(typeString),
        typeName,
        topic,
        fragmentType,
        c_uint32(sequenceNumber),
    )


# signature: int blpapi_EventFormatter_appendMessage(blpapi_EventFormatter_t *formatter,const char *typeString,blpapi_Name_t *typeName,const blpapi_Topic_t *topic);
def _blpapi_EventFormatter_appendMessage(
    formatter, typeString, typeName, topic
):
    return l_blpapi_EventFormatter_appendMessage(
        formatter, charPtrFromPyStr(typeString), typeName, topic
    )


# signature: int blpapi_EventFormatter_appendMessageSeq(blpapi_EventFormatter_t *formatter,const char *typeString,blpapi_Name_t *typeName,const blpapi_Topic_t *topic,unsigned int sequenceNumber,unsigned int);
def _blpapi_EventFormatter_appendMessageSeq(
    formatter, typeString, typeName, topic, sequenceNumber, aUIntArg
):
    return l_blpapi_EventFormatter_appendMessageSeq(
        formatter,
        charPtrFromPyStr(typeString),
        typeName,
        topic,
        c_uint32(sequenceNumber),
        c_uint(aUIntArg),
    )


# signature: int blpapi_EventFormatter_appendRecapMessage(blpapi_EventFormatter_t *formatter,const blpapi_Topic_t *topic,const blpapi_CorrelationId_t *cid);
def _blpapi_EventFormatter_appendRecapMessage(formatter, topic, cid):
    return l_blpapi_EventFormatter_appendRecapMessage(
        formatter,
        topic,
        byref(cid.thestruct) if cid is not None else None,
    )


# signature: int blpapi_EventFormatter_appendRecapMessageSeq(blpapi_EventFormatter_t *formatter,const blpapi_Topic_t *topic,const blpapi_CorrelationId_t *cid,unsigned int sequenceNumber,unsigned int);
def _blpapi_EventFormatter_appendRecapMessageSeq(
    formatter, topic, cid, sequenceNumber, aUIntArg
):
    return l_blpapi_EventFormatter_appendRecapMessageSeq(
        formatter,
        topic,
        byref(cid.thestruct) if cid is not None else None,
        c_uint32(sequenceNumber),
        c_uint(aUIntArg),
    )


# signature: int blpapi_EventFormatter_appendResponse(blpapi_EventFormatter_t *formatter,const char *typeString,blpapi_Name_t *typeName);
def _blpapi_EventFormatter_appendResponse(formatter, typeString, typeName):
    return l_blpapi_EventFormatter_appendResponse(
        formatter, charPtrFromPyStr(typeString), typeName
    )


# signature: int blpapi_EventFormatter_appendValueBool(blpapi_EventFormatter_t *formatter, blpapi_Bool_t value);
def _blpapi_EventFormatter_appendValueBool(formatter, value):
    return l_blpapi_EventFormatter_appendValueBool(
        formatter, c_int(value)
    )  # int as boolean


# signature: int blpapi_EventFormatter_appendValueChar(blpapi_EventFormatter_t *formatter, char value);
def _blpapi_EventFormatter_appendValueChar(formatter, value):
    return l_blpapi_EventFormatter_appendValueChar(formatter, c_char(value))


# signature: int blpapi_EventFormatter_appendValueFloat32(blpapi_EventFormatter_t *formatter, blpapi_Float32_t value);
def _blpapi_EventFormatter_appendValueFloat(formatter, value):
    # The C interface will not silently discard precision to store a 64-bit
    # float in a field whose schema type is 32-bit, however all Python floats
    # are 64-bit, so we explicitly allow narrowing to 32 bits if necessary.

    retCode = l_blpapi_EventFormatter_appendValueFloat64(
        formatter, c_double(value)
    )
    if retCode:
        retCode = l_blpapi_EventFormatter_appendValueFloat32(
            formatter, c_float(value)
        )
    return retCode


# signature: int blpapi_EventFormatter_appendValueFromName(blpapi_EventFormatter_t *formatter, const blpapi_Name_t *value);
def _blpapi_EventFormatter_appendValueFromName(formatter, value):
    return l_blpapi_EventFormatter_appendValueFromName(formatter, value)


# signature: int blpapi_EventFormatter_appendValueHighPrecisionDatetime(blpapi_EventFormatter_t *formatter,const blpapi_HighPrecisionDatetime_t *value);
def _blpapi_EventFormatter_appendValueHighPrecisionDatetime(formatter, value):
    return l_blpapi_EventFormatter_appendValueHighPrecisionDatetime(
        formatter, byref(value)
    )


# signature: int blpapi_EventFormatter_appendValueInt32(blpapi_EventFormatter_t *formatter, blpapi_Int32_t value);
def _blpapi_EventFormatter_appendValueInt32(formatter, value):
    return l_blpapi_EventFormatter_appendValueInt32(formatter, c_int(value))


# signature: int blpapi_EventFormatter_appendValueInt64(blpapi_EventFormatter_t *formatter, blpapi_Int64_t value);
def _blpapi_EventFormatter_appendValueInt64(formatter, value):
    return l_blpapi_EventFormatter_appendValueInt64(formatter, c_int64(value))


# signature: int blpapi_EventFormatter_appendValueString(blpapi_EventFormatter_t *formatter, const char *value);
def _blpapi_EventFormatter_appendValueString(formatter, value):
    return l_blpapi_EventFormatter_appendValueString(
        formatter, charPtrFromPyStr(value)
    )


# signature: blpapi_EventFormatter_t *blpapi_EventFormatter_create(blpapi_Event_t *event);
def _blpapi_EventFormatter_create(event):
    return getHandleFromPtr(l_blpapi_EventFormatter_create(event))


# signature: void blpapi_EventFormatter_destroy(blpapi_EventFormatter_t *victim);
def _blpapi_EventFormatter_destroy(victim):
    l_blpapi_EventFormatter_destroy(victim)


# signature: int blpapi_EventFormatter_popElement(blpapi_EventFormatter_t *formatter);
def _blpapi_EventFormatter_popElement(formatter):
    return l_blpapi_EventFormatter_popElement(formatter)


# signature: int blpapi_EventFormatter_pushElement(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName);
def _blpapi_EventFormatter_pushElement(formatter, typeString, typeName):
    return l_blpapi_EventFormatter_pushElement(
        formatter, charPtrFromPyStr(typeString), typeName
    )


# signature: int blpapi_EventFormatter_setValueBool(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,blpapi_Bool_t value);
def _blpapi_EventFormatter_setValueBool(
    formatter, typeString, typeName, value
):
    return l_blpapi_EventFormatter_setValueBool(
        formatter, charPtrFromPyStr(typeString), typeName, c_int(value)
    )  # int as boolean


# signature: int blpapi_EventFormatter_setValueBytes(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,const char *value,size_t length);
def _blpapi_EventFormatter_setValueBytes(
    formatter, typeString, typeName, value
):
    valuePtr, sz = charPtrWithSizeFromPyStr(value)
    return l_blpapi_EventFormatter_setValueBytes(
        formatter,
        charPtrFromPyStr(typeString),
        typeName,
        valuePtr,
        c_size_t(sz),
    )


# signature: int blpapi_EventFormatter_setValueChar(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,char value);
def _blpapi_EventFormatter_setValueChar(
    formatter, typeString, typeName, value
):
    return l_blpapi_EventFormatter_setValueChar(
        formatter,
        charPtrFromPyStr(typeString),
        typeName,
        c_char(value),
    )


# signature: int blpapi_EventFormatter_setValueFloat32(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,blpapi_Float32_t value);
def _blpapi_EventFormatter_setValueFloat(
    formatter, typeString, typeName, value
):
    # The C interface will not silently discard precision to store a 64-bit
    # float in a field whose schema type is 32-bit, however all Python floats
    # are 64-bit, so we explicitly allow narrowing to 32 bits if necessary.

    retCode = l_blpapi_EventFormatter_setValueFloat64(
        formatter, charPtrFromPyStr(typeString), typeName, c_double(value)
    )
    if retCode:
        retCode = l_blpapi_EventFormatter_setValueFloat32(
            formatter, charPtrFromPyStr(typeString), typeName, c_float(value)
        )
    return retCode


# signature: int blpapi_EventFormatter_setValueFromName(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,const blpapi_Name_t *value);
def _blpapi_EventFormatter_setValueFromName(
    formatter, typeString, typeName, value
):
    return l_blpapi_EventFormatter_setValueFromName(
        formatter, charPtrFromPyStr(typeString), typeName, value
    )


# signature: int blpapi_EventFormatter_setValueHighPrecisionDatetime(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,const blpapi_HighPrecisionDatetime_t *value);
def _blpapi_EventFormatter_setValueHighPrecisionDatetime(
    formatter, typeString, typeName, value
):
    return l_blpapi_EventFormatter_setValueHighPrecisionDatetime(
        formatter, charPtrFromPyStr(typeString), typeName, byref(value)
    )


# signature: int blpapi_EventFormatter_setValueInt32(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,blpapi_Int32_t value);
def _blpapi_EventFormatter_setValueInt32(
    formatter, typeString, typeName, value
):
    return l_blpapi_EventFormatter_setValueInt32(
        formatter, charPtrFromPyStr(typeString), typeName, c_int(value)
    )


# signature: int blpapi_EventFormatter_setValueInt64(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,blpapi_Int64_t value);
def _blpapi_EventFormatter_setValueInt64(
    formatter, typeString, typeName, value
):
    return l_blpapi_EventFormatter_setValueInt64(
        formatter, charPtrFromPyStr(typeString), typeName, c_int64(value)
    )


# signature: int blpapi_EventFormatter_setValueNull(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName);
def _blpapi_EventFormatter_setValueNull(formatter, typeString, typeName):
    return l_blpapi_EventFormatter_setValueNull(
        formatter,
        charPtrFromPyStr(typeString),
        typeName,
    )


# signature: int blpapi_EventFormatter_setValueString(blpapi_EventFormatter_t *formatter,const char *typeString,const blpapi_Name_t *typeName,const char *value);
def _blpapi_EventFormatter_setValueString(
    formatter, typeString, typeName, value
):
    return l_blpapi_EventFormatter_setValueString(
        formatter,
        charPtrFromPyStr(typeString),
        typeName,
        charPtrFromPyStr(value),
    )


# signature: int blpapi_EventFormatter_getElement(blpapi_EventFormatter_t *formatter, blpapi_Element_t **element);
def _blpapi_EventFormatter_getElement(formatter):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_EventFormatter_getElement(formatter, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: blpapi_EventQueue_t *blpapi_EventQueue_create(void);
def _blpapi_EventQueue_create():
    return getHandleFromPtr(l_blpapi_EventQueue_create())


# signature: int blpapi_EventQueue_destroy(blpapi_EventQueue_t *eventQueue);
def _blpapi_EventQueue_destroy(eventQueue):
    return l_blpapi_EventQueue_destroy(eventQueue)


# signature: blpapi_Event_t *blpapi_EventQueue_nextEvent(blpapi_EventQueue_t *eventQueue, int timeout);
def _blpapi_EventQueue_nextEvent(eventQueue, timeout):
    return getHandleFromPtr(l_blpapi_EventQueue_nextEvent(eventQueue, timeout))


# signature: int blpapi_EventQueue_purge(blpapi_EventQueue_t *eventQueue);
def _blpapi_EventQueue_purge(eventQueue):
    return l_blpapi_EventQueue_purge(eventQueue)


# signature: int blpapi_EventQueue_tryNextEvent(blpapi_EventQueue_t *eventQueue, blpapi_Event_t **eventPointer);
def _blpapi_EventQueue_tryNextEvent(eventQueue):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_EventQueue_tryNextEvent(eventQueue, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Event_eventType(const blpapi_Event_t *event);
def _blpapi_Event_eventType(event):
    return l_blpapi_Event_eventType(event)


# signature: int blpapi_Event_release(const blpapi_Event_t *event);
def _blpapi_Event_release(event):
    return l_blpapi_Event_release(event)


# signature: int blpapi_HighPrecisionDatetime_compare(const blpapi_HighPrecisionDatetime_t *lhs,const blpapi_HighPrecisionDatetime_t *rhs);
def _blpapi_HighPrecisionDatetime_compare(lhs, rhs):
    raise NotImplementedError("not called")


# signature: int blpapi_HighPrecisionDatetime_fromTimePoint(blpapi_HighPrecisionDatetime_t *datetime,const blpapi_TimePoint_t *timePoint,short offset);
def _blpapi_HighPrecisionDatetime_fromTimePoint(timepoint, offset):
    out = HighPrecisionDatetime()
    outp = pointer(out)
    retCode = l_blpapi_HighPrecisionDatetime_fromTimePoint(
        outp, byref(timepoint), c_int16(offset)
    )
    return retCode, getStructFromOutput(outp, retCode)


# signature:
def _blpapi_HighPrecisionDatetime_fromTimePoint_wrapper(timepoint):
    _, result = _blpapi_HighPrecisionDatetime_fromTimePoint(timepoint, 0)
    return result


# signature: int blpapi_HighPrecisionDatetime_print(const blpapi_HighPrecisionDatetime_t *datetime,blpapi_StreamWriter_t streamWriter,void *stream,int level,int spacesPerLevel);
def _blpapi_HighPrecisionDatetime_print(
    datetime, streamWriter, stream, level, spacesPerLevel
):
    raise NotImplementedError("not called")


# signature: int blpapi_HighResolutionClock_now(blpapi_TimePoint_t *timePoint);
def _blpapi_HighResolutionClock_now():
    out = TimePoint()
    outp = pointer(out)
    retCode = l_blpapi_HighResolutionClock_now(outp)
    return retCode, getStructFromOutput(outp, retCode)


# signature: int blpapi_Identity_addRef(blpapi_Identity_t *handle);
def _blpapi_Identity_addRef(handle):
    raise NotImplementedError("not called")  # only needed on copy


# signature: int blpapi_Identity_getSeatType(const blpapi_Identity_t *handle, int *seatType);
def _blpapi_Identity_getSeatType(handle):
    out = c_int()
    outp = pointer(out)
    retCode = l_blpapi_Identity_getSeatType(handle, outp)
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_Identity_hasEntitlements(const blpapi_Identity_t *handle,const blpapi_Service_t *service,const blpapi_Element_t *eidElement,const int *entitlementIds,size_t numEntitlements,int *failedEntitlements,int *failedEntitlementsCount);
def _blpapi_Identity_hasEntitlements(
    handle,
    service,
    eidElement,
    entitlementIds,
    numEntitlements,
    failedEntitlements,
    failedEntitlementsCount,
):
    return l_blpapi_Identity_hasEntitlements(
        handle,
        service,
        eidElement,
        c_void_p() if entitlementIds is None else byref(entitlementIds),
        c_size_t(numEntitlements),
        (
            c_void_p()
            if failedEntitlements is None
            else pointer(failedEntitlements)
        ),
        (
            c_void_p()
            if failedEntitlementsCount is None
            else pointer(failedEntitlementsCount)
        ),
    )


# signature: int blpapi_Identity_isAuthorized(const blpapi_Identity_t *handle, const blpapi_Service_t *service);
def _blpapi_Identity_isAuthorized(handle, service):
    return l_blpapi_Identity_isAuthorized(handle, service)


# signature: void blpapi_Identity_release(blpapi_Identity_t *handle);
def _blpapi_Identity_release(handle):
    l_blpapi_Identity_release(handle)


# signature: void blpapi_Logging_logTestMessage(blpapi_Logging_Severity_t severity);
def _blpapi_Logging_logTestMessage(severity):
    l_blpapi_Logging_logTestMessage(severity)


class LoggingCallbackWrapper:
    # typedef void (*blpapi_Logging_Func_t)(
    #        blpapi_UInt64_t threadId,
    #        int severity,
    #        blpapi_Datetime_t timestamp,
    #        const char *category,
    #        const char *message);
    _cftype = CFUNCTYPE(None, c_uint64, c_int, BDatetime, c_char_p, c_char_p)

    @staticmethod
    def get(cb: Optional[Callable]) -> Callable:
        return (
            LoggingCallbackWrapper._cftype(cb)
            if cb is not None
            else c_void_p(0)
        )


# signature: blpapi_Logging_registerCallback(logging_cb, int);
def _blpapi_Logging_registerCallback(callback, thresholdSeverity):
    proxy = LoggingCallbackWrapper.get(callback)
    return l_blpapi_Logging_registerCallback(proxy, thresholdSeverity), proxy


# signature: int blpapi_MessageFormatter_FormatMessageJson(blpapi_MessageFormatter_t *formatter, const char *message);
def _blpapi_MessageFormatter_FormatMessageJson(formatter, message):
    return l_blpapi_MessageFormatter_FormatMessageJson(
        formatter, charPtrFromPyStr(message)
    )


# signature: int blpapi_MessageFormatter_FormatMessageXml(blpapi_MessageFormatter_t *formatter, const char *message);
def _blpapi_MessageFormatter_FormatMessageXml(formatter, message):
    return l_blpapi_MessageFormatter_FormatMessageXml(
        formatter, charPtrFromPyStr(message)
    )


# signature: int blpapi_MessageFormatter_appendElement(blpapi_MessageFormatter_t *formatter);
def _blpapi_MessageFormatter_appendElement(formatter):
    return l_blpapi_MessageFormatter_appendElement(formatter)


# signature: int blpapi_MessageFormatter_appendValueBool(blpapi_MessageFormatter_t *formatter, blpapi_Bool_t value);
def _blpapi_MessageFormatter_appendValueBool(formatter, value):
    return l_blpapi_MessageFormatter_appendValueBool(
        formatter, c_int(value)
    )  # int as boolean


# signature: int blpapi_MessageFormatter_appendValueChar(blpapi_MessageFormatter_t *formatter, char value);
def _blpapi_MessageFormatter_appendValueChar(formatter, value):
    return l_blpapi_MessageFormatter_appendValueChar(formatter, c_char(value))


# signature: int blpapi_MessageFormatter_appendValueDatetime(blpapi_MessageFormatter_t *formatter, const blpapi_Datetime_t *value);
def _blpapi_MessageFormatter_appendValueDatetime(formatter, value):
    return l_blpapi_MessageFormatter_appendValueDatetime(
        formatter, byref(value)
    )


# signature: int blpapi_MessageFormatter_appendValueFloat32(blpapi_MessageFormatter_t *formatter, blpapi_Float32_t value);
def _blpapi_MessageFormatter_appendValueFloat(formatter, value):
    # The C interface will not silently discard precision to store a 64-bit
    # float in a field whose schema type is 32-bit, however all Python floats
    # are 64-bit, so we explicitly allow narrowing to 32 bits if necessary.

    retCode = l_blpapi_MessageFormatter_appendValueFloat64(
        formatter, c_double(value)
    )
    if retCode:
        retCode = l_blpapi_MessageFormatter_appendValueFloat32(
            formatter, c_float(value)
        )
    return retCode


# signature: int blpapi_MessageFormatter_appendValueFloat32(blpapi_MessageFormatter_t *formatter, blpapi_Float32_t value);
def _blpapi_MessageFormatter_appendValueFloat32(formatter, value):
    return l_blpapi_MessageFormatter_appendValueFloat32(
        formatter, c_float(value)
    )


# signature: int blpapi_MessageFormatter_appendValueFloat64(blpapi_MessageFormatter_t *formatter, blpapi_Float64_t value);
def _blpapi_MessageFormatter_appendValueFloat64(formatter, value):
    return l_blpapi_MessageFormatter_appendValueFloat64(
        formatter, c_double(value)
    )


# signature: int blpapi_MessageFormatter_appendValueFromName(blpapi_MessageFormatter_t *formatter, const blpapi_Name_t *value);
def _blpapi_MessageFormatter_appendValueFromName(formatter, value):
    return l_blpapi_MessageFormatter_appendValueFromName(formatter, value)


# signature: int blpapi_MessageFormatter_appendValueHighPrecisionDatetime(blpapi_MessageFormatter_t *formatter,const blpapi_HighPrecisionDatetime_t *value);
def _blpapi_MessageFormatter_appendValueHighPrecisionDatetime(
    formatter, value
):
    return l_blpapi_MessageFormatter_appendValueHighPrecisionDatetime(
        formatter, byref(value)
    )


# signature: int blpapi_MessageFormatter_appendValueInt32(blpapi_MessageFormatter_t *formatter, blpapi_Int32_t value);
def _blpapi_MessageFormatter_appendValueInt32(formatter, value):
    return l_blpapi_MessageFormatter_appendValueInt32(formatter, value)


# signature: int blpapi_MessageFormatter_appendValueInt64(blpapi_MessageFormatter_t *formatter, blpapi_Int64_t value);
def _blpapi_MessageFormatter_appendValueInt64(formatter, value):
    return l_blpapi_MessageFormatter_appendValueInt64(
        formatter, c_int64(value)
    )


# signature: int blpapi_MessageFormatter_appendValueString(blpapi_MessageFormatter_t *formatter, const char *value);
def _blpapi_MessageFormatter_appendValueString(formatter, value):
    return l_blpapi_MessageFormatter_appendValueString(
        formatter, charPtrFromPyStr(value)
    )


# signature: int blpapi_MessageFormatter_assign(blpapi_MessageFormatter_t **lhs, const blpapi_MessageFormatter_t *rhs);
def _blpapi_MessageFormatter_assign(rhs):
    raise NotImplementedError("not called")


# signature: int blpapi_MessageFormatter_copy(blpapi_MessageFormatter_t **formatter,const blpapi_MessageFormatter_t *original);
def _blpapi_MessageFormatter_copy(original):
    raise NotImplementedError("not called")


# signature: int blpapi_MessageFormatter_destroy(blpapi_MessageFormatter_t *formatter);
def _blpapi_MessageFormatter_destroy(formatter):
    return l_blpapi_MessageFormatter_destroy(formatter)


# signature: int blpapi_MessageFormatter_popElement(blpapi_MessageFormatter_t *formatter);
def _blpapi_MessageFormatter_popElement(formatter):
    return l_blpapi_MessageFormatter_popElement(formatter)


# signature: int blpapi_MessageFormatter_pushElement(blpapi_MessageFormatter_t *formatter, const blpapi_Name_t *typeName);
def _blpapi_MessageFormatter_pushElement(formatter, typeName):
    return l_blpapi_MessageFormatter_pushElement(formatter, typeName)


# signature: int blpapi_MessageFormatter_setValueBool(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,blpapi_Bool_t value);
def _blpapi_MessageFormatter_setValueBool(formatter, typeName, value):
    return l_blpapi_MessageFormatter_setValueBool(
        formatter, typeName, c_int(value)
    )  # int as boolean


# signature: int blpapi_MessageFormatter_setValueBytes(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,const char *value,size_t length);
def _blpapi_MessageFormatter_setValueBytes(formatter, typeName, value):
    valuePtr, sz = charPtrWithSizeFromPyStr(value)
    return l_blpapi_MessageFormatter_setValueBytes(
        formatter, typeName, valuePtr, c_size_t(sz)
    )


# signature: int blpapi_MessageFormatter_setValueChar(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,char value);
def _blpapi_MessageFormatter_setValueChar(formatter, typeName, value):
    return l_blpapi_MessageFormatter_setValueChar(
        formatter, typeName, c_char(value)
    )


# signature: int blpapi_MessageFormatter_setValueDatetime(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,const blpapi_Datetime_t *value);
def _blpapi_MessageFormatter_setValueDatetime(formatter, typeName, value):
    return l_blpapi_MessageFormatter_setValueDatetime(
        formatter, typeName, byref(value)
    )


# signature: int blpapi_MessageFormatter_setValueFloat32(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,blpapi_Float32_t value);
def _blpapi_MessageFormatter_setValueFloat(formatter, typeName, value):
    # The C interface will not silently discard precision to store a 64-bit
    # float in a field whose schema type is 32-bit, however all Python floats
    # are 64-bit, so we explicitly allow narrowing to 32 bits if necessary.

    retCode = l_blpapi_MessageFormatter_setValueFloat64(
        formatter, typeName, c_double(value)
    )
    if retCode:
        retCode = l_blpapi_MessageFormatter_setValueFloat32(
            formatter, typeName, c_float(value)
        )
    return retCode


# signature: int blpapi_MessageFormatter_setValueFloat32(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,blpapi_Float32_t value);
def _blpapi_MessageFormatter_setValueFloat32(formatter, typeName, value):
    return l_blpapi_MessageFormatter_appendValueFloat32(
        formatter, typeName, c_float(value)
    )


# signature: int blpapi_MessageFormatter_setValueFloat64(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,blpapi_Float64_t value);
def _blpapi_MessageFormatter_setValueFloat64(formatter, typeName, value):
    return l_blpapi_MessageFormatter_appendValueFloat64(
        formatter, typeName, c_double(value)
    )


# signature: int blpapi_MessageFormatter_setValueFromName(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,const blpapi_Name_t *value);
def _blpapi_MessageFormatter_setValueFromName(formatter, typeName, value):
    return l_blpapi_MessageFormatter_setValueFromName(
        formatter, typeName, value
    )


# signature: int blpapi_MessageFormatter_setValueHighPrecisionDatetime(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,const blpapi_HighPrecisionDatetime_t *value);
def _blpapi_MessageFormatter_setValueHighPrecisionDatetime(
    formatter, typeName, value
):
    return l_blpapi_MessageFormatter_setValueHighPrecisionDatetime(
        formatter, typeName, byref(value)
    )


# signature: int blpapi_MessageFormatter_setValueInt32(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,blpapi_Int32_t value);
def _blpapi_MessageFormatter_setValueInt32(formatter, typeName, value):
    return l_blpapi_MessageFormatter_setValueInt32(formatter, typeName, value)


# signature: int blpapi_MessageFormatter_setValueInt64(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,blpapi_Int64_t value);
def _blpapi_MessageFormatter_setValueInt64(formatter, typeName, value):
    return l_blpapi_MessageFormatter_setValueInt64(
        formatter, typeName, c_int64(value)
    )


# signature: int blpapi_MessageFormatter_setValueNull(blpapi_MessageFormatter_t *formatter, const blpapi_Name_t *typeName);
def _blpapi_MessageFormatter_setValueNull(formatter, typeName):
    return l_blpapi_MessageFormatter_setValueNull(formatter, typeName)


# signature: int blpapi_MessageFormatter_setValueString(blpapi_MessageFormatter_t *formatter,const blpapi_Name_t *typeName,const char *value);
def _blpapi_MessageFormatter_setValueString(formatter, typeName, value):
    return l_blpapi_MessageFormatter_setValueString(
        formatter, typeName, charPtrFromPyStr(value)
    )


# signature: int blpapi_MessageFormatter_getElement(blpapi_MessageFormatter_t *formatter, blpapi_Element_t **element);
def _blpapi_MessageFormatter_getElement(formatter):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_MessageFormatter_getElement(formatter, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: blpapi_MessageIterator_t *blpapi_MessageIterator_create(const blpapi_Event_t *event);
def _blpapi_MessageIterator_create(event):
    return getHandleFromPtr(l_blpapi_MessageIterator_create(event))


# signature: void blpapi_MessageIterator_destroy(blpapi_MessageIterator_t *iterator);
def _blpapi_MessageIterator_destroy(iterator):
    l_blpapi_MessageIterator_destroy(iterator)


# signature: int blpapi_MessageIterator_next(blpapi_MessageIterator_t *iterator, blpapi_Message_t **result);
def _blpapi_MessageIterator_next(iterator):
    message_pp = c_void_p()
    outp = pointer(message_pp)
    retCode = l_blpapi_MessageIterator_next(iterator, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_MessageProperties_assign(blpapi_MessageProperties_t *lhs,const blpapi_MessageProperties_t *rhs);
def _blpapi_MessageProperties_assign(lhs, rhs):
    raise NotImplementedError("not called")


# signature: int blpapi_MessageProperties_copy(blpapi_MessageProperties_t **dest,const blpapi_MessageProperties_t *src);
def _blpapi_MessageProperties_copy(src):
    raise NotImplementedError("not called")


# signature: int blpapi_MessageProperties_create(blpapi_MessageProperties_t **messageProperties);
def _blpapi_MessageProperties_create():
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_MessageProperties_create(outp)  # int
    return retCode, getHandleFromOutput(outp, retCode)


# signature: void blpapi_MessageProperties_destroy(blpapi_MessageProperties_t *messageProperties);
def _blpapi_MessageProperties_destroy(messageProperties):
    l_blpapi_MessageProperties_destroy(messageProperties)


# signature: int blpapi_MessageProperties_setCorrelationIds(blpapi_MessageProperties_t *messageProperties,const blpapi_CorrelationId_t *correlationIds,size_t numCorrelationIds);
def _blpapi_MessageProperties_setCorrelationIds(
    messageProperties, correlationIds
):
    szcids = len(correlationIds)
    if szcids > 1:
        arraytype = CidStruct * szcids
        ptrs = arraytype(*[c.thestruct for c in correlationIds])
        oneptr = byref(ptrs)
    elif szcids == 1:
        oneptr = byref(correlationIds[0].thestruct)
    else:
        oneptr = c_void_p()  # pass null, the C SDK will check and reject

    return l_blpapi_MessageProperties_setCorrelationIds(
        messageProperties, oneptr, c_size_t(szcids)
    )


# signature: int blpapi_MessageProperties_setRecapType(blpapi_MessageProperties_t *messageProperties,int recap,int fragment);
def _blpapi_MessageProperties_setRecapType(messageProperties, recap, fragment):
    return l_blpapi_MessageProperties_setRecapType(
        messageProperties, recap, fragment
    )


# signature: int blpapi_MessageProperties_setRequestId(blpapi_MessageProperties_t *messageProperties, const char *requestId);
def _blpapi_MessageProperties_setRequestId(messageProperties, requestId):
    return l_blpapi_MessageProperties_setRequestId(
        messageProperties, charPtrFromPyStr(requestId)
    )


# signature: int blpapi_MessageProperties_setService(blpapi_MessageProperties_t *messageProperties,const blpapi_Service_t *service);
def _blpapi_MessageProperties_setService(messageProperties, service):
    return l_blpapi_MessageProperties_setService(messageProperties, service)


# signature: int blpapi_MessageProperties_setTimeReceived(blpapi_MessageProperties_t *messageProperties,const blpapi_HighPrecisionDatetime_t *timestamp);
def _blpapi_MessageProperties_setTimeReceived(messageProperties, timestamp):
    return l_blpapi_MessageProperties_setTimeReceived(
        messageProperties, byref(timestamp)
    )


# signature: int blpapi_Message_addRef(const blpapi_Message_t *message);
def _blpapi_Message_addRef(message):
    return l_blpapi_Message_addRef(message)


# signature: blpapi_CorrelationId_t blpapi_Message_correlationId(const blpapi_Message_t *message, size_t index);
def _blpapi_Message_correlationId(message, index):
    # C does return ABIUtil::ptr(message)->correlationId(index).impl();
    # i.e., we need to bump the ref. -- the caller will wrap this in CorrelationId
    cid = l_blpapi_Message_correlationId(message, c_size_t(index))
    return cid


# signature: blpapi_Element_t *blpapi_Message_elements(const blpapi_Message_t *message);
def _blpapi_Message_elements(message):
    return getHandleFromPtr(l_blpapi_Message_elements(message))


# signature: int blpapi_Message_fragmentType(const blpapi_Message_t *message);
def _blpapi_Message_fragmentType(message):
    return l_blpapi_Message_fragmentType(message)


# signature: int blpapi_Message_getRequestId(const blpapi_Message_t *message, const char **requestId);
def _blpapi_Message_getRequestId(message):
    out = c_char_p()
    outp = pointer(out)
    retCode = l_blpapi_Message_getRequestId(message, outp)  # int
    return retCode, getStrFromOutput(outp, retCode)


# signature: blpapi_Name_t *blpapi_Message_messageType(const blpapi_Message_t *message);
def _blpapi_Message_messageType(message):
    return getHandleFromPtr(l_blpapi_Message_messageType(message))


# signature: int blpapi_Message_numCorrelationIds(const blpapi_Message_t *message);
def _blpapi_Message_numCorrelationIds(message):
    return l_blpapi_Message_numCorrelationIds(message)


# signature:
def _blpapi_Message_printHelper(message, level, spacesPerLevel):
    return any_printer(message, l_blpapi_Message_print, level, spacesPerLevel)


# signature: int blpapi_Message_recapType(const blpapi_Message_t *message);
def _blpapi_Message_recapType(message):
    return l_blpapi_Message_recapType(message)


# signature: int blpapi_Message_release(const blpapi_Message_t *message);
def _blpapi_Message_release(message):
    return l_blpapi_Message_release(message)


# signature: blpapi_Service_t *blpapi_Message_service(const blpapi_Message_t *message);
def _blpapi_Message_service(message):
    service = l_blpapi_Message_service(message)
    return getHandleFromPtr(service)


# signature: int blpapi_Message_timeReceived(const blpapi_Message_t *message, blpapi_TimePoint_t *timeReceived);
def _blpapi_Message_timeReceived(message):
    out = TimePoint()
    outp = pointer(out)
    retCode = l_blpapi_Message_timeReceived(message, outp)
    return retCode, getStructFromOutput(outp, retCode)


# signature: const char *blpapi_Message_topicName(const blpapi_Message_t *message);
def _blpapi_Message_topicName(message):  # pylint: disable=unused-argument
    return ""  # that is what C does


# signature: blpapi_Name_t *blpapi_Name_create(const char *nameString);
def _blpapi_Name_create(nameString):
    return getHandleFromPtr(l_blpapi_Name_create(charPtrFromPyStr(nameString)))


# signature: void blpapi_Name_destroy(blpapi_Name_t *name);
def _blpapi_Name_destroy(name):
    l_blpapi_Name_destroy(name)


# signature: int blpapi_Name_equalsStr(const blpapi_Name_t *name, const char *string);
def _blpapi_Name_equalsStr(name, string):
    return l_blpapi_Name_equalsStr(name, charPtrFromPyStr(string))


# signature: blpapi_Name_t *blpapi_Name_findName(const char *nameString);
def _blpapi_Name_findName(nameString):
    return getHandleFromPtr(
        l_blpapi_Name_findName(charPtrFromPyStr(nameString))
    )


# signature:
def _blpapi_Name_hasName(nameString):
    handle = _blpapi_Name_findName(nameString)
    return 0 if handle is None else 1


# signature: size_t blpapi_Name_length(const blpapi_Name_t *name);
def _blpapi_Name_length(name):
    return l_blpapi_Name_length(name)


# signature: const char *blpapi_Name_string(const blpapi_Name_t *name);
def _blpapi_Name_string(name):
    # C does not check the pointer, simply reinterpret_casts it
    # c_void_p().value and c_void_p(0).value are None
    if name is None or name.value is None:
        return None
    return getStrFromC(l_blpapi_Name_string(name))


# signature: const char *blpapi_Operation_description(blpapi_Operation_t *operation);
def _blpapi_Operation_description(operation):
    # tests assume empty string
    return getStrFromC(l_blpapi_Operation_description(operation), "")


# signature: const char *blpapi_Operation_name(blpapi_Operation_t *operation);
def _blpapi_Operation_name(operation):
    return getStrFromC(l_blpapi_Operation_name(operation))


# signature: int blpapi_Operation_numResponseDefinitions(blpapi_Operation_t *operation);
def _blpapi_Operation_numResponseDefinitions(operation):
    return l_blpapi_Operation_numResponseDefinitions(operation)


# signature: int blpapi_Operation_requestDefinition(blpapi_Operation_t *operation,blpapi_SchemaElementDefinition_t **requestDefinition);
def _blpapi_Operation_requestDefinition(operation):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Operation_requestDefinition(operation, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Operation_responseDefinition(blpapi_Operation_t *operation,blpapi_SchemaElementDefinition_t **responseDefinition,size_t index);
def _blpapi_Operation_responseDefinition(operation, index):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Operation_responseDefinition(
        operation, outp, c_size_t(index)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Operation_responseDefinitionFromName(blpapi_Operation_t *operation,blpapi_SchemaElementDefinition_t **responseDefinition,const blpapi_Name_t *name);
def _blpapi_Operation_responseDefinitionFromName(operation, name):
    raise NotImplementedError("not called")


# signature: int blpapi_ProviderSession_activateSubServiceCodeRange(blpapi_ProviderSession_t *session,const char *serviceName,int begin,int end,int priority);
def _blpapi_ProviderSession_activateSubServiceCodeRange(
    session, serviceName, begin, end, priority
):
    return l_blpapi_ProviderSession_activateSubServiceCodeRange(
        session, charPtrFromPyStr(serviceName), begin, end, priority
    )


# signature: int blpapi_ProviderSession_createServiceStatusTopic(blpapi_ProviderSession_t *session,const blpapi_Service_t *service,blpapi_Topic_t **topic);
def _blpapi_ProviderSession_createServiceStatusTopic(session, service):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_ProviderSession_createServiceStatusTopic(
        session, service, outp
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_ProviderSession_createTopics(blpapi_ProviderSession_t *session,blpapi_TopicList_t *topicList,int resolveMode,const blpapi_Identity_t *identity);
def _blpapi_ProviderSession_createTopic(session, message):
    raise NotImplementedError("not called")


# signature: int blpapi_ProviderSession_createTopics(blpapi_ProviderSession_t *session,blpapi_TopicList_t *topicList,int resolveMode,const blpapi_Identity_t *identity);
def _blpapi_ProviderSession_createTopics(
    session, topicList, resolveMode, identity
):
    return l_blpapi_ProviderSession_createTopics(
        session, topicList, c_int(resolveMode), identity
    )


# signature: int blpapi_ProviderSession_createTopicsAsync(blpapi_ProviderSession_t *session,const blpapi_TopicList_t *topicList,int resolveMode,const blpapi_Identity_t *identity);
def _blpapi_ProviderSession_createTopicsAsync(
    session, topicList, resolveMode, identity
):
    return l_blpapi_ProviderSession_createTopicsAsync(
        session, topicList, c_int(resolveMode), identity
    )


# signature: int blpapi_ProviderSession_deactivateSubServiceCodeRange(blpapi_ProviderSession_t *session,const char *serviceName,int begin,int end);
def _blpapi_ProviderSession_deactivateSubServiceCodeRange(
    session, serviceName, begin, end
):
    return l_blpapi_ProviderSession_deactivateSubServiceCodeRange(
        session, charPtrFromPyStr(serviceName), begin, end
    )


# signature: int blpapi_ProviderSession_deleteTopics(blpapi_ProviderSession_t *session,const blpapi_Topic_t **topics,size_t numTopics);
def _blpapi_ProviderSession_deleteTopics(session, topics):
    # topics is a python list of handles by now
    sz = len(topics)
    arraytpe = c_void_p * sz
    topicsp = arraytpe(*topics)
    return l_blpapi_ProviderSession_deleteTopics(
        session, topicsp, c_size_t(sz)
    )


# signature: int blpapi_ProviderSession_deregisterService(blpapi_ProviderSession_t *session, const char *serviceName);
def _blpapi_ProviderSession_deregisterService(session, serviceName):
    return l_blpapi_ProviderSession_deregisterService(
        session, charPtrFromPyStr(serviceName)
    )


# signature: int blpapi_ProviderSession_flushPublishedEvents(blpapi_ProviderSession_t *session, int *allFlushed, int timeoutMsecs);
def _blpapi_ProviderSession_flushPublishedEvents(session, timeoutMsecs):
    out = c_int()
    outp = pointer(out)
    retCode = l_blpapi_ProviderSession_flushPublishedEvents(
        session, outp, timeoutMsecs
    )
    return retCode, getPODFromOutput(outp, retCode)


# signature: blpapi_AbstractSession_t *blpapi_ProviderSession_getAbstractSession(blpapi_ProviderSession_t *session);
def _blpapi_ProviderSession_getAbstractSession(session):
    return getHandleFromPtr(
        l_blpapi_ProviderSession_getAbstractSession(session)
    )


# signature: int blpapi_ProviderSession_getTopic(blpapi_ProviderSession_t *session,const blpapi_Message_t *message,blpapi_Topic_t **topic);
def _blpapi_ProviderSession_getTopic(session, message):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_ProviderSession_getTopic(session, message, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_ProviderSession_nextEvent(blpapi_ProviderSession_t *session,blpapi_Event_t **eventPointer,unsigned int timeoutInMilliseconds);
def _blpapi_ProviderSession_nextEvent(session, timeoutInMilliseconds):
    eventptr = c_void_p()
    outp = pointer(eventptr)
    retCode = l_blpapi_ProviderSession_nextEvent(
        session, outp, c_uint(timeoutInMilliseconds)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_ProviderSession_publish(blpapi_ProviderSession_t *session, blpapi_Event_t *event);
def _blpapi_ProviderSession_publish(session, event):
    return l_blpapi_ProviderSession_publish(session, event)


# signature: int blpapi_ProviderSession_registerService(blpapi_ProviderSession_t *session,const char *serviceName,const blpapi_Identity_t *identity,blpapi_ServiceRegistrationOptions_t *registrationOptions);
def _blpapi_ProviderSession_registerService(
    session, serviceName, identity, registrationOptions
):
    return l_blpapi_ProviderSession_registerService(
        session, charPtrFromPyStr(serviceName), identity, registrationOptions
    )


# signature: int blpapi_ProviderSession_registerServiceAsync(blpapi_ProviderSession_t *session,const char *serviceName,const blpapi_Identity_t *identity,blpapi_CorrelationId_t *correlationId,blpapi_ServiceRegistrationOptions_t *registrationOptions);
def _blpapi_ProviderSession_registerServiceAsync(
    session, serviceName, identity, correlationId, registrationOptions
):
    # the C layer will OVERWRITE cid with autogen for unset
    cidp = pointer(correlationId.thestruct)

    return l_blpapi_ProviderSession_registerServiceAsync(
        session,
        charPtrFromPyStr(serviceName),
        identity,
        cidp,
        registrationOptions,
    )


# signature: int blpapi_ProviderSession_resolve(blpapi_ProviderSession_t *session,blpapi_ResolutionList_t *resolutionList,int resolveMode,const blpapi_Identity_t *identity);
def _blpapi_ProviderSession_resolve(
    session, resolutionList, resolveMode, identity
):
    return l_blpapi_ProviderSession_resolve(
        session, resolutionList, c_int(resolveMode), identity
    )


# signature: int blpapi_ProviderSession_resolveAsync(blpapi_ProviderSession_t *session,const blpapi_ResolutionList_t *resolutionList,int resolveMode,const blpapi_Identity_t *identity);
def _blpapi_ProviderSession_resolveAsync(
    session, resolutionList, resolveMode, identity
):
    return l_blpapi_ProviderSession_resolveAsync(
        session, resolutionList, c_int(resolveMode), identity
    )


# signature: int blpapi_ProviderSession_sendResponse(blpapi_ProviderSession_t *session,blpapi_Event_t *event,int isPartialResponse);
def _blpapi_ProviderSession_sendResponse(session, event, isPartialResponse):
    return l_blpapi_ProviderSession_sendResponse(
        session, event, c_int(isPartialResponse)
    )


# signature: int blpapi_ProviderSession_start(blpapi_ProviderSession_t *session);
def _blpapi_ProviderSession_start(session):
    return l_blpapi_ProviderSession_start(session)


# signature: int blpapi_ProviderSession_startAsync(blpapi_ProviderSession_t *session);
def _blpapi_ProviderSession_startAsync(session):
    return l_blpapi_ProviderSession_startAsync(session)


# signature: int blpapi_ProviderSession_stop(blpapi_ProviderSession_t *session);
def _blpapi_ProviderSession_stop(session):
    return l_blpapi_ProviderSession_stop(session)


# signature: int blpapi_ProviderSession_stopAsync(blpapi_ProviderSession_t *session);
def _blpapi_ProviderSession_stopAsync(session):
    return l_blpapi_ProviderSession_stopAsync(session)


def _blpapi_ProviderSession_terminateSubscriptionsOnTopic(
    session, topic, message
):
    return _blpapi_ProviderSession_terminateSubscriptionsOnTopics(
        session, [topic], message
    )


# signature: int blpapi_ProviderSession_terminateSubscriptionsOnTopics(blpapi_ProviderSession_t *session,const blpapi_Topic_t **topics,size_t numTopics,const char *message);
def _blpapi_ProviderSession_terminateSubscriptionsOnTopics(
    session, topics, message
):
    # we put handles in providersession inside topics
    sz = len(topics)
    arraytype = c_void_p * sz
    topicsp = arraytype(*topics)
    return l_blpapi_ProviderSession_terminateSubscriptionsOnTopics(
        session, topicsp, c_size_t(sz), charPtrFromPyStr(message)
    )


# signature: int blpapi_ProviderSession_tryNextEvent(blpapi_ProviderSession_t *session, blpapi_Event_t **eventPointer);
def _blpapi_ProviderSession_tryNextEvent(session):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_ProviderSession_tryNextEvent(session, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_RequestTemplate_release(const blpapi_RequestTemplate_t *requestTemplate);
def _blpapi_RequestTemplate_release(requestTemplate):
    return l_blpapi_RequestTemplate_release(requestTemplate)


# signature: void blpapi_Request_destroy(blpapi_Request_t *request);
def _blpapi_Request_destroy(request):
    l_blpapi_Request_destroy(request)


# signature: blpapi_Element_t *blpapi_Request_elements(blpapi_Request_t *request);
def _blpapi_Request_elements(request):
    return getHandleFromPtr(l_blpapi_Request_elements(request))


# signature: int blpapi_Request_getRequestId(const blpapi_Request_t *request, const char **requestId);
def _blpapi_Request_getRequestId(request):
    out = c_char_p()
    outp = pointer(out)
    retCode = l_blpapi_Request_getRequestId(request, outp)
    if retCode != 0:
        return retCode, None
    return (retCode, getStrFromOutput(outp, retCode))


# signature: void blpapi_Request_setPreferredRoute(blpapi_Request_t *request, blpapi_CorrelationId_t *correlationId);
def _blpapi_Request_setPreferredRoute(request, correlationId):
    raise NotImplementedError("not called")


# signature: int blpapi_ResolutionList_add(blpapi_ResolutionList_t *list,const char *topic,const blpapi_CorrelationId_t *correlationId);
def _blpapi_ResolutionList_add(resolution_list, topic, correlationId):
    return l_blpapi_ResolutionList_add(
        resolution_list,
        charPtrFromPyStr(topic),
        byref(correlationId.thestruct),
    )


# signature: int blpapi_ResolutionList_addAttribute(blpapi_ResolutionList_t *list, const blpapi_Name_t *name);
def _blpapi_ResolutionList_addAttribute(resolution_list, name):
    return l_blpapi_ResolutionList_addAttribute(resolution_list, name)


# signature: int blpapi_ResolutionList_addFromMessage(blpapi_ResolutionList_t *list,const blpapi_Message_t *topic,const blpapi_CorrelationId_t *correlationId);
def _blpapi_ResolutionList_addFromMessage(resolution_list, topic, cid):
    return l_blpapi_ResolutionList_addFromMessage(
        resolution_list,
        topic,
        byref(cid.thestruct),
    )


# signature: int blpapi_ResolutionList_attribute(const blpapi_ResolutionList_t *list,blpapi_Element_t **element,const blpapi_Name_t *attribute,const blpapi_CorrelationId_t *id);
def _blpapi_ResolutionList_attribute(resolution_list, attribute, cid):
    out = c_void_p()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_attribute(
        resolution_list,
        outp,
        attribute,
        byref(cid.thestruct),
    )

    return rc, getHandleFromOutput(outp, rc)


# signature: int blpapi_ResolutionList_attributeAt(const blpapi_ResolutionList_t *list,blpapi_Element_t **element,const blpapi_Name_t *attribute,size_t index);
def _blpapi_ResolutionList_attributeAt(resolution_list, attribute, index):
    out = c_void_p()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_attributeAt(
        resolution_list, outp, attribute, c_size_t(index)
    )

    return rc, getHandleFromOutput(outp, rc)


# signature: int blpapi_ResolutionList_correlationIdAt(const blpapi_ResolutionList_t *list,blpapi_CorrelationId_t *result,size_t index);
def _blpapi_ResolutionList_correlationIdAt(resolution_list, index):
    cid = CidStruct()
    cid_p = pointer(cid)
    rc = l_blpapi_ResolutionList_correlationIdAt(
        resolution_list, cid_p, c_size_t(index)
    )
    if rc == 0:
        # C will do: *result = rlImpl->correlationId(index).impl(),
        # i.e., we need to bump the reference
        # the caller will wrap this in CorrelationId
        return rc, cid
    return rc, None


# signature: blpapi_ResolutionList_t *blpapi_ResolutionList_create(blpapi_ResolutionList_t *from);
def _blpapi_ResolutionList_create(_from):
    from_p = c_void_p() if _from is None else _from
    return getHandleFromPtr(l_blpapi_ResolutionList_create(from_p))


# signature: void blpapi_ResolutionList_destroy(blpapi_ResolutionList_t *list);
def _blpapi_ResolutionList_destroy(resolution_list):
    l_blpapi_ResolutionList_destroy(resolution_list)


# signature: blpapi_Element_t *blpapi_ResolutionList_extractAttributeFromResolutionSuccess(const blpapi_Message_t *message, const blpapi_Name_t *attribute);
def _blpapi_ResolutionList_extractAttributeFromResolutionSuccess(
    message, attribute
):
    raise DeprecationWarning()


# signature: int blpapi_ResolutionList_message(const blpapi_ResolutionList_t *list,blpapi_Message_t **element,const blpapi_CorrelationId_t *id);
def _blpapi_ResolutionList_message(resolution_list, cid):
    out = c_void_p()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_message(
        resolution_list, outp, byref(cid.thestruct)
    )
    return rc, getHandleFromOutput(outp, rc)


# signature: int blpapi_ResolutionList_messageAt(const blpapi_ResolutionList_t *list,blpapi_Message_t **element,size_t index);
def _blpapi_ResolutionList_messageAt(resolution_list, index):
    out = c_void_p()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_messageAt(
        resolution_list, outp, c_size_t(index)
    )
    return rc, getHandleFromOutput(outp, rc)


# signature: int blpapi_ResolutionList_size(const blpapi_ResolutionList_t *list);
def _blpapi_ResolutionList_size(resolution_list):
    return l_blpapi_ResolutionList_size(resolution_list)


# signature: int blpapi_ResolutionList_status(const blpapi_ResolutionList_t *list,int *status,const blpapi_CorrelationId_t *id);
def _blpapi_ResolutionList_status(resolution_list, cid):
    out = c_int()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_status(
        resolution_list, outp, byref(cid.thestruct)
    )

    return rc, getPODFromOutput(outp, rc)


# signature: int blpapi_ResolutionList_statusAt(const blpapi_ResolutionList_t *list, int *status, size_t index);
def _blpapi_ResolutionList_statusAt(resolution_list, index):
    out = c_int()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_statusAt(resolution_list, outp, index)

    return rc, out.value


# signature: int blpapi_ResolutionList_topicString(const blpapi_ResolutionList_t *list,const char **topic,const blpapi_CorrelationId_t *id);
def _blpapi_ResolutionList_topicString(resolution_list, cid):
    out = c_char_p()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_topicString(
        resolution_list, outp, byref(cid.thestruct)
    )
    return rc, getStrFromOutput(outp, rc)


# signature: int blpapi_ResolutionList_topicStringAt(const blpapi_ResolutionList_t *list, const char **topic, size_t index);
def _blpapi_ResolutionList_topicStringAt(resolution_list, index):
    out = c_char_p()
    outp = pointer(out)
    rc = l_blpapi_ResolutionList_topicStringAt(resolution_list, outp, index)
    return rc, getStrFromOutput(outp, rc)


# signature: const char *blpapi_SchemaElementDefinition_description(const blpapi_SchemaElementDefinition_t *field);
def _blpapi_SchemaElementDefinition_description(field):
    ds = l_blpapi_SchemaElementDefinition_description(field)
    return getStrFromC(ds)


# signature: blpapi_Name_t *blpapi_SchemaElementDefinition_getAlternateName(const blpapi_SchemaElementDefinition_t *field, size_t index);
def _blpapi_SchemaElementDefinition_getAlternateName(field, index):
    return getHandleFromPtr(
        l_blpapi_SchemaElementDefinition_getAlternateName(
            field, c_size_t(index)
        )
    )


# signature: size_t blpapi_SchemaElementDefinition_maxValues(const blpapi_SchemaElementDefinition_t *field);
def _blpapi_SchemaElementDefinition_maxValues(field):
    return l_blpapi_SchemaElementDefinition_maxValues(field)


# signature: size_t blpapi_SchemaElementDefinition_minValues(const blpapi_SchemaElementDefinition_t *field);
def _blpapi_SchemaElementDefinition_minValues(field):
    return l_blpapi_SchemaElementDefinition_minValues(field)


# signature: blpapi_Name_t *blpapi_SchemaElementDefinition_name(const blpapi_SchemaElementDefinition_t *field);
def _blpapi_SchemaElementDefinition_name(field):
    return getHandleFromPtr(l_blpapi_SchemaElementDefinition_name(field))


# signature: size_t blpapi_SchemaElementDefinition_numAlternateNames(const blpapi_SchemaElementDefinition_t *field);
def _blpapi_SchemaElementDefinition_numAlternateNames(field):
    return l_blpapi_SchemaElementDefinition_numAlternateNames(field)


# signature:
def _blpapi_SchemaElementDefinition_printHelper(item, level, spacesPerLevel):
    return any_printer(
        item, l_blpapi_SchemaElementDefinition_print, level, spacesPerLevel
    )


# signature: int blpapi_SchemaElementDefinition_status(const blpapi_SchemaElementDefinition_t *field);
def _blpapi_SchemaElementDefinition_status(field):
    return l_blpapi_SchemaElementDefinition_status(field)


# signature: blpapi_SchemaTypeDefinition_t *blpapi_SchemaElementDefinition_type(const blpapi_SchemaElementDefinition_t *field);
def _blpapi_SchemaElementDefinition_type(field):
    return getHandleFromPtr(l_blpapi_SchemaElementDefinition_type(field))


# signature: int blpapi_SchemaTypeDefinition_datatype(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_datatype(stype):
    return l_blpapi_SchemaTypeDefinition_datatype(stype)


# signature: const char *blpapi_SchemaTypeDefinition_description(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_description(stype):
    ds = l_blpapi_SchemaTypeDefinition_description(stype)
    return getStrFromC(ds)


# signature: blpapi_ConstantList_t *blpapi_SchemaTypeDefinition_enumeration(const blpapi_SchemaTypeDefinition_t *element);
def _blpapi_SchemaTypeDefinition_enumeration(element):
    return getHandleFromPtr(l_blpapi_SchemaTypeDefinition_enumeration(element))


# signature: blpapi_SchemaTypeDefinition_getElementDefinition(const blpapi_SchemaTypeDefinition_t *type,const char *nameString,const blpapi_Name_t *name);
def _blpapi_SchemaTypeDefinition_getElementDefinition(stype, nameString, name):
    return getHandleFromPtr(
        l_blpapi_SchemaTypeDefinition_getElementDefinition(
            stype, charPtrFromPyStr(nameString), name
        )
    )


# signature: blpapi_SchemaTypeDefinition_getElementDefinitionAt(const blpapi_SchemaTypeDefinition_t *type, size_t index);
def _blpapi_SchemaTypeDefinition_getElementDefinitionAt(stype, index):
    return getHandleFromPtr(
        l_blpapi_SchemaTypeDefinition_getElementDefinitionAt(
            stype, c_size_t(index)
        )
    )


# signature:
def _blpapi_SchemaTypeDefinition_hasElementDefinition(stype, nameString, name):
    return l_blpapi_SchemaTypeDefinition_getElementDefinition(
        stype, charPtrFromPyStr(nameString), name
    )


# signature: int blpapi_SchemaTypeDefinition_isComplexType(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_isComplexType(stype):
    return l_blpapi_SchemaTypeDefinition_isComplexType(stype)


# signature: int blpapi_SchemaTypeDefinition_isEnumerationType(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_isEnumerationType(stype):
    return l_blpapi_SchemaTypeDefinition_isEnumerationType(stype)


# signature: int blpapi_SchemaTypeDefinition_isSimpleType(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_isSimpleType(stype):
    return l_blpapi_SchemaTypeDefinition_isSimpleType(stype)


# signature: blpapi_Name_t *blpapi_SchemaTypeDefinition_name(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_name(stype):
    return getHandleFromPtr(l_blpapi_SchemaTypeDefinition_name(stype))


# signature: size_t blpapi_SchemaTypeDefinition_numElementDefinitions(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_numElementDefinitions(stype):
    return l_blpapi_SchemaTypeDefinition_numElementDefinitions(stype)


# signature:
def _blpapi_SchemaTypeDefinition_printHelper(item, level, spacesPerLevel):
    return any_printer(
        item, l_blpapi_SchemaTypeDefinition_print, level, spacesPerLevel
    )


# signature: int blpapi_SchemaTypeDefinition_status(const blpapi_SchemaTypeDefinition_t *type);
def _blpapi_SchemaTypeDefinition_status(stype):
    return l_blpapi_SchemaTypeDefinition_status(stype)


# signature: int blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange(blpapi_ServiceRegistrationOptions_t *parameters,int start,int end,int priority);
def _blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange(
    parameters, start, end, priority
):
    return l_blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange(
        parameters, start, end, priority
    )  # all ints


# signature: void blpapi_ServiceRegistrationOptions_copy(blpapi_ServiceRegistrationOptions_t *lhs,const blpapi_ServiceRegistrationOptions_t *rhs);
def _blpapi_ServiceRegistrationOptions_copy(lhs, rhs):
    raise NotImplementedError("not called")


# signature: blpapi_ServiceRegistrationOptions_t *blpapi_ServiceRegistrationOptions_create(void);
def _blpapi_ServiceRegistrationOptions_create():
    return getHandleFromPtr(l_blpapi_ServiceRegistrationOptions_create())


# signature: void blpapi_ServiceRegistrationOptions_destroy(blpapi_ServiceRegistrationOptions_t *parameters);
def _blpapi_ServiceRegistrationOptions_destroy(parameters):
    l_blpapi_ServiceRegistrationOptions_destroy(parameters)


# signature: blpapi_ServiceRegistrationOptions_duplicate(const blpapi_ServiceRegistrationOptions_t *parameters);
def _blpapi_ServiceRegistrationOptions_duplicate(parameters):
    raise NotImplementedError("not called")


BLPAPI_MAX_GROUP_ID_SIZE = 64


# signature: int blpapi_ServiceRegistrationOptions_getGroupId(blpapi_ServiceRegistrationOptions_t *parameters,char *groupdIdBuffer,int *groupIdLength);
def _blpapi_ServiceRegistrationOptions_getGroupId(parameters):
    outp = create_string_buffer(BLPAPI_MAX_GROUP_ID_SIZE)
    sz = c_int()
    szp = pointer(sz)
    retCode = l_blpapi_ServiceRegistrationOptions_getGroupId(
        parameters, outp, szp
    )
    if retCode != 0:
        return None
    return retCode, getSizedStrFromBuffer(outp, sz.value)


# signature: int blpapi_ServiceRegistrationOptions_getPartsToRegister(blpapi_ServiceRegistrationOptions_t *parameters);
def _blpapi_ServiceRegistrationOptions_getPartsToRegister(parameters):
    return l_blpapi_ServiceRegistrationOptions_getPartsToRegister(parameters)


# signature: int blpapi_ServiceRegistrationOptions_getServicePriority(blpapi_ServiceRegistrationOptions_t *parameters);
def _blpapi_ServiceRegistrationOptions_getServicePriority(parameters):
    return l_blpapi_ServiceRegistrationOptions_getServicePriority(parameters)


# signature: void blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges(blpapi_ServiceRegistrationOptions_t *parameters);
def _blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges(
    parameters,
):
    l_blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges(
        parameters
    )


# signature: void blpapi_ServiceRegistrationOptions_setGroupId(blpapi_ServiceRegistrationOptions_t *parameters,const char *groupId,unsigned int groupIdLength);
def _blpapi_ServiceRegistrationOptions_setGroupId(parameters, groupId):
    gid, sz = charPtrWithSizeFromPyStr(groupId)
    l_blpapi_ServiceRegistrationOptions_setGroupId(parameters, gid, c_uint(sz))


# signature: void blpapi_ServiceRegistrationOptions_setPartsToRegister(blpapi_ServiceRegistrationOptions_t *parameters, int parts);
def _blpapi_ServiceRegistrationOptions_setPartsToRegister(parameters, parts):
    l_blpapi_ServiceRegistrationOptions_setPartsToRegister(parameters, parts)


# signature: int blpapi_ServiceRegistrationOptions_setServicePriority(blpapi_ServiceRegistrationOptions_t *parameters, int priority);
def _blpapi_ServiceRegistrationOptions_setServicePriority(
    parameters, priority
):
    return l_blpapi_ServiceRegistrationOptions_setServicePriority(
        parameters, priority
    )


# signature: int blpapi_Service_addRef(blpapi_Service_t *service);
def _blpapi_Service_addRef(service):
    return l_blpapi_Service_addRef(service)


# signature: const char *blpapi_Service_authorizationServiceName(blpapi_Service_t *service);
def _blpapi_Service_authorizationServiceName(service):
    return getStrFromC(l_blpapi_Service_authorizationServiceName(service))


# signature: int blpapi_Service_createAdminEvent(blpapi_Service_t *service, blpapi_Event_t **event);
def _blpapi_Service_createAdminEvent(service):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_createAdminEvent(service, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Service_createAuthorizationRequest(blpapi_Service_t *service,blpapi_Request_t **request,const char *operation);
def _blpapi_Service_createAuthorizationRequest(service, operation):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_createAuthorizationRequest(
        service, outp, charPtrFromPyStr(operation)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Service_createPublishEvent(blpapi_Service_t *service, blpapi_Event_t **event);
def _blpapi_Service_createPublishEvent(service):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_createPublishEvent(service, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Service_createRequest(blpapi_Service_t *service,blpapi_Request_t **request,const char *operation);
def _blpapi_Service_createRequest(service, operation):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_createRequest(
        service, outp, charPtrFromPyStr(operation)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Service_createResponseEvent(blpapi_Service_t *service,const blpapi_CorrelationId_t *correlationId,blpapi_Event_t **event);
def _blpapi_Service_createResponseEvent(service, correlationId):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_createResponseEvent(
        service, byref(correlationId.thestruct), outp
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: const char *blpapi_Service_description(blpapi_Service_t *service);
def _blpapi_Service_description(service):
    return getStrFromC(l_blpapi_Service_description(service))


# signature: int blpapi_Service_getEventDefinition(blpapi_Service_t *service,blpapi_SchemaElementDefinition_t **result,const char *nameString,const blpapi_Name_t *name);
def _blpapi_Service_getEventDefinition(service, nameString, name):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_getEventDefinition(
        service, outp, charPtrFromPyStr(nameString), name
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Service_getEventDefinitionAt(blpapi_Service_t *service,blpapi_SchemaElementDefinition_t **result,size_t index);
def _blpapi_Service_getEventDefinitionAt(service, index):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_getEventDefinitionAt(
        service, outp, c_size_t(index)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Service_getOperation(blpapi_Service_t *service,blpapi_Operation_t **operation,const char *nameString,const blpapi_Name_t *name);
def _blpapi_Service_getOperation(service, nameString, name):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_getOperation(
        service, outp, charPtrFromPyStr(nameString), name
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Service_getOperationAt(blpapi_Service_t *service,blpapi_Operation_t **operation,size_t index);
def _blpapi_Service_getOperationAt(service, index):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_Service_getOperationAt(service, outp, index)
    return retCode, getHandleFromOutput(outp, retCode)


# signature:
def _blpapi_Service_hasEventDefinition(service, nameString, name):
    return (
        0 == _blpapi_Service_getEventDefinition(service, nameString, name)[0]
    )


# signature:
def _blpapi_Service_hasOperation(service, nameString, name):
    return 0 == _blpapi_Service_getOperation(service, nameString, name)[0]


# signature: const char *blpapi_Service_name(blpapi_Service_t *service);
def _blpapi_Service_name(service):
    return getStrFromC(l_blpapi_Service_name(service))


# signature: int blpapi_Service_numEventDefinitions(blpapi_Service_t *service);
def _blpapi_Service_numEventDefinitions(service):
    return l_blpapi_Service_numEventDefinitions(service)


# signature: int blpapi_Service_numOperations(blpapi_Service_t *service);
def _blpapi_Service_numOperations(service):
    return l_blpapi_Service_numOperations(service)


# signature:
def _blpapi_Service_printHelper(service, level, spacesPerLevel):
    return any_printer(service, l_blpapi_Service_print, level, spacesPerLevel)


# signature: void blpapi_Service_release(blpapi_Service_t *service);
def _blpapi_Service_release(service):
    l_blpapi_Service_release(service)


# signature: int blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg(parameters):
    return l_blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg(parameters)


# signature: int blpapi_SessionOptions_applicationIdentityKey(const char **applicationIdentityKey,size_t *size,blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_applicationIdentityKey(parameters):
    out = c_char_p()
    outp = pointer(out)
    szout = c_size_t()
    szoutp = pointer(szout)
    retCode = l_blpapi_SessionOptions_applicationIdentityKey(
        outp, szoutp, parameters
    )
    return retCode, getSizedStrFromOutput(outp, szoutp, retCode)


# signature: const char *blpapi_SessionOptions_authenticationOptions(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_authenticationOptions(parameters):
    return getStrFromC(
        l_blpapi_SessionOptions_authenticationOptions(parameters)
    )


# signature: int blpapi_SessionOptions_autoRestartOnDisconnection(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_autoRestartOnDisconnection(parameters):
    return l_blpapi_SessionOptions_autoRestartOnDisconnection(parameters)


# signature: int blpapi_SessionOptions_bandwidthSaveModeDisabled(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_bandwidthSaveModeDisabled(parameters):
    return l_blpapi_SessionOptions_bandwidthSaveModeDisabled(parameters)


# signature: int blpapi_SessionOptions_clientMode(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_clientMode(parameters):
    return l_blpapi_SessionOptions_clientMode(parameters)


# signature: unsigned int blpapi_SessionOptions_connectTimeout(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_connectTimeout(parameters):
    return l_blpapi_SessionOptions_connectTimeout(parameters)


# signature: blpapi_SessionOptions_t *blpapi_SessionOptions_create(void);
def _blpapi_SessionOptions_create():
    return getHandleFromPtr(l_blpapi_SessionOptions_create())


# signature: int blpapi_SessionOptions_defaultKeepAliveInactivityTime(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_defaultKeepAliveInactivityTime(parameters):
    return l_blpapi_SessionOptions_defaultKeepAliveInactivityTime(parameters)


# signature: int blpapi_SessionOptions_defaultKeepAliveResponseTimeout(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_defaultKeepAliveResponseTimeout(parameters):
    return l_blpapi_SessionOptions_defaultKeepAliveResponseTimeout(parameters)


# signature: const char *blpapi_SessionOptions_defaultServices(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_defaultServices(parameters):
    return getStrFromC(l_blpapi_SessionOptions_defaultServices(parameters))


# signature: const char *blpapi_SessionOptions_defaultSubscriptionService(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_defaultSubscriptionService(parameters):
    return getStrFromC(
        l_blpapi_SessionOptions_defaultSubscriptionService(parameters)
    )


# signature: const char *blpapi_SessionOptions_defaultTopicPrefix(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_defaultTopicPrefix(parameters):
    return getStrFromC(l_blpapi_SessionOptions_defaultTopicPrefix(parameters))


# signature: void blpapi_SessionOptions_destroy(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_destroy(parameters):
    l_blpapi_SessionOptions_destroy(parameters)


# signature: int blpapi_SessionOptions_flushPublishedEventsTimeout(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_flushPublishedEventsTimeout(parameters):
    return l_blpapi_SessionOptions_flushPublishedEventsTimeout(parameters)


# signature: int blpapi_SessionOptions_getServerAddressWithProxy(blpapi_SessionOptions_t *parameters,const char **serverHost,unsigned short *serverPort,const char **socks5Host,unsigned short *sock5Port,size_t index);
def _blpapi_SessionOptions_getServerAddressWithProxy(parameters, index):
    hostout = c_char_p()
    hostoutp = pointer(hostout)
    portout = c_uint16()
    portoutp = pointer(portout)
    s5hostout = c_char_p()
    s5hostoutp = pointer(s5hostout)
    s5portout = c_uint16()
    s5portoutp = pointer(s5portout)
    retCode = l_blpapi_SessionOptions_getServerAddressWithProxy(
        parameters, hostoutp, portoutp, s5hostoutp, s5portoutp, c_size_t(index)
    )
    return (
        retCode,
        getStrFromOutput(hostoutp, retCode),
        getPODFromOutput(portoutp, retCode),
        getStrFromOutput(s5hostoutp, retCode),
        getPODFromOutput(s5portoutp, retCode),
    )


# signature: int blpapi_SessionOptions_keepAliveEnabled(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_keepAliveEnabled(parameters):
    return l_blpapi_SessionOptions_keepAliveEnabled(parameters)


# signature: size_t blpapi_SessionOptions_maxEventQueueSize(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_maxEventQueueSize(parameters):
    return l_blpapi_SessionOptions_maxEventQueueSize(parameters)


# signature: int blpapi_SessionOptions_maxPendingRequests(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_maxPendingRequests(parameters):
    return l_blpapi_SessionOptions_maxPendingRequests(parameters)


# signature: int blpapi_SessionOptions_numServerAddresses(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_numServerAddresses(parameters):
    return l_blpapi_SessionOptions_numServerAddresses(parameters)


# signature: int blpapi_SessionOptions_numStartAttempts(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_numStartAttempts(parameters):
    return l_blpapi_SessionOptions_numStartAttempts(parameters)


# signature:
def _blpapi_SessionOptions_printHelper(sessionOptions, level, spacesPerLevel):
    return any_printer(
        sessionOptions, l_blpapi_SessionOptions_print, level, spacesPerLevel
    )


# signature: int blpapi_SessionOptions_recordSubscriptionDataReceiveTimes(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_recordSubscriptionDataReceiveTimes(parameters):
    return l_blpapi_SessionOptions_recordSubscriptionDataReceiveTimes(
        parameters
    )


# signature: int blpapi_SessionOptions_removeServerAddress(blpapi_SessionOptions_t *parameters, size_t index);
def _blpapi_SessionOptions_removeServerAddress(parameters, index):
    return l_blpapi_SessionOptions_removeServerAddress(
        parameters, c_size_t(index)
    )


# signature: const char *blpapi_SessionOptions_serverHost(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_serverHost(parameters):
    return getStrFromC(l_blpapi_SessionOptions_serverHost(parameters))


# signature: unsigned int blpapi_SessionOptions_serverPort(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_serverPort(parameters):
    return l_blpapi_SessionOptions_serverPort(parameters)


# signature: int blpapi_SessionOptions_serviceCheckTimeout(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_serviceCheckTimeout(parameters):
    return l_blpapi_SessionOptions_serviceCheckTimeout(parameters)


# signature: int blpapi_SessionOptions_serviceDownloadTimeout(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_serviceDownloadTimeout(parameters):
    return l_blpapi_SessionOptions_serviceDownloadTimeout(parameters)


# signature: int blpapi_SessionOptions_sessionName(const char **sessionName,size_t *size,blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_sessionName(parameters):
    out = c_char_p()
    outp = pointer(out)
    szout = c_size_t()
    szoutp = pointer(szout)
    retCode = l_blpapi_SessionOptions_sessionName(outp, szoutp, parameters)
    return retCode, getSizedStrFromOutput(outp, szoutp, retCode)


# signature: void blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg(blpapi_SessionOptions_t *parameters,int allowMultipleCorrelatorsPerMsg);
def _blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg(
    parameters, allowMultipleCorrelatorsPerMsg
):
    l_blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg(
        parameters, allowMultipleCorrelatorsPerMsg
    )


# signature: int blpapi_SessionOptions_setApplicationIdentityKey(blpapi_SessionOptions_t *parameters,const char *applicationIdentityKey,size_t size);
def _blpapi_SessionOptions_setApplicationIdentityKey(
    parameters, applicationIdentityKey
):
    aik, sz = charPtrWithSizeFromPyStr(applicationIdentityKey)
    return l_blpapi_SessionOptions_setApplicationIdentityKey(
        parameters,
        aik,
        c_size_t(sz),
    )


# signature: void blpapi_SessionOptions_setAuthenticationOptions(blpapi_SessionOptions_t *parameters, const char *authOptions);
def _blpapi_SessionOptions_setAuthenticationOptions(parameters, authOptions):
    l_blpapi_SessionOptions_setAuthenticationOptions(
        parameters, charPtrFromPyStr(authOptions)
    )


# signature: void blpapi_SessionOptions_setAutoRestartOnDisconnection(blpapi_SessionOptions_t *parameters, int autoRestart);
def _blpapi_SessionOptions_setAutoRestartOnDisconnection(
    parameters, autoRestart
):
    l_blpapi_SessionOptions_setAutoRestartOnDisconnection(
        parameters, autoRestart
    )


# signature: int blpapi_SessionOptions_setBandwidthSaveModeDisabled(blpapi_SessionOptions_t *parameters, int disableBandwidthSaveMode);
def _blpapi_SessionOptions_setBandwidthSaveModeDisabled(
    parameters, disableBandwidthSaveMode
):
    return l_blpapi_SessionOptions_setBandwidthSaveModeDisabled(
        parameters, disableBandwidthSaveMode
    )


# signature: void blpapi_SessionOptions_setClientMode(blpapi_SessionOptions_t *parameters, int clientMode);
def _blpapi_SessionOptions_setClientMode(parameters, clientMode):
    l_blpapi_SessionOptions_setClientMode(parameters, clientMode)


# signature: int blpapi_SessionOptions_setConnectTimeout(blpapi_SessionOptions_t *parameters,unsigned int timeoutInMilliseconds);
def _blpapi_SessionOptions_setConnectTimeout(
    parameters, timeoutInMilliseconds
):
    return l_blpapi_SessionOptions_setConnectTimeout(
        parameters, c_uint32(timeoutInMilliseconds)
    )


# signature: int blpapi_SessionOptions_setDefaultKeepAliveInactivityTime(blpapi_SessionOptions_t *parameters, int inactivityMsecs);
def _blpapi_SessionOptions_setDefaultKeepAliveInactivityTime(
    parameters, inactivityMsecs
):
    return l_blpapi_SessionOptions_setDefaultKeepAliveInactivityTime(
        parameters, inactivityMsecs
    )


# signature: int blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout(blpapi_SessionOptions_t *parameters, int timeoutMsecs);
def _blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout(
    parameters, timeoutMsecs
):
    return l_blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout(
        parameters, timeoutMsecs
    )


# signature: int blpapi_SessionOptions_setDefaultServices(blpapi_SessionOptions_t *parameters, const char *defaultServices);
def _blpapi_SessionOptions_setDefaultServices(parameters, defaultServices):
    return l_blpapi_SessionOptions_setDefaultServices(
        parameters, charPtrFromPyStr(defaultServices)
    )


# signature: int blpapi_SessionOptions_setDefaultSubscriptionService(blpapi_SessionOptions_t *parameters, const char *serviceIdentifier);
def _blpapi_SessionOptions_setDefaultSubscriptionService(
    parameters, serviceIdentifier
):
    return l_blpapi_SessionOptions_setDefaultSubscriptionService(
        parameters, charPtrFromPyStr(serviceIdentifier)
    )


# signature: void blpapi_SessionOptions_setDefaultTopicPrefix(blpapi_SessionOptions_t *parameters, const char *prefix);
def _blpapi_SessionOptions_setDefaultTopicPrefix(parameters, topicPrefix):
    l_blpapi_SessionOptions_setDefaultTopicPrefix(
        parameters, charPtrFromPyStr(topicPrefix)
    )


# signature: int blpapi_SessionOptions_setFlushPublishedEventsTimeout(blpapi_SessionOptions_t *paramaters, int timeoutMsecs);
def _blpapi_SessionOptions_setFlushPublishedEventsTimeout(
    paramaters, timeoutMsecs
):
    return l_blpapi_SessionOptions_setFlushPublishedEventsTimeout(
        paramaters, timeoutMsecs
    )


# signature: int blpapi_SessionOptions_setKeepAliveEnabled(blpapi_SessionOptions_t *parameters, int isEnabled);
def _blpapi_SessionOptions_setKeepAliveEnabled(parameters, isEnabled):
    return l_blpapi_SessionOptions_setKeepAliveEnabled(parameters, isEnabled)


# signature: void blpapi_SessionOptions_setMaxEventQueueSize(blpapi_SessionOptions_t *parameters, size_t maxEventQueueSize);
def _blpapi_SessionOptions_setMaxEventQueueSize(parameters, maxEventQueueSize):
    l_blpapi_SessionOptions_setMaxEventQueueSize(
        parameters, c_size_t(maxEventQueueSize)
    )


# signature: void blpapi_SessionOptions_setMaxPendingRequests(blpapi_SessionOptions_t *parameters, int maxPendingRequests);
def _blpapi_SessionOptions_setMaxPendingRequests(
    parameters, maxPendingRequests
):
    l_blpapi_SessionOptions_setMaxPendingRequests(
        parameters, maxPendingRequests
    )


# signature: void blpapi_SessionOptions_setNumStartAttempts(blpapi_SessionOptions_t *parameters, int numStartAttempts);
def _blpapi_SessionOptions_setNumStartAttempts(parameters, numStartAttempts):
    l_blpapi_SessionOptions_setNumStartAttempts(parameters, numStartAttempts)


# signature: void blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes(blpapi_SessionOptions_t *parameters, int shouldRecord);
def _blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes(
    parameters, shouldRecord
):
    l_blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes(
        parameters, shouldRecord
    )


# signature: int blpapi_SessionOptions_setServerAddress(blpapi_SessionOptions_t *parameters,const char *serverHost,unsigned short serverPort,size_t index);
def _blpapi_SessionOptions_setServerAddress(
    parameters, serverHost, serverPort, index
):
    return l_blpapi_SessionOptions_setServerAddress(
        parameters,
        charPtrFromPyStr(serverHost),
        c_uint16(serverPort),
        c_size_t(index),
    )


# signature: int blpapi_SessionOptions_setServerAddressWithProxy(blpapi_SessionOptions_t *parameters,const char *serverHost,unsigned short serverPort,const blpapi_Socks5Config_t *socks5Config,size_t index);
def _blpapi_SessionOptions_setServerAddressWithProxy(
    parameters, serverHost, serverPort, socks5Config, index
):
    # parameters is the handle to SessionOptions
    # socks5Config if any would be a handle to Socks5Config
    return l_blpapi_SessionOptions_setServerAddressWithProxy(
        parameters,
        charPtrFromPyStr(serverHost),
        c_uint16(serverPort),
        socks5Config,
        c_size_t(index),
    )


# signature: int blpapi_SessionOptions_setServerHost(blpapi_SessionOptions_t *parameters, const char *serverHost);
def _blpapi_SessionOptions_setServerHost(parameters, serverHost):
    return l_blpapi_SessionOptions_setServerHost(
        parameters, charPtrFromPyStr(serverHost)
    )


# signature: int blpapi_SessionOptions_setServerPort(blpapi_SessionOptions_t *parameters, unsigned short serverPort);
def _blpapi_SessionOptions_setServerPort(parameters, serverPort):
    return l_blpapi_SessionOptions_setServerPort(
        parameters, c_uint16(serverPort)
    )


# signature: int blpapi_SessionOptions_setServiceCheckTimeout(blpapi_SessionOptions_t *paramaters, int timeoutMsecs);
def _blpapi_SessionOptions_setServiceCheckTimeout(paramaters, timeoutMsecs):
    return l_blpapi_SessionOptions_setServiceCheckTimeout(
        paramaters, timeoutMsecs
    )


# signature: int blpapi_SessionOptions_setServiceDownloadTimeout(blpapi_SessionOptions_t *paramaters, int timeoutMsecs);
def _blpapi_SessionOptions_setServiceDownloadTimeout(paramaters, timeoutMsecs):
    return l_blpapi_SessionOptions_setServiceDownloadTimeout(
        paramaters, timeoutMsecs
    )


# signature: int blpapi_SessionOptions_setSessionIdentityOptions(blpapi_SessionOptions_t *parameters,const blpapi_AuthOptions_t *authOptions,blpapi_CorrelationId_t *cid);
def _blpapi_SessionOptions_setSessionIdentityOptions(
    parameters, authOptions, cid
):
    # the C layer will OVERWRITE cid with autogen for unset
    cidp = pointer(cid.thestruct)
    retCode = l_blpapi_SessionOptions_setSessionIdentityOptions(
        parameters, authOptions, cidp
    )
    return retCode, cid if retCode == 0 else None


# signature: int blpapi_SessionOptions_setSessionName(blpapi_SessionOptions_t *parameters,const char *sessionName,size_t size);
def _blpapi_SessionOptions_setSessionName(parameters, sessionName):
    sn, sz = charPtrWithSizeFromPyStr(sessionName)
    return l_blpapi_SessionOptions_setSessionName(
        parameters,
        sn,
        c_size_t(sz),
    )


# signature: int blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark(blpapi_SessionOptions_t *parameters, float hiWaterMark);
def _blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark(
    parameters, hiWaterMark
):
    return l_blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark(
        parameters, c_float(hiWaterMark)
    )


# signature: int blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark(blpapi_SessionOptions_t *parameters, float loWaterMark);
def _blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark(
    parameters, loWaterMark
):
    return l_blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark(
        parameters, c_float(loWaterMark)
    )


# signature: void blpapi_SessionOptions_setTlsOptions(blpapi_SessionOptions_t *paramaters,const blpapi_TlsOptions_t *tlsOptions);
def _blpapi_SessionOptions_setTlsOptions(paramaters, tlsOptions):
    l_blpapi_SessionOptions_setTlsOptions(paramaters, tlsOptions)


# signature: float blpapi_SessionOptions_slowConsumerWarningHiWaterMark(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_slowConsumerWarningHiWaterMark(parameters):
    return l_blpapi_SessionOptions_slowConsumerWarningHiWaterMark(parameters)


# signature: float blpapi_SessionOptions_slowConsumerWarningLoWaterMark(blpapi_SessionOptions_t *parameters);
def _blpapi_SessionOptions_slowConsumerWarningLoWaterMark(parameters):
    return l_blpapi_SessionOptions_slowConsumerWarningLoWaterMark(parameters)


# signature: int blpapi_Session_createSnapshotRequestTemplate(blpapi_RequestTemplate_t **requestTemplate,blpapi_Session_t *session,const char *subscriptionString,const blpapi_Identity_t *identity,blpapi_CorrelationId_t *correlationId);
def _blpapi_Session_createSnapshotRequestTemplate(
    session, subscriptionString, identity, correlationId
):
    # the C layer will OVERWRITE cid with autogen for unset
    out = c_void_p()
    outp = pointer(out)
    idp = c_void_p() if identity is None else identity

    cidp = pointer(correlationId.thestruct)

    retCode = l_blpapi_Session_createSnapshotRequestTemplate(
        outp,
        session,
        charPtrFromPyStr(subscriptionString),
        idp,
        cidp,
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: blpapi_AbstractSession_t *blpapi_Session_getAbstractSession(blpapi_Session_t *session);
def _blpapi_Session_getAbstractSession(session):
    return getHandleFromPtr(l_blpapi_Session_getAbstractSession(session))


# signature: int blpapi_Session_nextEvent(blpapi_Session_t *session,blpapi_Event_t **eventPointer,unsigned int timeoutInMilliseconds);
def _blpapi_Session_nextEvent(session, timeoutInMilliseconds):
    eventptr = c_void_p()
    outp = pointer(eventptr)
    retCode = l_blpapi_Session_nextEvent(
        session, outp, c_uint(timeoutInMilliseconds)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Session_resubscribe(blpapi_Session_t *session,const blpapi_SubscriptionList_t *resubscriptionList,const char *requestLabel,int requestLabelLen);
def _blpapi_Session_resubscribe(session, resubscriptionList, requestLabel):
    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_resubscribe(session, resubscriptionList, label, sz)


# signature: int blpapi_Session_resubscribeEx(blpapi_Session_t *session,const blpapi_SubscriptionList_t *resubscriptionList,const char *requestLabel,int requestLabelLen,blpapi_SubscriptionPreprocessErrorHandler_t errorHandler,void *userData);
def _blpapi_Session_resubscribeEx(
    session, resubscriptionList, requestLabel, errorHandler, userData
):
    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_resubscribeEx(
        session, resubscriptionList, label, c_int(sz), errorHandler, userData
    )


# signature:
def _blpapi_Session_resubscribeEx_helper(
    session, resubscriptionList, requestLabel, errorAppenderCb
):
    proxy = anySessionSubErrorHandlerWrapper.get()
    userdata = voidFromPyFunction(errorAppenderCb)
    return _blpapi_Session_resubscribeEx(
        session, resubscriptionList, requestLabel, proxy, userdata
    )


# signature: int blpapi_Session_resubscribeWithId(blpapi_Session_t *session,const blpapi_SubscriptionList_t *resubscriptionList,int resubscriptionId,const char *requestLabel,int requestLabelLen);
def _blpapi_Session_resubscribeWithId(
    session, resubscriptionList, resubscriptionId, requestLabel
):
    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_resubscribeWithId(
        session,
        resubscriptionList,
        resubscriptionId,  # int
        label,
        sz,
    )


# signature: int blpapi_Session_resubscribeWithIdEx(blpapi_Session_t *session,const blpapi_SubscriptionList_t *resubscriptionList,int resubscriptionId,const char *requestLabel,int requestLabelLen,blpapi_SubscriptionPreprocessErrorHandler_t errorHandler,void *userData);
def _blpapi_Session_resubscribeWithIdEx(
    session,
    resubscriptionList,
    resubscriptionId,
    requestLabel,
    errorHandler,
    userdata,
):
    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_resubscribeWithIdEx(
        session,
        resubscriptionList,
        c_int(resubscriptionId),
        label,
        c_int(sz),
        errorHandler,
        userdata,
    )


# signature:
def _blpapi_Session_resubscribeWithIdEx_helper(
    session,
    resubscriptionList,
    resubscriptionId,
    requestLabel,
    errorAppenderCb,
):
    proxy = anySessionSubErrorHandlerWrapper.get()
    userdata = voidFromPyFunction(errorAppenderCb)
    return _blpapi_Session_resubscribeWithIdEx(
        session,
        resubscriptionList,
        resubscriptionId,
        requestLabel,
        proxy,
        userdata,
    )


# signature: int blpapi_Session_sendRequest(blpapi_Session_t *session,const blpapi_Request_t *request,blpapi_CorrelationId_t *correlationId,blpapi_Identity_t *identity,blpapi_EventQueue_t *eventQueue,const char *requestLabel,int requestLabelLen);
def _blpapi_Session_sendRequest(
    session, request, correlationId, identity, eventQueue, requestLabel
):
    # the C layer will OVERWRITE cid with autogen for unset
    cidp = pointer(correlationId.thestruct)

    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_sendRequest(
        session,
        request,
        cidp,
        identity,
        eventQueue,
        label,
        sz,  # int
    )


# signature: int blpapi_Session_sendRequestTemplate(blpapi_Session_t *session,const blpapi_RequestTemplate_t *requestTemplate,blpapi_CorrelationId_t *correlationId);
def _blpapi_Session_sendRequestTemplate(
    session, requestTemplate, correlationId
):
    # the C layer will OVERWRITE cid with autogen for unset
    cidp = pointer(correlationId.thestruct)

    return l_blpapi_Session_sendRequestTemplate(
        session,
        requestTemplate,
        cidp,
    )


# signature: int blpapi_Session_setStatusCorrelationId(blpapi_Session_t *session,const blpapi_Service_t *service,const blpapi_Identity_t *identity,const blpapi_CorrelationId_t *correlationId);
def _blpapi_Session_setStatusCorrelationId(
    session, service, identity, correlationId
):
    return l_blpapi_Session_setStatusCorrelationId(
        session, service, identity, byref(correlationId.thestruct)
    )


# signature: int blpapi_Session_start(blpapi_Session_t *session);
def _blpapi_Session_start(session):
    return l_blpapi_Session_start(session)


# signature: int blpapi_Session_startAsync(blpapi_Session_t *session);
def _blpapi_Session_startAsync(session):
    return l_blpapi_Session_startAsync(session)


# signature: int blpapi_Session_stop(blpapi_Session_t *session);
def _blpapi_Session_stop(session):
    return l_blpapi_Session_stop(session)


# signature: int blpapi_Session_stopAsync(blpapi_Session_t *session);
def _blpapi_Session_stopAsync(session):
    return l_blpapi_Session_stopAsync(session)


# signature: int blpapi_Session_subscribe(blpapi_Session_t *session,const blpapi_SubscriptionList_t *subscriptionList,const blpapi_Identity_t *handle,const char *requestLabel,int requestLabelLen);
def _blpapi_Session_subscribe(session, subscriptionList, handle, requestLabel):
    # handle is identity
    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_subscribe(
        session, subscriptionList, handle, label, sz  # int
    )


# signature: int blpapi_Session_subscribeEx(blpapi_Session_t *session,const blpapi_SubscriptionList_t *subscriptionList,const blpapi_Identity_t *handle,const char *requestLabel,int requestLabelLen,blpapi_SubscriptionPreprocessErrorHandler_t errorHandler,void *userData);
def _blpapi_Session_subscribeEx(
    session, subscriptionList, handle, requestLabel, errorHandler, userData
):
    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_subscribeEx(
        session,
        subscriptionList,
        handle,
        label,
        c_int(sz),
        errorHandler,
        userData,
    )


# signature:
def _blpapi_Session_subscribeEx_helper(
    session, subscriptionList, identity, requestLabel, errorAppenderCb
):
    proxy = anySessionSubErrorHandlerWrapper.get()
    userdata = voidFromPyFunction(errorAppenderCb)
    return _blpapi_Session_subscribeEx(
        session, subscriptionList, identity, requestLabel, proxy, userdata
    )


# signature: int blpapi_Session_tryNextEvent(blpapi_Session_t *session, blpapi_Event_t **eventPointer);
def _blpapi_Session_tryNextEvent(session):
    eventptr = c_void_p()
    outp = pointer(eventptr)
    retCode = l_blpapi_Session_tryNextEvent(session, outp)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_Session_unsubscribe(blpapi_Session_t *session,const blpapi_SubscriptionList_t *unsubscriptionList,const char *requestLabel,int requestLabelLen);
def _blpapi_Session_unsubscribe(session, unsubscriptionList, requestLabel):
    label, sz = charPtrWithSizeFromPyStr(requestLabel)
    return l_blpapi_Session_unsubscribe(
        session, unsubscriptionList, label, sz  # sz is int
    )


# signature: blpapi_Socks5Config_t *blpapi_Socks5Config_create(const char *hostname, size_t hostname_size, unsigned short port);
def _blpapi_Socks5Config_create(hostname, port):
    hn, sz = charPtrWithSizeFromPyStr(hostname)
    return getHandleFromPtr(
        l_blpapi_Socks5Config_create(hn, c_size_t(sz), c_uint16(port))
    )


# signature: void blpapi_Socks5Config_destroy(blpapi_Socks5Config_t *socks5Config);
def _blpapi_Socks5Config_destroy(socks5Config):
    l_blpapi_Socks5Config_destroy(socks5Config)


# signature:
def _blpapi_Socks5Config_printHelper(socks5Config, level, spacesPerLevel):
    return any_printer(
        socks5Config, l_blpapi_Socks5Config_print, level, spacesPerLevel
    )


# signature:
def _blpapi_SubscriptionList_addHelper(slist, topic, correlationId):
    return l_blpapi_SubscriptionList_add(
        slist,
        charPtrFromPyStr(topic),
        byref(correlationId.thestruct),
        None,
        None,
        0,
        0,
    )


# signature: int blpapi_SubscriptionList_addResolved(blpapi_SubscriptionList_t *list,const char *subscriptionString,const blpapi_CorrelationId_t *correlationId);
def _blpapi_SubscriptionList_addResolved(
    slist, subscriptionString, correlationId
):
    return l_blpapi_SubscriptionList_addResolved(
        slist,
        charPtrFromPyStr(subscriptionString),
        byref(correlationId.thestruct),
    )


# signature: int blpapi_SubscriptionList_append(blpapi_SubscriptionList_t *dest, const blpapi_SubscriptionList_t *src);
def _blpapi_SubscriptionList_append(dest, src):
    return l_blpapi_SubscriptionList_append(dest, src)


# signature: int blpapi_SubscriptionList_clear(blpapi_SubscriptionList_t *list);
def _blpapi_SubscriptionList_clear(slist):
    return l_blpapi_SubscriptionList_clear(slist)


# signature: int blpapi_SubscriptionList_correlationIdAt(const blpapi_SubscriptionList_t *list,blpapi_CorrelationId_t *result,size_t index);
def _blpapi_SubscriptionList_correlationIdAt(slist, index):
    cid = CidStruct()
    cidp = pointer(cid)
    retCode = l_blpapi_SubscriptionList_correlationIdAt(
        slist, cidp, c_size_t(index)
    )
    if retCode == 0:
        # C doese *result = list->d_impl.subscription(index).d_correlationId.impl();
        # i.e., we need to bump ref
        # the caller will wrap this in CorrelationId
        return retCode, cid
    return retCode, None


# signature: blpapi_SubscriptionList_t *blpapi_SubscriptionList_create(void);
def _blpapi_SubscriptionList_create():
    return getHandleFromPtr(l_blpapi_SubscriptionList_create())


# signature: void blpapi_SubscriptionList_destroy(blpapi_SubscriptionList_t *list);
def _blpapi_SubscriptionList_destroy(slist):
    l_blpapi_SubscriptionList_destroy(slist)


# signature: int blpapi_SubscriptionList_isResolvedAt(blpapi_SubscriptionList_t *list, int *result, size_t index);
def _blpapi_SubscriptionList_isResolvedAt(slist, index):
    out = c_int()
    outp = pointer(out)
    retCode = l_blpapi_SubscriptionList_isResolvedAt(
        slist, outp, c_size_t(index)
    )
    return retCode, getPODFromOutput(outp, retCode) != 0


# signature: int blpapi_SubscriptionList_size(const blpapi_SubscriptionList_t *list);
def _blpapi_SubscriptionList_size(slist):
    return l_blpapi_SubscriptionList_size(slist)  # int


# signature: int blpapi_SubscriptionList_topicStringAt(blpapi_SubscriptionList_t *list, const char **result, size_t index);
def _blpapi_SubscriptionList_topicStringAt(slist, index):
    out = c_char_p()
    outp = pointer(out)
    retCode = l_blpapi_SubscriptionList_topicStringAt(
        slist, outp, c_size_t(index)
    )
    return retCode, getStrFromOutput(outp, retCode)


# signature: int blpapi_TestUtil_appendMessage(blpapi_MessageFormatter_t **formatter,blpapi_Event_t *event,const blpapi_SchemaElementDefinition_t *messageType,const blpapi_MessageProperties_t *properties);
def _blpapi_TestUtil_appendMessage(event, messageType, properties):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_TestUtil_appendMessage(
        outp, event, messageType, properties
    )  # int
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_TestUtil_createEvent(blpapi_Event_t **event, int eventType);
def _blpapi_TestUtil_createEvent(eventType):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_TestUtil_createEvent(outp, eventType)  # int
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_TestUtil_createTopic(blpapi_Topic_t **topic, const blpapi_Service_t *service, int isActive);
def _blpapi_TestUtil_createTopic(service, isActive):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_TestUtil_createTopic(outp, service, isActive)  # int
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_TestUtil_deserializeService(const char *schema, size_t schemaLength, blpapi_Service_t **service);
def _blpapi_TestUtil_deserializeService(
    schema, schemaLength
):  # pylint: disable=unused-argument
    out = c_void_p()
    outp = pointer(out)
    schemac, sz = charPtrWithSizeFromPyStr(schema)
    retCode = l_blpapi_TestUtil_deserializeService(
        schemac, c_size_t(sz), outp
    )  # int
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_TestUtil_getAdminMessageDefinition(blpapi_SchemaElementDefinition_t **definition,blpapi_Name_t *messageName);
def _blpapi_TestUtil_getAdminMessageDefinition(messageName):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_TestUtil_getAdminMessageDefinition(
        outp, messageName
    )  # int
    return retCode, getHandleFromOutput(outp, retCode)


# signature:
def _blpapi_TestUtil_serializeServiceHelper(service):
    out = StringIO()
    writer = StreamWrapper()
    outparam = voidFromPyObject(out)
    retCode = l_blpapi_TestUtil_serializeService(
        writer.get(), outparam, service
    )
    if retCode:
        return None
    out.seek(0)
    return out.read()


# signature: long long blpapi_TimePointUtil_nanosecondsBetween(const blpapi_TimePoint_t *start, const blpapi_TimePoint_t *end);
def _blpapi_TimePointUtil_nanosecondsBetween(start, end):
    raise NotImplementedError("not called")


# signature: blpapi_TlsOptions_t *blpapi_TlsOptions_createFromBlobs(const char *clientCredentialsRawData,int clientCredentialsRawDataLength,const char *clientCredentialsPassword,const char *trustedCertificatesRawData,int trustedCertificatesRawDataLength);
def _blpapi_TlsOptions_createFromBlobs(
    clientCredentialsRawData,
    clientCredentialsPassword,
    trustedCertificatesRawData,
):
    cc, ccsz = charPtrWithSizeFromPyStr(clientCredentialsRawData)
    tc, tcsz = charPtrWithSizeFromPyStr(trustedCertificatesRawData)
    return getHandleFromPtr(
        l_blpapi_TlsOptions_createFromBlobs(
            cc, ccsz, charPtrFromPyStr(clientCredentialsPassword), tc, tcsz
        )
    )


# signature: blpapi_TlsOptions_t *blpapi_TlsOptions_createFromFiles(const char *clientCredentialsFileName,const char *clientCredentialsPassword,const char *trustedCertificatesFileName);
def _blpapi_TlsOptions_createFromFiles(
    clientCredentialsFileName,
    clientCredentialsPassword,
    trustedCertificatesFileName,
):
    return getHandleFromPtr(
        l_blpapi_TlsOptions_createFromFiles(
            charPtrFromPyStr(clientCredentialsFileName),
            charPtrFromPyStr(clientCredentialsPassword),
            charPtrFromPyStr(trustedCertificatesFileName),
        )
    )


# signature: void blpapi_TlsOptions_destroy(blpapi_TlsOptions_t *parameters);
def _blpapi_TlsOptions_destroy(parameters):
    l_blpapi_TlsOptions_destroy(parameters)


# signature: void blpapi_TlsOptions_setCrlFetchTimeoutMs(blpapi_TlsOptions_t *paramaters, int crlFetchTimeoutMs);
def _blpapi_TlsOptions_setCrlFetchTimeoutMs(paramaters, crlFetchTimeoutMs):
    l_blpapi_TlsOptions_setCrlFetchTimeoutMs(paramaters, crlFetchTimeoutMs)


# signature: void blpapi_TlsOptions_setTlsHandshakeTimeoutMs(blpapi_TlsOptions_t *paramaters, int tlsHandshakeTimeoutMs);
def _blpapi_TlsOptions_setTlsHandshakeTimeoutMs(
    paramaters, tlsHandshakeTimeoutMs
):
    l_blpapi_TlsOptions_setTlsHandshakeTimeoutMs(
        paramaters, tlsHandshakeTimeoutMs
    )


# signature: int blpapi_TopicList_add(blpapi_TopicList_t *list,const char *topic,const blpapi_CorrelationId_t *correlationId);
def _blpapi_TopicList_add(topic_list, topic, correlationId):
    return l_blpapi_TopicList_add(
        topic_list,
        charPtrFromPyStr(topic),
        byref(correlationId.thestruct),
    )


# signature: int blpapi_TopicList_addFromMessage(blpapi_TopicList_t *list,const blpapi_Message_t *topic,const blpapi_CorrelationId_t *correlationId);
def _blpapi_TopicList_addFromMessage(topic_list, message, correlationId):
    return l_blpapi_TopicList_addFromMessage(
        topic_list, message, byref(correlationId.thestruct)
    )


# signature: int blpapi_TopicList_correlationIdAt(const blpapi_TopicList_t *list,blpapi_CorrelationId_t *result,size_t index);
def _blpapi_TopicList_correlationIdAt(topic_list, index):
    cid = CidStruct()
    cidp = pointer(cid)
    retCode = l_blpapi_TopicList_correlationIdAt(
        topic_list, cidp, c_size_t(index)
    )
    if retCode == 0:
        # C does *result = rlImpl->correlationId(index).impl();
        # i.e, we need to bump ref.
        # the caller will wrap this in CorrelationId
        return retCode, cid
    return retCode, None


# signature: blpapi_TopicList_t *blpapi_TopicList_create(blpapi_TopicList_t *from);
def _blpapi_TopicList_create(_from):
    fromp = c_void_p() if _from is None else _from
    return getHandleFromPtr(l_blpapi_TopicList_create(fromp))


# signature:
def _blpapi_TopicList_createFromResolutionList(_from):
    return getHandleFromPtr(l_blpapi_TopicList_create(_from))


# signature: void blpapi_TopicList_destroy(blpapi_TopicList_t *list);
def _blpapi_TopicList_destroy(topic_list):
    l_blpapi_TopicList_destroy(topic_list)


# signature: int blpapi_TopicList_message(const blpapi_TopicList_t *list,blpapi_Message_t **element,const blpapi_CorrelationId_t *id);
def _blpapi_TopicList_message(topic_list, cid):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_TopicList_message(
        topic_list, outp, byref(cid.thestruct)
    )
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_TopicList_messageAt(const blpapi_TopicList_t *list,blpapi_Message_t **element,size_t index);
def _blpapi_TopicList_messageAt(topic_list, index):
    out = c_void_p()
    outp = pointer(out)
    retCode = l_blpapi_TopicList_messageAt(topic_list, outp, index)
    return retCode, getHandleFromOutput(outp, retCode)


# signature: int blpapi_TopicList_size(const blpapi_TopicList_t *list);
def _blpapi_TopicList_size(topic_list):
    return l_blpapi_TopicList_size(topic_list)  # int


# signature: int blpapi_TopicList_status(const blpapi_TopicList_t *list,int *status,const blpapi_CorrelationId_t *id);
def _blpapi_TopicList_status(topic_list, cid):
    out = c_int()
    outp = pointer(out)
    retCode = l_blpapi_TopicList_status(topic_list, outp, byref(cid.thestruct))
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_TopicList_statusAt(const blpapi_TopicList_t *list, int *status, size_t index);
def _blpapi_TopicList_statusAt(topic_list, index):
    out = c_int()
    outp = pointer(out)
    retCode = l_blpapi_TopicList_statusAt(topic_list, outp, index)
    return retCode, getPODFromOutput(outp, retCode)


# signature: int blpapi_TopicList_topicString(const blpapi_TopicList_t *list,const char **topic,const blpapi_CorrelationId_t *id);
def _blpapi_TopicList_topicString(topic_list, cid):
    out = c_char_p()
    outp = pointer(out)
    retCode = l_blpapi_TopicList_topicString(
        topic_list, outp, byref(cid.thestruct)
    )
    return retCode, getStrFromOutput(outp, retCode)


# signature: int blpapi_TopicList_topicStringAt(const blpapi_TopicList_t *list, const char **topic, size_t index);
def _blpapi_TopicList_topicStringAt(topic_list, index):
    out = c_char_p()
    outp = pointer(out)
    retCode = l_blpapi_TopicList_topicStringAt(topic_list, outp, index)
    return retCode, getStrFromOutput(outp, retCode)


# signature: int blpapi_Topic_compare(const blpapi_Topic_t *lhs, const blpapi_Topic_t *rhs);
def _blpapi_Topic_compare(lhs, rhs):
    return l_blpapi_Topic_compare(lhs, rhs)


# signature: blpapi_Topic_t *blpapi_Topic_create(blpapi_Topic_t *from);
def _blpapi_Topic_create(_from):
    raise NotImplementedError("not called")


# signature: void blpapi_Topic_destroy(blpapi_Topic_t *victim);
def _blpapi_Topic_destroy(victim):
    l_blpapi_Topic_destroy(victim)


# signature: int blpapi_Topic_isActive(const blpapi_Topic_t *topic);
def _blpapi_Topic_isActive(topic):
    return l_blpapi_Topic_isActive(topic) != 0


# signature: blpapi_Service_t *blpapi_Topic_service(const blpapi_Topic_t *topic);
def _blpapi_Topic_service(topic):
    return getHandleFromPtr(l_blpapi_Topic_service(topic))


# signature: int blpapi_UserAgentInfo_setUserTaskName(const char *userTaskName);
def _blpapi_UserAgentInfo_setUserTaskName(userTaskName):
    return l_blpapi_UserAgentInfo_setUserTaskName(
        charPtrFromPyStr(userTaskName)
    )


# signature: int blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion(const char *language, const char *version);
def _blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion(language, version):
    return l_blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion(
        charPtrFromPyStr(language), charPtrFromPyStr(version)
    )


# signature: int blpapi_ZfpUtil_getOptionsForLeasedLines(blpapi_SessionOptions_t *sessionOptions,const blpapi_TlsOptions_t *tlsOptions,int remote);
def _blpapi_ZfpUtil_getOptionsForLeasedLines(
    sessionOptions, tlsOptions, remote
):
    return l_blpapi_ZfpUtil_getOptionsForLeasedLines(
        sessionOptions, tlsOptions, remote
    )


# signature: const char *blpapi_getLastErrorDescription(int resultCode);
def _blpapi_getLastErrorDescription(resultCode):
    return getStrFromC(l_blpapi_getLastErrorDescription(resultCode))


def _blpapi_getVersionInfo():
    major = c_int()
    majorp = pointer(major)
    minor = c_int()
    minorp = pointer(minor)
    patch = c_int()
    patchp = pointer(patch)
    build = c_int()
    buildp = pointer(build)

    l_blpapi_getVersionInfo(majorp, minorp, patchp, buildp)

    return ".".join(
        [
            str(major.value),
            str(minor.value),
            str(patch.value),
            str(build.value),
        ]
    )


def _ProviderSession_createHelper(parameters, eventHandlerFunc, dispatcher):
    # parameters is a handle to SessionOptions
    # eventHandlerFunc is python callback
    # dispatcher is a handle to dispatcher, which we honestly hope to be None!
    # returns handle to Session
    hasHandler = eventHandlerFunc is not None
    if hasHandler:
        handlerparam = anySessionEventHandlerWrapper.get()
        userdata = voidFromPyFunction(eventHandlerFunc)
    else:
        handlerparam = c_void_p(0)
        userdata = c_void_p(0)
    handle = l_blpapi_ProviderSession_create(
        parameters,
        handlerparam,
        dispatcher,
        userdata,
    )
    return getHandleFromPtr(handle)


def _ProviderSession_destroyHelper(sessionHandle, _eventHandlerFunc):
    l_blpapi_ProviderSession_destroy(sessionHandle)


def _Session_createHelper(parameters, dispatcher):
    # parameters is a handle to SessionOptions
    # dispatcher is a handle to dispatcher, which we honestly hope to be None!
    # returns handle to Session
    handlerparam = c_void_p(0)
    userdata = c_void_p(0)

    # `Session.py` uses now a separated thread to poll event from the queue
    # so we do not need to pass a handler parameter to C++ anymore.
    # In the past, C++ used this function to call back into Python (bindings)

    handle = l_blpapi_Session_create(
        parameters,
        handlerparam,
        dispatcher,
        userdata,
    )
    # returns address of control block of shared_ptr<SessionImpl>
    return getHandleFromPtr(handle)


def _Session_destroyHelper(sessionHandle, _eventHandlerFunc):
    l_blpapi_Session_destroy(sessionHandle)


blpapi_AbstractSession_cancel = _blpapi_AbstractSession_cancel
blpapi_AbstractSession_createIdentity = _blpapi_AbstractSession_createIdentity
blpapi_AbstractSession_generateAuthorizedIdentityAsync = (
    _blpapi_AbstractSession_generateAuthorizedIdentityAsync
)
blpapi_AbstractSession_generateManualToken = (
    _blpapi_AbstractSession_generateManualToken
)
blpapi_AbstractSession_generateToken = _blpapi_AbstractSession_generateToken
blpapi_AbstractSession_getAuthorizedIdentity = (
    _blpapi_AbstractSession_getAuthorizedIdentity
)
blpapi_AbstractSession_getService = _blpapi_AbstractSession_getService
blpapi_AbstractSession_openService = _blpapi_AbstractSession_openService
blpapi_AbstractSession_openServiceAsync = (
    _blpapi_AbstractSession_openServiceAsync
)
blpapi_AbstractSession_sendAuthorizationRequest = (
    _blpapi_AbstractSession_sendAuthorizationRequest
)
blpapi_AbstractSession_sessionName = _blpapi_AbstractSession_sessionName
blpapi_AuthApplication_copy = _blpapi_AuthApplication_copy
blpapi_AuthApplication_create = _blpapi_AuthApplication_create
blpapi_AuthApplication_destroy = _blpapi_AuthApplication_destroy
blpapi_AuthApplication_duplicate = _blpapi_AuthApplication_duplicate
blpapi_AuthOptions_copy = _blpapi_AuthOptions_copy
blpapi_AuthOptions_create_default = _blpapi_AuthOptions_create_default
blpapi_AuthOptions_create_forAppMode = _blpapi_AuthOptions_create_forAppMode
blpapi_AuthOptions_create_forToken = _blpapi_AuthOptions_create_forToken
blpapi_AuthOptions_create_forUserAndAppMode = (
    _blpapi_AuthOptions_create_forUserAndAppMode
)
blpapi_AuthOptions_create_forUserMode = _blpapi_AuthOptions_create_forUserMode
blpapi_AuthOptions_destroy = _blpapi_AuthOptions_destroy
blpapi_AuthOptions_duplicate = _blpapi_AuthOptions_duplicate
blpapi_AuthToken_copy = _blpapi_AuthToken_copy
blpapi_AuthToken_create = _blpapi_AuthToken_create
blpapi_AuthToken_destroy = _blpapi_AuthToken_destroy
blpapi_AuthToken_duplicate = _blpapi_AuthToken_duplicate
blpapi_AuthUser_copy = _blpapi_AuthUser_copy
blpapi_AuthUser_createWithActiveDirectoryProperty = (
    _blpapi_AuthUser_createWithActiveDirectoryProperty
)
blpapi_AuthUser_createWithLogonName = _blpapi_AuthUser_createWithLogonName
blpapi_AuthUser_createWithManualOptions = (
    _blpapi_AuthUser_createWithManualOptions
)
blpapi_AuthUser_destroy = _blpapi_AuthUser_destroy
blpapi_AuthUser_duplicate = _blpapi_AuthUser_duplicate
blpapi_ConstantList_datatype = _blpapi_ConstantList_datatype
blpapi_ConstantList_description = _blpapi_ConstantList_description
blpapi_ConstantList_getConstant = _blpapi_ConstantList_getConstant
blpapi_ConstantList_getConstantAt = _blpapi_ConstantList_getConstantAt
blpapi_ConstantList_hasConstant = _blpapi_ConstantList_hasConstant
blpapi_ConstantList_name = _blpapi_ConstantList_name
blpapi_ConstantList_numConstants = _blpapi_ConstantList_numConstants
blpapi_ConstantList_status = _blpapi_ConstantList_status
blpapi_Constant_datatype = _blpapi_Constant_datatype
blpapi_Constant_description = _blpapi_Constant_description
blpapi_Constant_getValueAsChar = _blpapi_Constant_getValueAsChar
blpapi_Constant_getValueAsDatetime = _blpapi_Constant_getValueAsDatetime
blpapi_Constant_getValueAsFloat32 = _blpapi_Constant_getValueAsFloat32
blpapi_Constant_getValueAsFloat64 = _blpapi_Constant_getValueAsFloat64
blpapi_Constant_getValueAsInt32 = _blpapi_Constant_getValueAsInt32
blpapi_Constant_getValueAsInt64 = _blpapi_Constant_getValueAsInt64
blpapi_Constant_getValueAsString = _blpapi_Constant_getValueAsString
blpapi_Constant_name = _blpapi_Constant_name
blpapi_Constant_status = _blpapi_Constant_status
blpapi_Datetime_tag = BDatetime
blpapi_DiagnosticsUtil_memoryInfo_wrapper = (
    _blpapi_DiagnosticsUtil_memoryInfo_wrapper
)
blpapi_Element_appendElement = _blpapi_Element_appendElement
blpapi_Element_datatype = _blpapi_Element_datatype
blpapi_Element_definition = _blpapi_Element_definition
blpapi_Element_getChoice = _blpapi_Element_getChoice
blpapi_Element_getElement = _blpapi_Element_getElement
blpapi_Element_getElementAt = _blpapi_Element_getElementAt
blpapi_Element_getValueAsBool = _blpapi_Element_getValueAsBool
blpapi_Element_getValueAsBytes = _blpapi_Element_getValueAsBytes
blpapi_Element_getValueAsChar = _blpapi_Element_getValueAsChar
blpapi_Element_getValueAsDatetime = _blpapi_Element_getValueAsDatetime
blpapi_Element_getValueAsElement = _blpapi_Element_getValueAsElement
blpapi_Element_getValueAsFloat64 = _blpapi_Element_getValueAsFloat64
blpapi_Element_getValueAsHighPrecisionDatetime = (
    _blpapi_Element_getValueAsHighPrecisionDatetime
)
blpapi_Element_getValueAsInt32 = _blpapi_Element_getValueAsInt32
blpapi_Element_getValueAsInt64 = _blpapi_Element_getValueAsInt64
blpapi_Element_getValueAsName = _blpapi_Element_getValueAsName
blpapi_Element_getValueAsString = _blpapi_Element_getValueAsString
blpapi_Element_hasElementEx = _blpapi_Element_hasElementEx
blpapi_Element_isArray = _blpapi_Element_isArray
blpapi_Element_isComplexType = _blpapi_Element_isComplexType
blpapi_Element_isNull = _blpapi_Element_isNull
blpapi_Element_isNullValue = _blpapi_Element_isNullValue
blpapi_Element_isReadOnly = _blpapi_Element_isReadOnly
blpapi_Element_name = _blpapi_Element_name
blpapi_Element_nameString = _blpapi_Element_nameString
blpapi_Element_numElements = _blpapi_Element_numElements
blpapi_Element_numValues = _blpapi_Element_numValues
blpapi_Element_printHelper = _blpapi_Element_printHelper
blpapi_Element_setChoice = _blpapi_Element_setChoice
blpapi_Element_setElementBool = _blpapi_Element_setElementBool
blpapi_Element_setElementBytes = _blpapi_Element_setElementBytes
blpapi_Element_setElementFloat = _blpapi_Element_setElementFloat
blpapi_Element_setElementFromName = _blpapi_Element_setElementFromName
blpapi_Element_setElementHighPrecisionDatetime = (
    _blpapi_Element_setElementHighPrecisionDatetime
)
blpapi_Element_setElementInt32 = _blpapi_Element_setElementInt32
blpapi_Element_setElementInt64 = _blpapi_Element_setElementInt64
blpapi_Element_setElementString = _blpapi_Element_setElementString
blpapi_Element_setValueBool = _blpapi_Element_setValueBool
blpapi_Element_setValueBytes = _blpapi_Element_setValueBytes
blpapi_Element_setValueFloat = _blpapi_Element_setValueFloat
blpapi_Element_setValueFromName = _blpapi_Element_setValueFromName
blpapi_Element_setValueHighPrecisionDatetime = (
    _blpapi_Element_setValueHighPrecisionDatetime
)
blpapi_Element_setValueInt32 = _blpapi_Element_setValueInt32
blpapi_Element_setValueInt64 = _blpapi_Element_setValueInt64
blpapi_Element_setValueString = _blpapi_Element_setValueString
blpapi_Element_toJson = _blpapi_Element_toJson
blpapi_Element_toJsonHelper = _blpapi_Element_toJsonHelper
blpapi_Element_fromJson = _blpapi_Element_fromJson
blpapi_Element_toPy = _blpapi_Element_toPy
blpapi_EventDispatcher_create = _blpapi_EventDispatcher_create
blpapi_EventDispatcher_destroy = _blpapi_EventDispatcher_destroy
blpapi_EventDispatcher_start = _blpapi_EventDispatcher_start
blpapi_EventDispatcher_stop = _blpapi_EventDispatcher_stop
blpapi_EventFormatter_appendElement = _blpapi_EventFormatter_appendElement
blpapi_EventFormatter_appendFragmentedRecapMessage = (
    _blpapi_EventFormatter_appendFragmentedRecapMessage
)
blpapi_EventFormatter_appendFragmentedRecapMessageSeq = (
    _blpapi_EventFormatter_appendFragmentedRecapMessageSeq
)
blpapi_EventFormatter_appendMessage = _blpapi_EventFormatter_appendMessage
blpapi_EventFormatter_appendMessageSeq = (
    _blpapi_EventFormatter_appendMessageSeq
)
blpapi_EventFormatter_appendRecapMessage = (
    _blpapi_EventFormatter_appendRecapMessage
)
blpapi_EventFormatter_appendRecapMessageSeq = (
    _blpapi_EventFormatter_appendRecapMessageSeq
)
blpapi_EventFormatter_appendResponse = _blpapi_EventFormatter_appendResponse
blpapi_EventFormatter_appendValueBool = _blpapi_EventFormatter_appendValueBool
blpapi_EventFormatter_appendValueChar = _blpapi_EventFormatter_appendValueChar
blpapi_EventFormatter_appendValueFloat = (
    _blpapi_EventFormatter_appendValueFloat
)
blpapi_EventFormatter_appendValueFromName = (
    _blpapi_EventFormatter_appendValueFromName
)
blpapi_EventFormatter_appendValueHighPrecisionDatetime = (
    _blpapi_EventFormatter_appendValueHighPrecisionDatetime
)
blpapi_EventFormatter_appendValueInt32 = (
    _blpapi_EventFormatter_appendValueInt32
)
blpapi_EventFormatter_appendValueInt64 = (
    _blpapi_EventFormatter_appendValueInt64
)
blpapi_EventFormatter_appendValueString = (
    _blpapi_EventFormatter_appendValueString
)
blpapi_EventFormatter_create = _blpapi_EventFormatter_create
blpapi_EventFormatter_destroy = _blpapi_EventFormatter_destroy
blpapi_EventFormatter_popElement = _blpapi_EventFormatter_popElement
blpapi_EventFormatter_pushElement = _blpapi_EventFormatter_pushElement
blpapi_EventFormatter_setValueBool = _blpapi_EventFormatter_setValueBool
blpapi_EventFormatter_setValueBytes = _blpapi_EventFormatter_setValueBytes
blpapi_EventFormatter_setValueChar = _blpapi_EventFormatter_setValueChar
blpapi_EventFormatter_setValueFloat = _blpapi_EventFormatter_setValueFloat
blpapi_EventFormatter_setValueFromName = (
    _blpapi_EventFormatter_setValueFromName
)
blpapi_EventFormatter_setValueHighPrecisionDatetime = (
    _blpapi_EventFormatter_setValueHighPrecisionDatetime
)
blpapi_EventFormatter_setValueInt32 = _blpapi_EventFormatter_setValueInt32
blpapi_EventFormatter_setValueInt64 = _blpapi_EventFormatter_setValueInt64
blpapi_EventFormatter_setValueNull = _blpapi_EventFormatter_setValueNull
blpapi_EventFormatter_setValueString = _blpapi_EventFormatter_setValueString
blpapi_EventFormatter_getElement = _blpapi_EventFormatter_getElement
blpapi_EventQueue_create = _blpapi_EventQueue_create
blpapi_EventQueue_destroy = _blpapi_EventQueue_destroy
blpapi_EventQueue_nextEvent = _blpapi_EventQueue_nextEvent
blpapi_EventQueue_purge = _blpapi_EventQueue_purge
blpapi_EventQueue_tryNextEvent = _blpapi_EventQueue_tryNextEvent
blpapi_Event_eventType = _blpapi_Event_eventType
blpapi_Event_release = _blpapi_Event_release
blpapi_HighPrecisionDatetime_compare = _blpapi_HighPrecisionDatetime_compare
blpapi_HighPrecisionDatetime_fromTimePoint = (
    _blpapi_HighPrecisionDatetime_fromTimePoint
)
blpapi_HighPrecisionDatetime_fromTimePoint_wrapper = (
    _blpapi_HighPrecisionDatetime_fromTimePoint_wrapper
)
blpapi_HighPrecisionDatetime_print = _blpapi_HighPrecisionDatetime_print
blpapi_HighPrecisionDatetime_tag = HighPrecisionDatetime
blpapi_HighResolutionClock_now = _blpapi_HighResolutionClock_now
blpapi_Identity_addRef = _blpapi_Identity_addRef
blpapi_Identity_getSeatType = _blpapi_Identity_getSeatType
blpapi_Identity_hasEntitlements = _blpapi_Identity_hasEntitlements
blpapi_Identity_isAuthorized = _blpapi_Identity_isAuthorized
blpapi_Identity_release = _blpapi_Identity_release
blpapi_Logging_logTestMessage = _blpapi_Logging_logTestMessage
blpapi_Logging_registerCallback = _blpapi_Logging_registerCallback
blpapi_MessageFormatter_FormatMessageJson = (
    _blpapi_MessageFormatter_FormatMessageJson
)
blpapi_MessageFormatter_FormatMessageXml = (
    _blpapi_MessageFormatter_FormatMessageXml
)
blpapi_MessageFormatter_appendElement = _blpapi_MessageFormatter_appendElement
blpapi_MessageFormatter_appendValueBool = (
    _blpapi_MessageFormatter_appendValueBool
)
blpapi_MessageFormatter_appendValueChar = (
    _blpapi_MessageFormatter_appendValueChar
)
blpapi_MessageFormatter_appendValueDatetime = (
    _blpapi_MessageFormatter_appendValueDatetime
)
blpapi_MessageFormatter_appendValueFloat = (
    _blpapi_MessageFormatter_appendValueFloat
)
blpapi_MessageFormatter_appendValueFloat32 = (
    _blpapi_MessageFormatter_appendValueFloat32
)
blpapi_MessageFormatter_appendValueFloat64 = (
    _blpapi_MessageFormatter_appendValueFloat64
)
blpapi_MessageFormatter_appendValueFromName = (
    _blpapi_MessageFormatter_appendValueFromName
)
blpapi_MessageFormatter_appendValueHighPrecisionDatetime = (
    _blpapi_MessageFormatter_appendValueHighPrecisionDatetime
)
blpapi_MessageFormatter_appendValueInt32 = (
    _blpapi_MessageFormatter_appendValueInt32
)
blpapi_MessageFormatter_appendValueInt64 = (
    _blpapi_MessageFormatter_appendValueInt64
)
blpapi_MessageFormatter_appendValueString = (
    _blpapi_MessageFormatter_appendValueString
)
blpapi_MessageFormatter_assign = _blpapi_MessageFormatter_assign
blpapi_MessageFormatter_copy = _blpapi_MessageFormatter_copy
blpapi_MessageFormatter_destroy = _blpapi_MessageFormatter_destroy
blpapi_MessageFormatter_popElement = _blpapi_MessageFormatter_popElement
blpapi_MessageFormatter_pushElement = _blpapi_MessageFormatter_pushElement
blpapi_MessageFormatter_setValueBool = _blpapi_MessageFormatter_setValueBool
blpapi_MessageFormatter_setValueBytes = _blpapi_MessageFormatter_setValueBytes
blpapi_MessageFormatter_setValueChar = _blpapi_MessageFormatter_setValueChar
blpapi_MessageFormatter_setValueDatetime = (
    _blpapi_MessageFormatter_setValueDatetime
)
blpapi_MessageFormatter_setValueFloat = _blpapi_MessageFormatter_setValueFloat
blpapi_MessageFormatter_setValueFloat32 = (
    _blpapi_MessageFormatter_setValueFloat32
)
blpapi_MessageFormatter_setValueFloat64 = (
    _blpapi_MessageFormatter_setValueFloat64
)
blpapi_MessageFormatter_setValueFromName = (
    _blpapi_MessageFormatter_setValueFromName
)
blpapi_MessageFormatter_setValueHighPrecisionDatetime = (
    _blpapi_MessageFormatter_setValueHighPrecisionDatetime
)
blpapi_MessageFormatter_setValueInt32 = _blpapi_MessageFormatter_setValueInt32
blpapi_MessageFormatter_setValueInt64 = _blpapi_MessageFormatter_setValueInt64
blpapi_MessageFormatter_setValueNull = _blpapi_MessageFormatter_setValueNull
blpapi_MessageFormatter_setValueString = (
    _blpapi_MessageFormatter_setValueString
)
blpapi_MessageFormatter_getElement = _blpapi_MessageFormatter_getElement
blpapi_MessageIterator_create = _blpapi_MessageIterator_create
blpapi_MessageIterator_destroy = _blpapi_MessageIterator_destroy
blpapi_MessageIterator_next = _blpapi_MessageIterator_next
blpapi_MessageProperties_assign = _blpapi_MessageProperties_assign
blpapi_MessageProperties_copy = _blpapi_MessageProperties_copy
blpapi_MessageProperties_create = _blpapi_MessageProperties_create
blpapi_MessageProperties_destroy = _blpapi_MessageProperties_destroy
blpapi_MessageProperties_setCorrelationIds = (
    _blpapi_MessageProperties_setCorrelationIds
)
blpapi_MessageProperties_setRecapType = _blpapi_MessageProperties_setRecapType
blpapi_MessageProperties_setRequestId = _blpapi_MessageProperties_setRequestId
blpapi_MessageProperties_setService = _blpapi_MessageProperties_setService
blpapi_MessageProperties_setTimeReceived = (
    _blpapi_MessageProperties_setTimeReceived
)
blpapi_Message_addRef = _blpapi_Message_addRef
blpapi_Message_correlationId = _blpapi_Message_correlationId
blpapi_Message_elements = _blpapi_Message_elements
blpapi_Message_fragmentType = _blpapi_Message_fragmentType
blpapi_Message_getRequestId = _blpapi_Message_getRequestId
blpapi_Message_messageType = _blpapi_Message_messageType
blpapi_Message_numCorrelationIds = _blpapi_Message_numCorrelationIds
blpapi_Message_printHelper = _blpapi_Message_printHelper
blpapi_Message_recapType = _blpapi_Message_recapType
blpapi_Message_release = _blpapi_Message_release
blpapi_Message_service = _blpapi_Message_service
blpapi_Message_timeReceived = _blpapi_Message_timeReceived
blpapi_Message_topicName = _blpapi_Message_topicName
blpapi_Name_create = _blpapi_Name_create
blpapi_Name_destroy = _blpapi_Name_destroy
blpapi_Name_equalsStr = _blpapi_Name_equalsStr
blpapi_Name_findName = _blpapi_Name_findName
blpapi_Name_hasName = _blpapi_Name_hasName
blpapi_Name_length = _blpapi_Name_length
blpapi_Name_string = _blpapi_Name_string
blpapi_Operation_description = _blpapi_Operation_description
blpapi_Operation_name = _blpapi_Operation_name
blpapi_Operation_numResponseDefinitions = (
    _blpapi_Operation_numResponseDefinitions
)
blpapi_Operation_requestDefinition = _blpapi_Operation_requestDefinition
blpapi_Operation_responseDefinition = _blpapi_Operation_responseDefinition
blpapi_Operation_responseDefinitionFromName = (
    _blpapi_Operation_responseDefinitionFromName
)
blpapi_ProviderSession_activateSubServiceCodeRange = (
    _blpapi_ProviderSession_activateSubServiceCodeRange
)
blpapi_ProviderSession_createServiceStatusTopic = (
    _blpapi_ProviderSession_createServiceStatusTopic
)
blpapi_ProviderSession_createTopic = _blpapi_ProviderSession_createTopic
blpapi_ProviderSession_createTopics = _blpapi_ProviderSession_createTopics
blpapi_ProviderSession_createTopicsAsync = (
    _blpapi_ProviderSession_createTopicsAsync
)
blpapi_ProviderSession_deactivateSubServiceCodeRange = (
    _blpapi_ProviderSession_deactivateSubServiceCodeRange
)
blpapi_ProviderSession_deleteTopics = _blpapi_ProviderSession_deleteTopics
blpapi_ProviderSession_deregisterService = (
    _blpapi_ProviderSession_deregisterService
)
blpapi_ProviderSession_flushPublishedEvents = (
    _blpapi_ProviderSession_flushPublishedEvents
)
blpapi_ProviderSession_getAbstractSession = (
    _blpapi_ProviderSession_getAbstractSession
)
blpapi_ProviderSession_getTopic = _blpapi_ProviderSession_getTopic
blpapi_ProviderSession_nextEvent = _blpapi_ProviderSession_nextEvent
blpapi_ProviderSession_publish = _blpapi_ProviderSession_publish
blpapi_ProviderSession_registerService = (
    _blpapi_ProviderSession_registerService
)
blpapi_ProviderSession_registerServiceAsync = (
    _blpapi_ProviderSession_registerServiceAsync
)
blpapi_ProviderSession_resolve = _blpapi_ProviderSession_resolve
blpapi_ProviderSession_resolveAsync = _blpapi_ProviderSession_resolveAsync
blpapi_ProviderSession_sendResponse = _blpapi_ProviderSession_sendResponse
blpapi_ProviderSession_start = _blpapi_ProviderSession_start
blpapi_ProviderSession_startAsync = _blpapi_ProviderSession_startAsync
blpapi_ProviderSession_stop = _blpapi_ProviderSession_stop
blpapi_ProviderSession_stopAsync = _blpapi_ProviderSession_stopAsync
ProviderSession_terminateSubscriptionsOnTopic = (
    _blpapi_ProviderSession_terminateSubscriptionsOnTopic
)
blpapi_ProviderSession_terminateSubscriptionsOnTopics = (
    _blpapi_ProviderSession_terminateSubscriptionsOnTopics
)
blpapi_ProviderSession_tryNextEvent = _blpapi_ProviderSession_tryNextEvent
blpapi_RequestTemplate_release = _blpapi_RequestTemplate_release
blpapi_Request_destroy = _blpapi_Request_destroy
blpapi_Request_elements = _blpapi_Request_elements
blpapi_Request_getRequestId = _blpapi_Request_getRequestId
blpapi_Request_setPreferredRoute = _blpapi_Request_setPreferredRoute
blpapi_ResolutionList_add = _blpapi_ResolutionList_add
blpapi_ResolutionList_addAttribute = _blpapi_ResolutionList_addAttribute
blpapi_ResolutionList_addFromMessage = _blpapi_ResolutionList_addFromMessage
blpapi_ResolutionList_attribute = _blpapi_ResolutionList_attribute
blpapi_ResolutionList_attributeAt = _blpapi_ResolutionList_attributeAt
blpapi_ResolutionList_correlationIdAt = _blpapi_ResolutionList_correlationIdAt
blpapi_ResolutionList_create = _blpapi_ResolutionList_create
blpapi_ResolutionList_destroy = _blpapi_ResolutionList_destroy
blpapi_ResolutionList_extractAttributeFromResolutionSuccess = (
    _blpapi_ResolutionList_extractAttributeFromResolutionSuccess
)
blpapi_ResolutionList_message = _blpapi_ResolutionList_message
blpapi_ResolutionList_messageAt = _blpapi_ResolutionList_messageAt
blpapi_ResolutionList_size = _blpapi_ResolutionList_size
blpapi_ResolutionList_status = _blpapi_ResolutionList_status
blpapi_ResolutionList_statusAt = _blpapi_ResolutionList_statusAt
blpapi_ResolutionList_topicString = _blpapi_ResolutionList_topicString
blpapi_ResolutionList_topicStringAt = _blpapi_ResolutionList_topicStringAt
blpapi_SchemaElementDefinition_description = (
    _blpapi_SchemaElementDefinition_description
)
blpapi_SchemaElementDefinition_getAlternateName = (
    _blpapi_SchemaElementDefinition_getAlternateName
)
blpapi_SchemaElementDefinition_maxValues = (
    _blpapi_SchemaElementDefinition_maxValues
)
blpapi_SchemaElementDefinition_minValues = (
    _blpapi_SchemaElementDefinition_minValues
)
blpapi_SchemaElementDefinition_name = _blpapi_SchemaElementDefinition_name
blpapi_SchemaElementDefinition_numAlternateNames = (
    _blpapi_SchemaElementDefinition_numAlternateNames
)
blpapi_SchemaElementDefinition_printHelper = (
    _blpapi_SchemaElementDefinition_printHelper
)
blpapi_SchemaElementDefinition_status = _blpapi_SchemaElementDefinition_status
blpapi_SchemaElementDefinition_type = _blpapi_SchemaElementDefinition_type
blpapi_SchemaTypeDefinition_datatype = _blpapi_SchemaTypeDefinition_datatype
blpapi_SchemaTypeDefinition_description = (
    _blpapi_SchemaTypeDefinition_description
)
blpapi_SchemaTypeDefinition_enumeration = (
    _blpapi_SchemaTypeDefinition_enumeration
)
blpapi_SchemaTypeDefinition_getElementDefinition = (
    _blpapi_SchemaTypeDefinition_getElementDefinition
)
blpapi_SchemaTypeDefinition_getElementDefinitionAt = (
    _blpapi_SchemaTypeDefinition_getElementDefinitionAt
)
blpapi_SchemaTypeDefinition_hasElementDefinition = (
    _blpapi_SchemaTypeDefinition_hasElementDefinition
)
blpapi_SchemaTypeDefinition_isComplexType = (
    _blpapi_SchemaTypeDefinition_isComplexType
)
blpapi_SchemaTypeDefinition_isEnumerationType = (
    _blpapi_SchemaTypeDefinition_isEnumerationType
)
blpapi_SchemaTypeDefinition_isSimpleType = (
    _blpapi_SchemaTypeDefinition_isSimpleType
)
blpapi_SchemaTypeDefinition_name = _blpapi_SchemaTypeDefinition_name
blpapi_SchemaTypeDefinition_numElementDefinitions = (
    _blpapi_SchemaTypeDefinition_numElementDefinitions
)
blpapi_SchemaTypeDefinition_printHelper = (
    _blpapi_SchemaTypeDefinition_printHelper
)
blpapi_SchemaTypeDefinition_status = _blpapi_SchemaTypeDefinition_status
blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange = (
    _blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange
)
blpapi_ServiceRegistrationOptions_copy = (
    _blpapi_ServiceRegistrationOptions_copy
)
blpapi_ServiceRegistrationOptions_create = (
    _blpapi_ServiceRegistrationOptions_create
)
blpapi_ServiceRegistrationOptions_destroy = (
    _blpapi_ServiceRegistrationOptions_destroy
)
blpapi_ServiceRegistrationOptions_duplicate = (
    _blpapi_ServiceRegistrationOptions_duplicate
)
blpapi_ServiceRegistrationOptions_getGroupId = (
    _blpapi_ServiceRegistrationOptions_getGroupId
)
blpapi_ServiceRegistrationOptions_getPartsToRegister = (
    _blpapi_ServiceRegistrationOptions_getPartsToRegister
)
blpapi_ServiceRegistrationOptions_getServicePriority = (
    _blpapi_ServiceRegistrationOptions_getServicePriority
)
blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges = (
    _blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges
)
blpapi_ServiceRegistrationOptions_setGroupId = (
    _blpapi_ServiceRegistrationOptions_setGroupId
)
blpapi_ServiceRegistrationOptions_setPartsToRegister = (
    _blpapi_ServiceRegistrationOptions_setPartsToRegister
)
blpapi_ServiceRegistrationOptions_setServicePriority = (
    _blpapi_ServiceRegistrationOptions_setServicePriority
)
blpapi_Service_addRef = _blpapi_Service_addRef
blpapi_Service_authorizationServiceName = (
    _blpapi_Service_authorizationServiceName
)
blpapi_Service_createAdminEvent = _blpapi_Service_createAdminEvent
blpapi_Service_createAuthorizationRequest = (
    _blpapi_Service_createAuthorizationRequest
)
blpapi_Service_createPublishEvent = _blpapi_Service_createPublishEvent
blpapi_Service_createRequest = _blpapi_Service_createRequest
blpapi_Service_createResponseEvent = _blpapi_Service_createResponseEvent
blpapi_Service_description = _blpapi_Service_description
blpapi_Service_getEventDefinition = _blpapi_Service_getEventDefinition
blpapi_Service_getEventDefinitionAt = _blpapi_Service_getEventDefinitionAt
blpapi_Service_getOperation = _blpapi_Service_getOperation
blpapi_Service_getOperationAt = _blpapi_Service_getOperationAt
blpapi_Service_hasEventDefinition = _blpapi_Service_hasEventDefinition
blpapi_Service_hasOperation = _blpapi_Service_hasOperation
blpapi_Service_name = _blpapi_Service_name
blpapi_Service_numEventDefinitions = _blpapi_Service_numEventDefinitions
blpapi_Service_numOperations = _blpapi_Service_numOperations
blpapi_Service_printHelper = _blpapi_Service_printHelper
blpapi_Service_release = _blpapi_Service_release
blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg = (
    _blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg
)
blpapi_SessionOptions_applicationIdentityKey = (
    _blpapi_SessionOptions_applicationIdentityKey
)
blpapi_SessionOptions_authenticationOptions = (
    _blpapi_SessionOptions_authenticationOptions
)
blpapi_SessionOptions_autoRestartOnDisconnection = (
    _blpapi_SessionOptions_autoRestartOnDisconnection
)
blpapi_SessionOptions_bandwidthSaveModeDisabled = (
    _blpapi_SessionOptions_bandwidthSaveModeDisabled
)
blpapi_SessionOptions_clientMode = _blpapi_SessionOptions_clientMode
blpapi_SessionOptions_connectTimeout = _blpapi_SessionOptions_connectTimeout
blpapi_SessionOptions_create = _blpapi_SessionOptions_create
blpapi_SessionOptions_defaultKeepAliveInactivityTime = (
    _blpapi_SessionOptions_defaultKeepAliveInactivityTime
)
blpapi_SessionOptions_defaultKeepAliveResponseTimeout = (
    _blpapi_SessionOptions_defaultKeepAliveResponseTimeout
)
blpapi_SessionOptions_defaultServices = _blpapi_SessionOptions_defaultServices
blpapi_SessionOptions_defaultSubscriptionService = (
    _blpapi_SessionOptions_defaultSubscriptionService
)
blpapi_SessionOptions_defaultTopicPrefix = (
    _blpapi_SessionOptions_defaultTopicPrefix
)
blpapi_SessionOptions_destroy = _blpapi_SessionOptions_destroy
blpapi_SessionOptions_flushPublishedEventsTimeout = (
    _blpapi_SessionOptions_flushPublishedEventsTimeout
)
blpapi_SessionOptions_getServerAddressWithProxy = (
    _blpapi_SessionOptions_getServerAddressWithProxy
)
blpapi_SessionOptions_keepAliveEnabled = (
    _blpapi_SessionOptions_keepAliveEnabled
)
blpapi_SessionOptions_maxEventQueueSize = (
    _blpapi_SessionOptions_maxEventQueueSize
)
blpapi_SessionOptions_maxPendingRequests = (
    _blpapi_SessionOptions_maxPendingRequests
)
blpapi_SessionOptions_numServerAddresses = (
    _blpapi_SessionOptions_numServerAddresses
)
blpapi_SessionOptions_numStartAttempts = (
    _blpapi_SessionOptions_numStartAttempts
)
blpapi_SessionOptions_printHelper = _blpapi_SessionOptions_printHelper
blpapi_SessionOptions_recordSubscriptionDataReceiveTimes = (
    _blpapi_SessionOptions_recordSubscriptionDataReceiveTimes
)
blpapi_SessionOptions_removeServerAddress = (
    _blpapi_SessionOptions_removeServerAddress
)
blpapi_SessionOptions_serverHost = _blpapi_SessionOptions_serverHost
blpapi_SessionOptions_serverPort = _blpapi_SessionOptions_serverPort
blpapi_SessionOptions_serviceCheckTimeout = (
    _blpapi_SessionOptions_serviceCheckTimeout
)
blpapi_SessionOptions_serviceDownloadTimeout = (
    _blpapi_SessionOptions_serviceDownloadTimeout
)
blpapi_SessionOptions_sessionName = _blpapi_SessionOptions_sessionName
blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg = (
    _blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg
)
blpapi_SessionOptions_setApplicationIdentityKey = (
    _blpapi_SessionOptions_setApplicationIdentityKey
)
blpapi_SessionOptions_setAuthenticationOptions = (
    _blpapi_SessionOptions_setAuthenticationOptions
)
blpapi_SessionOptions_setAutoRestartOnDisconnection = (
    _blpapi_SessionOptions_setAutoRestartOnDisconnection
)
blpapi_SessionOptions_setBandwidthSaveModeDisabled = (
    _blpapi_SessionOptions_setBandwidthSaveModeDisabled
)
blpapi_SessionOptions_setClientMode = _blpapi_SessionOptions_setClientMode
blpapi_SessionOptions_setConnectTimeout = (
    _blpapi_SessionOptions_setConnectTimeout
)
blpapi_SessionOptions_setDefaultKeepAliveInactivityTime = (
    _blpapi_SessionOptions_setDefaultKeepAliveInactivityTime
)
blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout = (
    _blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout
)
blpapi_SessionOptions_setDefaultServices = (
    _blpapi_SessionOptions_setDefaultServices
)
blpapi_SessionOptions_setDefaultSubscriptionService = (
    _blpapi_SessionOptions_setDefaultSubscriptionService
)
blpapi_SessionOptions_setDefaultTopicPrefix = (
    _blpapi_SessionOptions_setDefaultTopicPrefix
)
blpapi_SessionOptions_setFlushPublishedEventsTimeout = (
    _blpapi_SessionOptions_setFlushPublishedEventsTimeout
)
blpapi_SessionOptions_setKeepAliveEnabled = (
    _blpapi_SessionOptions_setKeepAliveEnabled
)
blpapi_SessionOptions_setMaxEventQueueSize = (
    _blpapi_SessionOptions_setMaxEventQueueSize
)
blpapi_SessionOptions_setMaxPendingRequests = (
    _blpapi_SessionOptions_setMaxPendingRequests
)
blpapi_SessionOptions_setNumStartAttempts = (
    _blpapi_SessionOptions_setNumStartAttempts
)
blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes = (
    _blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes
)
blpapi_SessionOptions_setServerAddress = (
    _blpapi_SessionOptions_setServerAddress
)
blpapi_SessionOptions_setServerAddressWithProxy = (
    _blpapi_SessionOptions_setServerAddressWithProxy
)
blpapi_SessionOptions_setServerHost = _blpapi_SessionOptions_setServerHost
blpapi_SessionOptions_setServerPort = _blpapi_SessionOptions_setServerPort
blpapi_SessionOptions_setServiceCheckTimeout = (
    _blpapi_SessionOptions_setServiceCheckTimeout
)
blpapi_SessionOptions_setServiceDownloadTimeout = (
    _blpapi_SessionOptions_setServiceDownloadTimeout
)
blpapi_SessionOptions_setSessionIdentityOptions = (
    _blpapi_SessionOptions_setSessionIdentityOptions
)
blpapi_SessionOptions_setSessionName = _blpapi_SessionOptions_setSessionName
blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark = (
    _blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark
)
blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark = (
    _blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark
)
blpapi_SessionOptions_setTlsOptions = _blpapi_SessionOptions_setTlsOptions
blpapi_SessionOptions_slowConsumerWarningHiWaterMark = (
    _blpapi_SessionOptions_slowConsumerWarningHiWaterMark
)
blpapi_SessionOptions_slowConsumerWarningLoWaterMark = (
    _blpapi_SessionOptions_slowConsumerWarningLoWaterMark
)
blpapi_Session_createSnapshotRequestTemplate = (
    _blpapi_Session_createSnapshotRequestTemplate
)
blpapi_Session_getAbstractSession = _blpapi_Session_getAbstractSession
blpapi_Session_nextEvent = _blpapi_Session_nextEvent
blpapi_Session_resubscribe = _blpapi_Session_resubscribe
blpapi_Session_resubscribeEx = _blpapi_Session_resubscribeEx
blpapi_Session_resubscribeEx_helper = _blpapi_Session_resubscribeEx_helper
blpapi_Session_resubscribeWithId = _blpapi_Session_resubscribeWithId
blpapi_Session_resubscribeWithIdEx = _blpapi_Session_resubscribeWithIdEx
blpapi_Session_resubscribeWithIdEx_helper = (
    _blpapi_Session_resubscribeWithIdEx_helper
)
blpapi_Session_sendRequest = _blpapi_Session_sendRequest
blpapi_Session_sendRequestTemplate = _blpapi_Session_sendRequestTemplate
blpapi_Session_setStatusCorrelationId = _blpapi_Session_setStatusCorrelationId
blpapi_Session_start = _blpapi_Session_start
blpapi_Session_startAsync = _blpapi_Session_startAsync
blpapi_Session_stop = _blpapi_Session_stop
blpapi_Session_stopAsync = _blpapi_Session_stopAsync
blpapi_Session_subscribe = _blpapi_Session_subscribe
blpapi_Session_subscribeEx = _blpapi_Session_subscribeEx
blpapi_Session_subscribeEx_helper = _blpapi_Session_subscribeEx_helper
blpapi_Session_tryNextEvent = _blpapi_Session_tryNextEvent
blpapi_Session_unsubscribe = _blpapi_Session_unsubscribe
blpapi_Socks5Config_create = _blpapi_Socks5Config_create
blpapi_Socks5Config_destroy = _blpapi_Socks5Config_destroy
blpapi_Socks5Config_printHelper = _blpapi_Socks5Config_printHelper
blpapi_SubscriptionList_addHelper = _blpapi_SubscriptionList_addHelper
blpapi_SubscriptionList_addResolved = _blpapi_SubscriptionList_addResolved
blpapi_SubscriptionList_append = _blpapi_SubscriptionList_append
blpapi_SubscriptionList_clear = _blpapi_SubscriptionList_clear
blpapi_SubscriptionList_correlationIdAt = (
    _blpapi_SubscriptionList_correlationIdAt
)
blpapi_SubscriptionList_create = _blpapi_SubscriptionList_create
blpapi_SubscriptionList_destroy = _blpapi_SubscriptionList_destroy
blpapi_SubscriptionList_isResolvedAt = _blpapi_SubscriptionList_isResolvedAt
blpapi_SubscriptionList_size = _blpapi_SubscriptionList_size
blpapi_SubscriptionList_topicStringAt = _blpapi_SubscriptionList_topicStringAt
blpapi_TestUtil_appendMessage = _blpapi_TestUtil_appendMessage
blpapi_TestUtil_createEvent = _blpapi_TestUtil_createEvent
blpapi_TestUtil_createTopic = _blpapi_TestUtil_createTopic
blpapi_TestUtil_deserializeService = _blpapi_TestUtil_deserializeService
blpapi_TestUtil_getAdminMessageDefinition = (
    _blpapi_TestUtil_getAdminMessageDefinition
)
blpapi_TestUtil_serializeServiceHelper = (
    _blpapi_TestUtil_serializeServiceHelper
)
blpapi_TimePoint = TimePoint
blpapi_TimePointUtil_nanosecondsBetween = (
    _blpapi_TimePointUtil_nanosecondsBetween
)
blpapi_TlsOptions_createFromBlobs = _blpapi_TlsOptions_createFromBlobs
blpapi_TlsOptions_createFromFiles = _blpapi_TlsOptions_createFromFiles
blpapi_TlsOptions_destroy = _blpapi_TlsOptions_destroy
blpapi_TlsOptions_setCrlFetchTimeoutMs = (
    _blpapi_TlsOptions_setCrlFetchTimeoutMs
)
blpapi_TlsOptions_setTlsHandshakeTimeoutMs = (
    _blpapi_TlsOptions_setTlsHandshakeTimeoutMs
)
blpapi_TopicList_add = _blpapi_TopicList_add
blpapi_TopicList_addFromMessage = _blpapi_TopicList_addFromMessage
blpapi_TopicList_correlationIdAt = _blpapi_TopicList_correlationIdAt
blpapi_TopicList_create = _blpapi_TopicList_create
blpapi_TopicList_createFromResolutionList = (
    _blpapi_TopicList_createFromResolutionList
)
blpapi_TopicList_destroy = _blpapi_TopicList_destroy
blpapi_TopicList_message = _blpapi_TopicList_message
blpapi_TopicList_messageAt = _blpapi_TopicList_messageAt
blpapi_TopicList_size = _blpapi_TopicList_size
blpapi_TopicList_status = _blpapi_TopicList_status
blpapi_TopicList_statusAt = _blpapi_TopicList_statusAt
blpapi_TopicList_topicString = _blpapi_TopicList_topicString
blpapi_TopicList_topicStringAt = _blpapi_TopicList_topicStringAt
blpapi_Topic_compare = _blpapi_Topic_compare
blpapi_Topic_create = _blpapi_Topic_create
blpapi_Topic_destroy = _blpapi_Topic_destroy
blpapi_Topic_isActive = _blpapi_Topic_isActive
blpapi_Topic_service = _blpapi_Topic_service
blpapi_UserAgentInfo_setUserTaskName = _blpapi_UserAgentInfo_setUserTaskName
blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion = (
    _blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion
)
blpapi_ZfpUtil_getOptionsForLeasedLines = (
    _blpapi_ZfpUtil_getOptionsForLeasedLines
)
blpapi_getLastErrorDescription = _blpapi_getLastErrorDescription
blpapi_getVersionInfo = _blpapi_getVersionInfo
ProviderSession_createHelper = _ProviderSession_createHelper
ProviderSession_destroyHelper = _ProviderSession_destroyHelper
Session_createHelper = _Session_createHelper
Session_destroyHelper = _Session_destroyHelper


def _test_function_signatures():
    _C_TO_PY = {
        "char": c_char,
        "double": c_double,
        "float": c_float,
        "int": c_int,
        "int*": POINTER(c_int),
        "size_t": c_size_t,
        "unsigned int": c_uint,
        "blpapi_CorrelationId_t": CidStruct,
        "blpapi_StreamWriter_t": blpapi_StreamWriter_t,
    }

    def c_type_to_ctypes(ctype: str):
        pt = _C_TO_PY.get(ctype, None)
        if pt is not None:
            return pt
        if "char" in ctype:
            return c_char_p
        elif "*" in ctype:
            return c_void_p
        return None

    def verify_ctypes(fnc, ret: str, args: List[str]):
        f = globals().get("l_" + fnc, None)  # find in local module
        if f is None:
            # this if fine, not yet impl
            return

        if f.restype != c_type_to_ctypes(ret):
            raise ImportError(
                f"Return type for '{fnc}' is '{ret}', but restype set to '{f.restype}'"
            )

        if f.argtypes is None:
            # OK, for now, not all have it
            return

        assert len(f.argtypes) == len(args)
        for pyarg, carg in zip(f.argtypes, args):
            if pyarg != c_type_to_ctypes(carg):
                raise ImportError(
                    f"Argument type for '{fnc}' is '{carg}' but set to '{pyarg}'"
                )

    verify_ctypes(
        fnc="blpapi_AbstractSession_cancel",
        ret="int",
        args=[
            "blpapi_AbstractSession_t*",
            "blpapi_CorrelationId_t*",
            "size_t",
            "char*",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_createIdentity",
        ret="blpapi_Identity_t *",
        args=["blpapi_AbstractSession_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_generateAuthorizedIdentityAsync",
        ret="int",
        args=[
            "blpapi_AbstractSession_t*",
            "blpapi_AuthOptions_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_generateManualToken",
        ret="int",
        args=[
            "blpapi_AbstractSession_t*",
            "blpapi_CorrelationId_t*",
            "char*",
            "char*",
            "blpapi_EventQueue_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_generateToken",
        ret="int",
        args=[
            "blpapi_AbstractSession_t*",
            "blpapi_CorrelationId_t*",
            "blpapi_EventQueue_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_getAuthorizedIdentity",
        ret="int",
        args=[
            "blpapi_AbstractSession_t*",
            "blpapi_CorrelationId_t*",
            "blpapi_Identity_t**",
        ],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_getService",
        ret="int",
        args=["blpapi_AbstractSession_t*", "blpapi_Service_t**", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_openService",
        ret="int",
        args=["blpapi_AbstractSession_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_openServiceAsync",
        ret="int",
        args=["blpapi_AbstractSession_t*", "char*", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AbstractSession_sessionName",
        ret="int",
        args=["blpapi_AbstractSession_t*", "char**", "size_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthApplication_copy",
        ret="int",
        args=["blpapi_AuthApplication_t*", "blpapi_AuthApplication_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthApplication_create",
        ret="int",
        args=["blpapi_AuthApplication_t**", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthApplication_destroy",
        ret="void",
        args=["blpapi_AuthApplication_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthApplication_duplicate",
        ret="int",
        args=["blpapi_AuthApplication_t**", "blpapi_AuthApplication_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_copy",
        ret="int",
        args=["blpapi_AuthOptions_t*", "blpapi_AuthOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_create_default",
        ret="int",
        args=["blpapi_AuthOptions_t**"],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_create_forAppMode",
        ret="int",
        args=["blpapi_AuthOptions_t**", "blpapi_AuthApplication_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_create_forToken",
        ret="int",
        args=["blpapi_AuthOptions_t**", "blpapi_AuthToken_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_create_forUserAndAppMode",
        ret="int",
        args=[
            "blpapi_AuthOptions_t**",
            "blpapi_AuthUser_t*",
            "blpapi_AuthApplication_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_create_forUserMode",
        ret="int",
        args=["blpapi_AuthOptions_t**", "blpapi_AuthUser_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_destroy",
        ret="void",
        args=["blpapi_AuthOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthOptions_duplicate",
        ret="int",
        args=["blpapi_AuthOptions_t**", "blpapi_AuthOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthToken_copy",
        ret="int",
        args=["blpapi_AuthToken_t*", "blpapi_AuthToken_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthToken_create",
        ret="int",
        args=["blpapi_AuthToken_t**", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthToken_destroy",
        ret="void",
        args=["blpapi_AuthToken_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthToken_duplicate",
        ret="int",
        args=["blpapi_AuthToken_t**", "blpapi_AuthToken_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthUser_copy",
        ret="int",
        args=["blpapi_AuthUser_t*", "blpapi_AuthUser_t*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthUser_createWithActiveDirectoryProperty",
        ret="int",
        args=["blpapi_AuthUser_t**", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthUser_createWithLogonName",
        ret="int",
        args=["blpapi_AuthUser_t**"],
    )
    verify_ctypes(
        fnc="blpapi_AuthUser_createWithManualOptions",
        ret="int",
        args=["blpapi_AuthUser_t**", "char*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_AuthUser_destroy", ret="void", args=["blpapi_AuthUser_t*"]
    )
    verify_ctypes(
        fnc="blpapi_AuthUser_duplicate",
        ret="int",
        args=["blpapi_AuthUser_t**", "blpapi_AuthUser_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ConstantList_datatype",
        ret="int",
        args=["blpapi_ConstantList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ConstantList_description",
        ret="char *",
        args=["blpapi_ConstantList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ConstantList_getConstant",
        ret="blpapi_Constant_t *",
        args=["blpapi_ConstantList_t*", "char*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ConstantList_getConstantAt",
        ret="blpapi_Constant_t *",
        args=["blpapi_ConstantList_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_ConstantList_name",
        ret="blpapi_Name_t *",
        args=["blpapi_ConstantList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ConstantList_numConstants",
        ret="int",
        args=["blpapi_ConstantList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ConstantList_status",
        ret="int",
        args=["blpapi_ConstantList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_datatype", ret="int", args=["blpapi_Constant_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Constant_description",
        ret="char *",
        args=["blpapi_Constant_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_getValueAsChar",
        ret="int",
        args=["blpapi_Constant_t*", "blpapi_Char_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_getValueAsDatetime",
        ret="int",
        args=["blpapi_Constant_t*", "blpapi_Datetime_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_getValueAsFloat32",
        ret="int",
        args=["blpapi_Constant_t*", "blpapi_Float32_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_getValueAsFloat64",
        ret="int",
        args=["blpapi_Constant_t*", "blpapi_Float64_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_getValueAsInt32",
        ret="int",
        args=["blpapi_Constant_t*", "blpapi_Int32_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_getValueAsInt64",
        ret="int",
        args=["blpapi_Constant_t*", "blpapi_Int64_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_getValueAsString",
        ret="int",
        args=["blpapi_Constant_t*", "char**"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_name",
        ret="blpapi_Name_t *",
        args=["blpapi_Constant_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Constant_status", ret="int", args=["blpapi_Constant_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Element_appendElement",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Element_t**"],
    )
    verify_ctypes(
        fnc="blpapi_Element_datatype", ret="int", args=["blpapi_Element_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Element_definition",
        ret="blpapi_SchemaElementDefinition_t *",
        args=["blpapi_Element_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getChoice",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Element_t**"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getElement",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Element_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getElementAt",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Element_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsBool",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Bool_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsBytes",
        ret="int",
        args=["blpapi_Element_t*", "char**", "size_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsChar",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Char_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsDatetime",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Datetime_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsElement",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Element_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsFloat64",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Float64_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsHighPrecisionDatetime",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "blpapi_HighPrecisionDatetime_t*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsInt32",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Int32_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsInt64",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Int64_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsName",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Name_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_getValueAsString",
        ret="int",
        args=["blpapi_Element_t*", "char**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_hasElementEx",
        ret="int",
        args=["blpapi_Element_t*", "char*", "blpapi_Name_t*", "int", "int"],
    )
    verify_ctypes(
        fnc="blpapi_Element_isArray", ret="int", args=["blpapi_Element_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Element_isComplexType",
        ret="int",
        args=["blpapi_Element_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_isNull",
        ret="int",
        args=["blpapi_Element_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_isNullValue",
        ret="int",
        args=["blpapi_Element_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_isReadOnly", ret="int", args=["blpapi_Element_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Element_name",
        ret="blpapi_Name_t *",
        args=["blpapi_Element_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_nameString",
        ret="char *",
        args=["blpapi_Element_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_numElements",
        ret="size_t",
        args=["blpapi_Element_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_numValues",
        ret="size_t",
        args=["blpapi_Element_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setChoice",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "blpapi_Element_t**",
            "char*",
            "blpapi_Name_t*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementBool",
        ret="int",
        args=["blpapi_Element_t*", "char*", "blpapi_Name_t*", "blpapi_Bool_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementBytes",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "char*",
            "blpapi_Name_t*",
            "char*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementFloat",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Float32_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementFromName",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Name_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementHighPrecisionDatetime",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_HighPrecisionDatetime_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementInt32",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Int32_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementInt64",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Int64_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setElementString",
        ret="int",
        args=["blpapi_Element_t*", "char*", "blpapi_Name_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueBool",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Bool_t", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueBytes",
        ret="int",
        args=["blpapi_Element_t*", "char*", "size_t", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueFloat",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Float32_t", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueFromName",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Name_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueHighPrecisionDatetime",
        ret="int",
        args=[
            "blpapi_Element_t*",
            "blpapi_HighPrecisionDatetime_t*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueInt32",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Int32_t", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueInt64",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_Int64_t", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_setValueString",
        ret="int",
        args=["blpapi_Element_t*", "char*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Element_toJson",
        ret="int",
        args=["blpapi_Element_t*", "blpapi_StreamWriter_t", "void*"],
    )
    verify_ctypes(
        fnc="blpapi_Element_fromJson",
        ret="int",
        args=["blpapi_Element_t*", "char const *"],
    )
    verify_ctypes(
        fnc="blpapi_EventDispatcher_create",
        ret="blpapi_EventDispatcher_t *",
        args=["size_t"],
    )
    verify_ctypes(
        fnc="blpapi_EventDispatcher_destroy",
        ret="void",
        args=["blpapi_EventDispatcher_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventDispatcher_start",
        ret="int",
        args=["blpapi_EventDispatcher_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventDispatcher_stop",
        ret="int",
        args=["blpapi_EventDispatcher_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendElement",
        ret="int",
        args=["blpapi_EventFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendFragmentedRecapMessage",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Topic_t*",
            "blpapi_CorrelationId_t*",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendFragmentedRecapMessageSeq",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Topic_t*",
            "int",
            "unsigned int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendMessage",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Topic_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendMessageSeq",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Topic_t*",
            "unsigned int",
            "unsigned",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendRecapMessage",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "blpapi_Topic_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendRecapMessageSeq",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "blpapi_Topic_t*",
            "blpapi_CorrelationId_t*",
            "unsigned int",
            "unsigned",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendResponse",
        ret="int",
        args=["blpapi_EventFormatter_t*", "char*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueBool",
        ret="int",
        args=["blpapi_EventFormatter_t*", "blpapi_Bool_t"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueChar",
        ret="int",
        args=["blpapi_EventFormatter_t*", "char"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueFloat",
        ret="int",
        args=["blpapi_EventFormatter_t*", "blpapi_Float32_t"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueFromName",
        ret="int",
        args=["blpapi_EventFormatter_t*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueHighPrecisionDatetime",
        ret="int",
        args=["blpapi_EventFormatter_t*", "blpapi_HighPrecisionDatetime_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueInt32",
        ret="int",
        args=["blpapi_EventFormatter_t*", "blpapi_Int32_t"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueInt64",
        ret="int",
        args=["blpapi_EventFormatter_t*", "blpapi_Int64_t"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_appendValueString",
        ret="int",
        args=["blpapi_EventFormatter_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_create",
        ret="blpapi_EventFormatter_t *",
        args=["blpapi_Event_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_destroy",
        ret="void",
        args=["blpapi_EventFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_popElement",
        ret="int",
        args=["blpapi_EventFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_getElement",
        ret="int",
        args=["blpapi_EventFormatter_t*", "blpapi_Element_t**"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_pushElement",
        ret="int",
        args=["blpapi_EventFormatter_t*", "char*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueBool",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Bool_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueBytes",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "char*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueChar",
        ret="int",
        args=["blpapi_EventFormatter_t*", "char*", "blpapi_Name_t*", "char"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueFloat",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Float32_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueFromName",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Name_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueHighPrecisionDatetime",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_HighPrecisionDatetime_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueInt32",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Int32_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueInt64",
        ret="int",
        args=[
            "blpapi_EventFormatter_t*",
            "char*",
            "blpapi_Name_t*",
            "blpapi_Int64_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueNull",
        ret="int",
        args=["blpapi_EventFormatter_t*", "char*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventFormatter_setValueString",
        ret="int",
        args=["blpapi_EventFormatter_t*", "char*", "blpapi_Name_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_EventQueue_create", ret="blpapi_EventQueue_t *", args=[""]
    )
    verify_ctypes(
        fnc="blpapi_EventQueue_destroy",
        ret="int",
        args=["blpapi_EventQueue_t*"],
    )
    verify_ctypes(
        fnc="blpapi_EventQueue_nextEvent",
        ret="blpapi_Event_t *",
        args=["blpapi_EventQueue_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_getElement",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Element_t**"],
    )
    verify_ctypes(
        fnc="blpapi_EventQueue_purge", ret="int", args=["blpapi_EventQueue_t*"]
    )
    verify_ctypes(
        fnc="blpapi_EventQueue_tryNextEvent",
        ret="int",
        args=["blpapi_EventQueue_t*", "blpapi_Event_t**"],
    )
    verify_ctypes(
        fnc="blpapi_Event_eventType", ret="int", args=["blpapi_Event_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Event_release", ret="int", args=["blpapi_Event_t*"]
    )
    verify_ctypes(
        fnc="blpapi_HighPrecisionDatetime_compare",
        ret="int",
        args=[
            "blpapi_HighPrecisionDatetime_t*",
            "blpapi_HighPrecisionDatetime_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_HighPrecisionDatetime_fromTimePoint",
        ret="int",
        args=[
            "blpapi_HighPrecisionDatetime_t*",
            "blpapi_TimePoint_t*",
            "short",
        ],
    )
    verify_ctypes(
        fnc="blpapi_HighPrecisionDatetime_print",
        ret="int",
        args=[
            "blpapi_HighPrecisionDatetime_t*",
            "blpapi_StreamWriter_t",
            "void*",
            "int",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_HighResolutionClock_now",
        ret="int",
        args=["blpapi_TimePoint_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Identity_addRef", ret="int", args=["blpapi_Identity_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Identity_getSeatType",
        ret="int",
        args=["blpapi_Identity_t*", "int*"],
    )
    verify_ctypes(
        fnc="blpapi_Identity_hasEntitlements",
        ret="int",
        args=[
            "blpapi_Identity_t*",
            "blpapi_Service_t*",
            "blpapi_Element_t*",
            "int*",
            "size_t",
            "int*",
            "int*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Identity_isAuthorized",
        ret="int",
        args=["blpapi_Identity_t*", "blpapi_Service_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Identity_release", ret="void", args=["blpapi_Identity_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Logging_logTestMessage",
        ret="void",
        args=["blpapi_Logging_Severity_t"],
    )
    verify_ctypes(
        fnc="blpapi_Logging_registerCallback",
        ret="int",
        args=["funct", "blpapi_Logging_Severity_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_FormatMessageJson",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_FormatMessageXml",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendElement",
        ret="int",
        args=["blpapi_MessageFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueBool",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Bool_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueChar",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "char"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueDatetime",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Datetime_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueFloat",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Float32_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueFloat32",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Float32_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueFloat64",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Float64_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueFromName",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueHighPrecisionDatetime",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_HighPrecisionDatetime_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueInt32",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Int32_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueInt64",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Int64_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_appendValueString",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_assign",
        ret="int",
        args=["blpapi_MessageFormatter_t**", "blpapi_MessageFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_copy",
        ret="int",
        args=["blpapi_MessageFormatter_t**", "blpapi_MessageFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_destroy",
        ret="int",
        args=["blpapi_MessageFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_popElement",
        ret="int",
        args=["blpapi_MessageFormatter_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_pushElement",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueBool",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Name_t*", "blpapi_Bool_t"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueBytes",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "char*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueChar",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Name_t*", "char"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueDatetime",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_Datetime_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueFloat",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_Float32_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueFloat32",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_Float32_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueFloat64",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_Float64_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueFromName",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_Name_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueHighPrecisionDatetime",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_HighPrecisionDatetime_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueInt32",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_Int32_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueInt64",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t*",
            "blpapi_Name_t*",
            "blpapi_Int64_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueNull",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageFormatter_setValueString",
        ret="int",
        args=["blpapi_MessageFormatter_t*", "blpapi_Name_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageIterator_create",
        ret="blpapi_MessageIterator_t *",
        args=["blpapi_Event_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageIterator_destroy",
        ret="void",
        args=["blpapi_MessageIterator_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageIterator_next",
        ret="int",
        args=["blpapi_MessageIterator_t*", "blpapi_Message_t**"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_assign",
        ret="int",
        args=["blpapi_MessageProperties_t*", "blpapi_MessageProperties_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_copy",
        ret="int",
        args=["blpapi_MessageProperties_t**", "blpapi_MessageProperties_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_create",
        ret="int",
        args=["blpapi_MessageProperties_t**"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_destroy",
        ret="void",
        args=["blpapi_MessageProperties_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_setCorrelationIds",
        ret="int",
        args=[
            "blpapi_MessageProperties_t*",
            "blpapi_CorrelationId_t*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_setRecapType",
        ret="int",
        args=["blpapi_MessageProperties_t*", "int", "int"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_setRequestId",
        ret="int",
        args=["blpapi_MessageProperties_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_setService",
        ret="int",
        args=["blpapi_MessageProperties_t*", "blpapi_Service_t*"],
    )
    verify_ctypes(
        fnc="blpapi_MessageProperties_setTimeReceived",
        ret="int",
        args=[
            "blpapi_MessageProperties_t*",
            "blpapi_HighPrecisionDatetime_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Message_addRef", ret="int", args=["blpapi_Message_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Message_correlationId",
        ret="blpapi_CorrelationId_t",
        args=["blpapi_Message_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Message_elements",
        ret="blpapi_Element_t *",
        args=["blpapi_Message_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Message_fragmentType",
        ret="int",
        args=["blpapi_Message_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Message_getRequestId",
        ret="int",
        args=["blpapi_Message_t*", "char**"],
    )
    verify_ctypes(
        fnc="blpapi_Message_messageType",
        ret="blpapi_Name_t *",
        args=["blpapi_Message_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Message_numCorrelationIds",
        ret="int",
        args=["blpapi_Message_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Message_recapType", ret="int", args=["blpapi_Message_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Message_release", ret="int", args=["blpapi_Message_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Message_service",
        ret="blpapi_Service_t *",
        args=["blpapi_Message_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Message_timeReceived",
        ret="int",
        args=["blpapi_Message_t*", "blpapi_TimePoint_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Message_topicName",
        ret="char *",
        args=["blpapi_Message_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Name_create", ret="blpapi_Name_t *", args=["char*"]
    )
    verify_ctypes(
        fnc="blpapi_Name_destroy", ret="void", args=["blpapi_Name_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Name_equalsStr",
        ret="int",
        args=["blpapi_Name_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_Name_findName", ret="blpapi_Name_t *", args=["char*"]
    )
    verify_ctypes(
        fnc="blpapi_Name_length", ret="size_t", args=["blpapi_Name_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Name_string", ret="char *", args=["blpapi_Name_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Operation_description",
        ret="char *",
        args=["blpapi_Operation_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Operation_name", ret="char *", args=["blpapi_Operation_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Operation_numResponseDefinitions",
        ret="int",
        args=["blpapi_Operation_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Operation_requestDefinition",
        ret="int",
        args=["blpapi_Operation_t*", "blpapi_SchemaElementDefinition_t**"],
    )
    verify_ctypes(
        fnc="blpapi_Operation_responseDefinition",
        ret="int",
        args=[
            "blpapi_Operation_t*",
            "blpapi_SchemaElementDefinition_t**",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Operation_responseDefinitionFromName",
        ret="int",
        args=[
            "blpapi_Operation_t*",
            "blpapi_SchemaElementDefinition_t**",
            "blpapi_Name_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_activateSubServiceCodeRange",
        ret="int",
        args=["blpapi_ProviderSession_t*", "char*", "int", "int", "int"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_createServiceStatusTopic",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_Service_t*",
            "blpapi_Topic_t**",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_createTopic",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_TopicList_t*",
            "int",
            "blpapi_Identity_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_createTopics",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_TopicList_t*",
            "int",
            "blpapi_Identity_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_createTopicsAsync",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_TopicList_t*",
            "int",
            "blpapi_Identity_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_deactivateSubServiceCodeRange",
        ret="int",
        args=["blpapi_ProviderSession_t*", "char*", "int", "int"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_deleteTopics",
        ret="int",
        args=["blpapi_ProviderSession_t*", "blpapi_Topic_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_deregisterService",
        ret="int",
        args=["blpapi_ProviderSession_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_flushPublishedEvents",
        ret="int",
        args=["blpapi_ProviderSession_t*", "int*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_getAbstractSession",
        ret="blpapi_AbstractSession_t *",
        args=["blpapi_ProviderSession_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_getTopic",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_Message_t*",
            "blpapi_Topic_t**",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_nextEvent",
        ret="int",
        args=["blpapi_ProviderSession_t*", "blpapi_Event_t**", "unsigned int"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_publish",
        ret="int",
        args=["blpapi_ProviderSession_t*", "blpapi_Event_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_registerService",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "char*",
            "blpapi_Identity_t*",
            "blpapi_ServiceRegistrationOptions_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_registerServiceAsync",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "char*",
            "blpapi_Identity_t*",
            "blpapi_CorrelationId_t*",
            "blpapi_ServiceRegistrationOptions_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_resolve",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_ResolutionList_t*",
            "int",
            "blpapi_Identity_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_resolveAsync",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_ResolutionList_t*",
            "int",
            "blpapi_Identity_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_sendResponse",
        ret="int",
        args=["blpapi_ProviderSession_t*", "blpapi_Event_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_start",
        ret="int",
        args=["blpapi_ProviderSession_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_startAsync",
        ret="int",
        args=["blpapi_ProviderSession_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_stop",
        ret="int",
        args=["blpapi_ProviderSession_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_stopAsync",
        ret="int",
        args=["blpapi_ProviderSession_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_terminateSubscriptionsOnTopics",
        ret="int",
        args=[
            "blpapi_ProviderSession_t*",
            "blpapi_Topic_t**",
            "size_t",
            "char*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ProviderSession_tryNextEvent",
        ret="int",
        args=["blpapi_ProviderSession_t*", "blpapi_Event_t**"],
    )
    verify_ctypes(
        fnc="blpapi_RequestTemplate_release",
        ret="int",
        args=["blpapi_RequestTemplate_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Request_destroy", ret="void", args=["blpapi_Request_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Request_elements",
        ret="blpapi_Element_t *",
        args=["blpapi_Request_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Request_getRequestId",
        ret="int",
        args=["blpapi_Request_t*", "char**"],
    )
    verify_ctypes(
        fnc="blpapi_Request_setPreferredRoute",
        ret="void",
        args=["blpapi_Request_t*", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_add",
        ret="int",
        args=["blpapi_ResolutionList_t*", "char*", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_addAttribute",
        ret="int",
        args=["blpapi_ResolutionList_t*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_addFromMessage",
        ret="int",
        args=[
            "blpapi_ResolutionList_t*",
            "blpapi_Message_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_attribute",
        ret="int",
        args=[
            "blpapi_ResolutionList_t*",
            "blpapi_Element_t**",
            "blpapi_Name_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_attributeAt",
        ret="int",
        args=[
            "blpapi_ResolutionList_t*",
            "blpapi_Element_t**",
            "blpapi_Name_t*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_correlationIdAt",
        ret="int",
        args=["blpapi_ResolutionList_t*", "blpapi_CorrelationId_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_create",
        ret="blpapi_ResolutionList_t *",
        args=["blpapi_ResolutionList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_destroy",
        ret="void",
        args=["blpapi_ResolutionList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_extractAttributeFromResolutionSuccess",
        ret="blpapi_Element_t *",
        args=["blpapi_Message_t*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_message",
        ret="int",
        args=[
            "blpapi_ResolutionList_t*",
            "blpapi_Message_t**",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_messageAt",
        ret="int",
        args=["blpapi_ResolutionList_t*", "blpapi_Message_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_size",
        ret="int",
        args=["blpapi_ResolutionList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_status",
        ret="int",
        args=["blpapi_ResolutionList_t*", "int*", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_statusAt",
        ret="int",
        args=["blpapi_ResolutionList_t*", "int*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_topicString",
        ret="int",
        args=["blpapi_ResolutionList_t*", "char**", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ResolutionList_topicStringAt",
        ret="int",
        args=["blpapi_ResolutionList_t*", "char**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_description",
        ret="char *",
        args=["blpapi_SchemaElementDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_getAlternateName",
        ret="blpapi_Name_t *",
        args=["blpapi_SchemaElementDefinition_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_maxValues",
        ret="size_t",
        args=["blpapi_SchemaElementDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_minValues",
        ret="size_t",
        args=["blpapi_SchemaElementDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_name",
        ret="blpapi_Name_t *",
        args=["blpapi_SchemaElementDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_numAlternateNames",
        ret="size_t",
        args=["blpapi_SchemaElementDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_status",
        ret="int",
        args=["blpapi_SchemaElementDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaElementDefinition_type",
        ret="blpapi_SchemaTypeDefinition_t *",
        args=["blpapi_SchemaElementDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_datatype",
        ret="int",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_description",
        ret="char *",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_enumeration",
        ret="blpapi_ConstantList_t *",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_getElementDefinition",
        ret="void*",
        args=["blpapi_SchemaTypeDefinition_t*", "char*", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_getElementDefinitionAt",
        ret="void*",
        args=["blpapi_SchemaTypeDefinition_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_isComplexType",
        ret="int",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_isEnumerationType",
        ret="int",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_isSimpleType",
        ret="int",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_name",
        ret="blpapi_Name_t *",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_numElementDefinitions",
        ret="size_t",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SchemaTypeDefinition_status",
        ret="int",
        args=["blpapi_SchemaTypeDefinition_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_addActiveSubServiceCodeRange",
        ret="int",
        args=["blpapi_ServiceRegistrationOptions_t*", "int", "int", "int"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_copy",
        ret="void",
        args=[
            "blpapi_ServiceRegistrationOptions_t*",
            "blpapi_ServiceRegistrationOptions_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_create",
        ret="blpapi_ServiceRegistrationOptions_t *",
        args=[""],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_destroy",
        ret="void",
        args=["blpapi_ServiceRegistrationOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_duplicate",
        ret="void*",
        args=["blpapi_ServiceRegistrationOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_getGroupId",
        ret="int",
        args=["blpapi_ServiceRegistrationOptions_t*", "char*", "int*"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_getPartsToRegister",
        ret="int",
        args=["blpapi_ServiceRegistrationOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_getServicePriority",
        ret="int",
        args=["blpapi_ServiceRegistrationOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_removeAllActiveSubServiceCodeRanges",
        ret="void",
        args=["blpapi_ServiceRegistrationOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_setGroupId",
        ret="void",
        args=["blpapi_ServiceRegistrationOptions_t*", "char*", "unsigned int"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_setPartsToRegister",
        ret="void",
        args=["blpapi_ServiceRegistrationOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_ServiceRegistrationOptions_setServicePriority",
        ret="int",
        args=["blpapi_ServiceRegistrationOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_Service_addRef", ret="int", args=["blpapi_Service_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Service_authorizationServiceName",
        ret="char *",
        args=["blpapi_Service_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Service_createAdminEvent",
        ret="int",
        args=["blpapi_Service_t*", "blpapi_Event_t**"],
    )
    verify_ctypes(
        fnc="blpapi_Service_createAuthorizationRequest",
        ret="int",
        args=["blpapi_Service_t*", "blpapi_Request_t**", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_Service_createPublishEvent",
        ret="int",
        args=["blpapi_Service_t*", "blpapi_Event_t**"],
    )
    verify_ctypes(
        fnc="blpapi_Service_createRequest",
        ret="int",
        args=["blpapi_Service_t*", "blpapi_Request_t**", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_Service_createResponseEvent",
        ret="int",
        args=[
            "blpapi_Service_t*",
            "blpapi_CorrelationId_t*",
            "blpapi_Event_t**",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Service_description",
        ret="char *",
        args=["blpapi_Service_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Service_getEventDefinition",
        ret="int",
        args=[
            "blpapi_Service_t*",
            "blpapi_SchemaElementDefinition_t**",
            "char*",
            "blpapi_Name_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Service_getEventDefinitionAt",
        ret="int",
        args=[
            "blpapi_Service_t*",
            "blpapi_SchemaElementDefinition_t**",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Service_getOperation",
        ret="int",
        args=[
            "blpapi_Service_t*",
            "blpapi_Operation_t**",
            "char*",
            "blpapi_Name_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Service_getOperationAt",
        ret="int",
        args=["blpapi_Service_t*", "blpapi_Operation_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Service_name", ret="char *", args=["blpapi_Service_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Service_numEventDefinitions",
        ret="int",
        args=["blpapi_Service_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Service_numOperations",
        ret="int",
        args=["blpapi_Service_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Service_release", ret="void", args=["blpapi_Service_t*"]
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_allowMultipleCorrelatorsPerMsg",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_applicationIdentityKey",
        ret="int",
        args=["char**", "size_t*", "blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_authenticationOptions",
        ret="char *",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_autoRestartOnDisconnection",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_bandwidthSaveModeDisabled",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_clientMode",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_connectTimeout",
        ret="unsigned int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_create",
        ret="blpapi_SessionOptions_t *",
        args=[""],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_defaultKeepAliveInactivityTime",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_defaultKeepAliveResponseTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_defaultServices",
        ret="char *",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_defaultSubscriptionService",
        ret="char *",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_defaultTopicPrefix",
        ret="char *",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_destroy",
        ret="void",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_flushPublishedEventsTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_getServerAddressWithProxy",
        ret="int",
        args=[
            "blpapi_SessionOptions_t*",
            "char**",
            "unsigned short*",
            "char**",
            "unsigned short*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_keepAliveEnabled",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_maxEventQueueSize",
        ret="size_t",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_maxPendingRequests",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_numServerAddresses",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_numStartAttempts",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_recordSubscriptionDataReceiveTimes",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_removeServerAddress",
        ret="int",
        args=["blpapi_SessionOptions_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_serverHost",
        ret="char *",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_serverPort",
        ret="unsigned int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_serviceCheckTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_serviceDownloadTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_sessionName",
        ret="int",
        args=["char**", "size_t*", "blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setAllowMultipleCorrelatorsPerMsg",
        ret="void",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setApplicationIdentityKey",
        ret="int",
        args=["blpapi_SessionOptions_t*", "char*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setAuthenticationOptions",
        ret="void",
        args=["blpapi_SessionOptions_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setAutoRestartOnDisconnection",
        ret="void",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setBandwidthSaveModeDisabled",
        ret="int",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setClientMode",
        ret="void",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setConnectTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*", "unsigned int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setDefaultKeepAliveInactivityTime",
        ret="int",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setDefaultKeepAliveResponseTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setDefaultServices",
        ret="int",
        args=["blpapi_SessionOptions_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setDefaultSubscriptionService",
        ret="int",
        args=["blpapi_SessionOptions_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setDefaultTopicPrefix",
        ret="void",
        args=["blpapi_SessionOptions_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setFlushPublishedEventsTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setKeepAliveEnabled",
        ret="int",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setMaxEventQueueSize",
        ret="void",
        args=["blpapi_SessionOptions_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setMaxPendingRequests",
        ret="void",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setNumStartAttempts",
        ret="void",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setRecordSubscriptionDataReceiveTimes",
        ret="void",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setServerAddress",
        ret="int",
        args=["blpapi_SessionOptions_t*", "char*", "unsigned short", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setServerAddressWithProxy",
        ret="int",
        args=[
            "blpapi_SessionOptions_t*",
            "char*",
            "unsigned short",
            "blpapi_Socks5Config_t*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setServerHost",
        ret="int",
        args=["blpapi_SessionOptions_t*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setServerPort",
        ret="int",
        args=["blpapi_SessionOptions_t*", "unsigned short"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setServiceCheckTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setServiceDownloadTimeout",
        ret="int",
        args=["blpapi_SessionOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setSessionIdentityOptions",
        ret="int",
        args=[
            "blpapi_SessionOptions_t*",
            "blpapi_AuthOptions_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setSessionName",
        ret="int",
        args=["blpapi_SessionOptions_t*", "char*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setSlowConsumerWarningHiWaterMark",
        ret="int",
        args=["blpapi_SessionOptions_t*", "float"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setSlowConsumerWarningLoWaterMark",
        ret="int",
        args=["blpapi_SessionOptions_t*", "float"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_setTlsOptions",
        ret="void",
        args=["blpapi_SessionOptions_t*", "blpapi_TlsOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_slowConsumerWarningHiWaterMark",
        ret="float",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SessionOptions_slowConsumerWarningLoWaterMark",
        ret="float",
        args=["blpapi_SessionOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Session_createSnapshotRequestTemplate",
        ret="int",
        args=[
            "blpapi_RequestTemplate_t**",
            "blpapi_Session_t*",
            "char*",
            "blpapi_Identity_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_getAbstractSession",
        ret="blpapi_AbstractSession_t *",
        args=["blpapi_Session_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Session_nextEvent",
        ret="int",
        args=["blpapi_Session_t*", "blpapi_Event_t**", "unsigned int"],
    )
    verify_ctypes(
        fnc="blpapi_Session_resubscribe",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_SubscriptionList_t*",
            "char*",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_resubscribeEx",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_SubscriptionList_t*",
            "char*",
            "int",
            "blpapi_SubscriptionPreprocessErrorHandler_t",
            "void*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_resubscribeWithId",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_SubscriptionList_t*",
            "int",
            "char*",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_resubscribeWithIdEx",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_SubscriptionList_t*",
            "int",
            "char*",
            "int",
            "blpapi_SubscriptionPreprocessErrorHandler_t",
            "void*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_sendRequest",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_Request_t*",
            "blpapi_CorrelationId_t*",
            "blpapi_Identity_t*",
            "blpapi_EventQueue_t*",
            "char*",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_sendRequestTemplate",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_RequestTemplate_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_setStatusCorrelationId",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_Service_t*",
            "blpapi_Identity_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_start", ret="int", args=["blpapi_Session_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Session_startAsync", ret="int", args=["blpapi_Session_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Session_stop", ret="int", args=["blpapi_Session_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Session_stopAsync", ret="int", args=["blpapi_Session_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Session_subscribe",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_SubscriptionList_t*",
            "blpapi_Identity_t*",
            "char*",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Session_tryNextEvent",
        ret="int",
        args=["blpapi_Session_t*", "blpapi_Event_t**"],
    )
    verify_ctypes(
        fnc="blpapi_Session_unsubscribe",
        ret="int",
        args=[
            "blpapi_Session_t*",
            "blpapi_SubscriptionList_t*",
            "char*",
            "int",
        ],
    )
    verify_ctypes(
        fnc="blpapi_Socks5Config_create",
        ret="blpapi_Socks5Config_t *",
        args=["char*", "size_t", "unsigned short"],
    )
    verify_ctypes(
        fnc="blpapi_Socks5Config_destroy",
        ret="void",
        args=["blpapi_Socks5Config_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_addResolved",
        ret="int",
        args=[
            "blpapi_SubscriptionList_t*",
            "char*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_append",
        ret="int",
        args=["blpapi_SubscriptionList_t*", "blpapi_SubscriptionList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_clear",
        ret="int",
        args=["blpapi_SubscriptionList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_correlationIdAt",
        ret="int",
        args=[
            "blpapi_SubscriptionList_t*",
            "blpapi_CorrelationId_t*",
            "size_t",
        ],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_create",
        ret="blpapi_SubscriptionList_t *",
        args=[""],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_destroy",
        ret="void",
        args=["blpapi_SubscriptionList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_isResolvedAt",
        ret="int",
        args=["blpapi_SubscriptionList_t*", "int*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_size",
        ret="int",
        args=["blpapi_SubscriptionList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_SubscriptionList_topicStringAt",
        ret="int",
        args=["blpapi_SubscriptionList_t*", "char**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_TestUtil_appendMessage",
        ret="int",
        args=[
            "blpapi_MessageFormatter_t**",
            "blpapi_Event_t*",
            "blpapi_SchemaElementDefinition_t*",
            "blpapi_MessageProperties_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_TestUtil_createEvent",
        ret="int",
        args=["blpapi_Event_t**", "int"],
    )
    verify_ctypes(
        fnc="blpapi_TestUtil_createTopic",
        ret="int",
        args=["blpapi_Topic_t**", "blpapi_Service_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_TestUtil_deserializeService",
        ret="int",
        args=["char*", "size_t", "blpapi_Service_t**"],
    )
    verify_ctypes(
        fnc="blpapi_TestUtil_getAdminMessageDefinition",
        ret="int",
        args=["blpapi_SchemaElementDefinition_t**", "blpapi_Name_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TimePointUtil_nanosecondsBetween",
        ret="long long",
        args=["blpapi_TimePoint_t*", "blpapi_TimePoint_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TlsOptions_createFromBlobs",
        ret="blpapi_TlsOptions_t *",
        args=["char*", "int", "char*", "char*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_TlsOptions_createFromFiles",
        ret="blpapi_TlsOptions_t *",
        args=["char*", "char*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_TlsOptions_destroy",
        ret="void",
        args=["blpapi_TlsOptions_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TlsOptions_setCrlFetchTimeoutMs",
        ret="void",
        args=["blpapi_TlsOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_TlsOptions_setTlsHandshakeTimeoutMs",
        ret="void",
        args=["blpapi_TlsOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_add",
        ret="int",
        args=["blpapi_TopicList_t*", "char*", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_addFromMessage",
        ret="int",
        args=[
            "blpapi_TopicList_t*",
            "blpapi_Message_t*",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_correlationIdAt",
        ret="int",
        args=["blpapi_TopicList_t*", "blpapi_CorrelationId_t*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_create",
        ret="blpapi_TopicList_t *",
        args=["blpapi_TopicList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_destroy",
        ret="void",
        args=["blpapi_TopicList_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_message",
        ret="int",
        args=[
            "blpapi_TopicList_t*",
            "blpapi_Message_t**",
            "blpapi_CorrelationId_t*",
        ],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_messageAt",
        ret="int",
        args=["blpapi_TopicList_t*", "blpapi_Message_t**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_size", ret="int", args=["blpapi_TopicList_t*"]
    )
    verify_ctypes(
        fnc="blpapi_TopicList_status",
        ret="int",
        args=["blpapi_TopicList_t*", "int*", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_statusAt",
        ret="int",
        args=["blpapi_TopicList_t*", "int*", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_topicString",
        ret="int",
        args=["blpapi_TopicList_t*", "char**", "blpapi_CorrelationId_t*"],
    )
    verify_ctypes(
        fnc="blpapi_TopicList_topicStringAt",
        ret="int",
        args=["blpapi_TopicList_t*", "char**", "size_t"],
    )
    verify_ctypes(
        fnc="blpapi_Topic_compare",
        ret="int",
        args=["blpapi_Topic_t*", "blpapi_Topic_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Topic_create",
        ret="blpapi_Topic_t *",
        args=["blpapi_Topic_t*"],
    )
    verify_ctypes(
        fnc="blpapi_Topic_destroy", ret="void", args=["blpapi_Topic_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Topic_isActive", ret="int", args=["blpapi_Topic_t*"]
    )
    verify_ctypes(
        fnc="blpapi_Topic_service",
        ret="blpapi_Service_t *",
        args=["blpapi_Topic_t*"],
    )
    verify_ctypes(
        fnc="blpapi_UserAgentInfo_setUserTaskName", ret="int", args=["char*"]
    )
    verify_ctypes(
        fnc="blpapi_UserAgentInfo_setNativeSdkLanguageAndVersion",
        ret="int",
        args=["char*", "char*"],
    )
    verify_ctypes(
        fnc="blpapi_ZfpUtil_getOptionsForLeasedLines",
        ret="int",
        args=["blpapi_SessionOptions_t*", "blpapi_TlsOptions_t*", "int"],
    )
    verify_ctypes(
        fnc="blpapi_getLastErrorDescription", ret="char *", args=["int"]
    )
