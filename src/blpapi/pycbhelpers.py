from ctypes import (
    CFUNCTYPE,
    c_int,
    c_char_p,
    c_void_p,
)

from typing import Any, Callable
from io import StringIO

from .ctypesutils import pyObjectFromVoid, voidFromPyObject

# ============== General disclaimer ==============
# All python callback wrappers currently use the same approach,
# namely, the pointer to py object is given as void* userdata,
# converted back to py object and a proper call is made on it.
# The benefit of this approach is that we can have one instance
# of a proxy to serve all needs.
# The other approach would be to bind the pythonic callback
# and pass null as userdata. That way we need to keep fewer things alive,
# but would have to create per call proxy object (and keep that alive)


def default_print_helper(data: bytes, sz: int, out: Any) -> int:
    if sz > 0:
        pyout = pyObjectFromVoid(out)
        getattr(pyout, "write")(data[:sz].decode())
    return 0


class StreamWrapper:
    _cftype = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)

    def __init__(self, cb: Callable = default_print_helper) -> None:
        self._cb = self._cftype(cb)

    def get(self) -> Callable:
        return self._cb


def any_printer(
    handle: c_void_p, cfun: Callable, level: int, spacesPerLevel: int
) -> str:
    out = StringIO()
    writer = StreamWrapper()
    outparam = voidFromPyObject(out)
    cfun(handle, writer.get(), outparam, level, spacesPerLevel)
    out.seek(0)
    return out.read()


def _dispatchEventProxy(event: Any, _session: Any, pycb: Any) -> None:
    pyout = pyObjectFromVoid(pycb)
    getattr(pyout, "__call__")(c_void_p(event))


class EventHandleWrapper:
    # blpapi_Event_t *event, blpapi_Session_t *session, void *userData
    _cftype = CFUNCTYPE(None, c_void_p, c_void_p, c_void_p)

    def __init__(self) -> None:
        self._cb = self._cftype(_dispatchEventProxy)

    def get(self) -> Callable:
        return self._cb


anySessionEventHandlerWrapper = EventHandleWrapper()


def _subscriptionPreprocessProxy(
    cid: int, subString: bytes, errorCode: int, errorDesc: bytes, pycb: int
) -> None:
    # ^ the typehints are representation of
    # c_void_p, c_char_p, c_int, c_char_p, c_void_p
    pyout = pyObjectFromVoid(c_void_p(pycb))

    # The handler is given &correlationId.impl()
    # by ProxySubscriptionPreprocessErrorHandler::handleError
    # i.e., it does not bump the ref. for us
    correlationId = correlationIdWrapper(cid)
    getattr(pyout, "__call__")(
        correlationId, subString.decode(), errorCode, errorDesc.decode()
    )


class SubscriptionPreprocessHandlerWrapper:
    # void (*blpapi_SubscriptionPreprocessErrorHandler_t)(
    #     const blpapi_CorrelationId_t *correlationId,
    #     const char *subscriptionString,
    #     int errorCode,
    #     const char *errorDescription,
    #     void *userData)
    _cftype = CFUNCTYPE(None, c_void_p, c_char_p, c_int, c_char_p, c_void_p)

    def __init__(self) -> None:
        self._cb = self._cftype(_subscriptionPreprocessProxy)

    def get(self) -> Callable:
        return self._cb


anySessionSubErrorHandlerWrapper = SubscriptionPreprocessHandlerWrapper()


# will be overridden in correlationid.py
def correlationIdWrapper(ptr: int) -> Any:
    raise Exception("Invalid cid wrapper called with", ptr)
