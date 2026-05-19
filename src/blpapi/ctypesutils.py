import ctypes
from ctypes import (
    c_void_p,
    Structure,
    cast,
    py_object,
    c_char,
    c_uint16,
)
from typing import Any, Callable, Generic, Union, Optional, Tuple, TypeVar

T = TypeVar("T")


class POINTER(
    Generic[T],
    ctypes._Pointer,  # pylint: disable=protected-access
):
    """A type-hint wrapper around :func:`ctypes.POINTER` that supports
    ``POINTER[T]`` bracket syntax.

    This class exists only for static type checking with ``mypy``.
    At runtime, ``POINTER[T]`` delegates to :func:`ctypes.POINTER`
    and returns the actual ctypes pointer type, not an instance of
    this class.
    """

    def __class_getitem__(cls, *args: type) -> Any:
        return ctypes.POINTER(*args)


class blpapi_Event_t(Structure):
    """Opaque structure representing a BLPAPI Event."""


blpapi_Event_t_p = POINTER[blpapi_Event_t]


def voidFromPyObject(obj: Any) -> c_void_p:
    # an alternative would be c_void_p.from_buffer(py_object(obj))
    # use .value to get the address as an int
    return c_void_p(id(obj))


def voidFromPyFunction(cb: Callable) -> c_void_p:
    return voidFromPyObject(cb)


def py_objectFromVoid(voidp: c_void_p) -> py_object:
    return cast(voidp, py_object)


def pyObjectFromVoid(voidp: c_void_p) -> Any:
    return py_objectFromVoid(voidp).value


_LIMITS = {c_uint16: [0, 0xFFFF]}


def safePOD(value: Union[int, float], ctype: Any) -> Any:
    limits = _LIMITS[ctype]
    if value <= limits[1] and value >= limits[0]:
        return ctype(value)
    raise OverflowError()


def getHandleFromPtr(outp: Union[int, Any]) -> Optional[Union[c_void_p, Any]]:
    """Get c_void_p handle or None to populate a CHandle.

    Many C interface functions can return NULL, or populate an output pointer
    with NULL,  when that happens we want to provide a None object,
    rather than a c_void_p holding the NULL value.

    NB: Currently all call sites to this are POINTER type,yet we keep outp
    compatible with old convention, where C-function's restype was c_void_p.
    When that was the case, ctypes always converted c_void_p to a pythonic int.
    Thus c_void_p and POINTER have different "falsiness" behaviour around 0.
    """
    return (
        (c_void_p(outp) if outp else None)
        if isinstance(outp, int)
        else (outp if outp else None)
    )


def getHandleFromOutput(
    outp: Any, retCode: int
) -> Optional[Union[c_void_p, Any]]:
    """Get handle (c_void_p or POINTER type)

    Special case: C layer populates the buffer with NULL.
    The following statements are true (tested separately)
    1) outp is not None and type(outp) is POINTER(c_void_p) or POINTER(POINTER(...))
    2) outp.contents is not None and type(outp.contents) is c_void_p or a POINTER type
    3) but outp.contents.value is None, so its type is the NoneType not int

    i.e., it is always safe to access outp.contents as a valid c_void_p or POINTER type.

    Returns either a c_void_p (for c_void_p inputs) or a POINTER type (for
    POINTER inputs) or None.
    """
    # if retCode != 0 there is no chance this None
    # is used as handle by caller
    return outp.contents if retCode == 0 else None


def getRawPtrFromHandle(
    handle: Optional[Any],
) -> Optional[int]:
    """Get int pointer or None

    Some C interface functions expect a NULL pointer to be passed as 0, when
    that happens we want to pass a None pointer in Python, rather than a
    c_void_p holding the NULL value.

    Handles both c_void_p and POINTER types.
    """
    if handle is None:
        return None
    # For c_void_p types, we can directly access the .value attribute
    # For Mock objects, we can also access the .value attribute if it exists
    if isinstance(handle, c_void_p) or hasattr(handle, "value"):
        return handle.value
    # For POINTER types, we need to get the address
    # ctypes POINTER types can be cast to c_void_p to get their address
    try:
        return cast(handle, c_void_p).value
    except (TypeError, AttributeError):
        # If casting fails, return None
        return None


def getStrFromC(
    value: Optional[bytes], dflt: Optional[str] = None
) -> Optional[str]:
    """When restype = c_char_p ctypes will:
    1) provide a None for nullptr
    2) provide empty bytes object for empty string
    3) provide non-empty bytes object for non-empty string.
    [2 and 3] are safe to decode.
    We assume all such are null-terminated and not funny unicode"""
    return value.decode() if value is not None else dflt


def getStrFromOutput(
    outp: Any, retCode: int, dflt: Optional[str] = None
) -> Optional[str]:
    if retCode != 0:
        return dflt
    value = outp.contents.value
    return value.decode() if value is not None else dflt


def getSizedStrFromOutput(
    outp: Any, outsz: Any, retCode: int, dflt: Optional[str] = None
) -> Optional[str]:
    if retCode != 0:
        return dflt
    if not outp.contents.value or not outsz.contents.value:
        return ""
    return getSizedStrFromBuffer(outp.contents, outsz.contents.value)


def getSizedStrFromBuffer(outp: Any, outsz: Any) -> str:
    return getSizedBytesFromBuffer(outp, outsz).decode()


def getSizedBytesFromOutput(
    outp: Any, outsz: Any, retCode: int, dflt: Optional[bytes] = None
) -> Optional[bytes]:
    if retCode != 0:
        return dflt
    if not outp.contents.value or not outsz.contents.value:
        return b""
    return getSizedBytesFromBuffer(outp.contents, outsz.contents.value)


def getSizedBytesFromBuffer(outp: Any, outsz: int) -> bytes:
    return bytes(cast(outp, ctypes.POINTER(c_char * outsz)).contents)


def getPODFromOutput(outp: Any, retCode: int) -> Any:
    return outp.contents.value if retCode == 0 else None


def getStructFromOutput(outp: Any, retCode: int) -> Any:
    return outp.contents if retCode == 0 else None


def charPtrFromPyStr(val: Union[str, bytes, None]) -> bytes:
    """Use for immutable null-terminated input strings
    Works with None"""
    return val.encode() if str == type(val) else val  # type: ignore


def charPtrWithSizeFromPyStr(
    val: Union[str, bytes, bytearray, None],
) -> Tuple[Optional[bytes], int]:
    if str == type(val):
        bts = val.encode()
        return bts, len(bts)
    if val is None:
        return None, 0
    return val, len(val)  # type: ignore
