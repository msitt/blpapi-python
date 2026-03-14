# abstractsessionhandle.py

"""An implementation of 'AbstractSession' that forwards all calls to the held
C object handle.
"""

# pylint: disable=protected-access
from typing import Union, Sequence, Optional
from weakref import ref
from . import typehints  # pylint: disable=unused-import
from .typehints import (
    BlpapiAbstractSessionHandle,
)
from . import exception
from .exception import _ExceptionUtil
from .identity import Identity
from .service import Service
from . import internals
from .correlationid import CorrelationId
from .utils import get_handle
from .chandle import CHandle
from .abstractsession import AbstractSession


class AbstractSessionHandle(CHandle, AbstractSession):
    r"""An implementation of :class:`AbstractSession` that can be used as
    a delegate.
    """

    def __init__(
        self,
        abstractSessionHandle: BlpapiAbstractSessionHandle,
        parentHandle: CHandle,
    ) -> None:
        """Instantiate an :class:`AbstractSession` with the specified handle.

        Args:
            abstractSessionHandle: Handle to the underlying abstract session

        This function is for internal use only. Clients should create sessions
        using one of the concrete subclasses of :class:`AbstractSession`.
        """

        super(AbstractSessionHandle, self).__init__(
            abstractSessionHandle, None
        )
        self._parentHandle = ref(parentHandle)

    def openService(self, serviceName: str) -> bool:
        return (
            internals.blpapi_AbstractSession_openService(
                self._handle(), serviceName
            )
            == 0
        )

    def openServiceAsync(
        self, serviceName: str, correlationId: Optional[CorrelationId] = None
    ) -> CorrelationId:
        if correlationId is None:
            correlationId = CorrelationId()
        _ExceptionUtil.raiseOnError(
            internals.blpapi_AbstractSession_openServiceAsync(
                self._handle(), serviceName, correlationId
            )
        )
        return correlationId

    def sendAuthorizationRequest(
        self,
        request: "typehints.Request",
        identity: Identity,
        correlationId: Optional[CorrelationId] = None,
        eventQueue: Optional["typehints.EventQueue"] = None,
    ) -> CorrelationId:

        if correlationId is None:
            correlationId = CorrelationId()

        if eventQueue is not None:
            eventQueue._throwOnParentMismatch(self._parentHandle())
        _ExceptionUtil.raiseOnError(
            internals.blpapi_AbstractSession_sendAuthorizationRequest(
                self._handle(),
                get_handle(request),
                get_handle(identity),
                correlationId,
                get_handle(eventQueue),
                None,  # no request label
            )
        )
        if eventQueue is not None:
            eventQueue._registerSession(self._parentHandle())
        return correlationId

    def cancel(
        self,
        correlationId: Union[CorrelationId, Sequence[CorrelationId], None],
    ) -> None:
        if correlationId is None:
            return
        if isinstance(correlationId, list):
            cids = correlationId
        else:
            cids = [correlationId]
        _ExceptionUtil.raiseOnError(
            internals.blpapi_AbstractSession_cancel(self._handle(), cids, None)
        )  # no request label

    def generateToken(
        self,
        correlationId: Optional[CorrelationId] = None,
        eventQueue: Optional["typehints.EventQueue"] = None,
        authId: Optional[str] = None,
        ipAddress: Optional[str] = None,
    ) -> CorrelationId:
        if correlationId is None:
            correlationId = CorrelationId()

        if eventQueue is not None:
            eventQueue._throwOnParentMismatch(self._parentHandle())

        if authId is None and ipAddress is None:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_AbstractSession_generateToken(
                    self._handle(), correlationId, get_handle(eventQueue)
                )
            )
        elif authId is not None and ipAddress is not None:
            _ExceptionUtil.raiseOnError(
                internals.blpapi_AbstractSession_generateManualToken(
                    self._handle(),
                    correlationId,
                    authId,
                    ipAddress,
                    get_handle(eventQueue),
                )
            )
        else:
            raise exception.InvalidArgumentException(
                "'authId' and 'ipAddress' must be provided together", 0
            )
        if eventQueue is not None:
            eventQueue._registerSession(self._parentHandle())
        return correlationId

    def getService(self, serviceName: str) -> Service:
        errorCode, service = internals.blpapi_AbstractSession_getService(
            self._handle(), serviceName
        )
        _ExceptionUtil.raiseOnError(errorCode)
        return Service(service, self._parentHandle())

    def createIdentity(self) -> Identity:
        return Identity(
            internals.blpapi_AbstractSession_createIdentity(self._handle()),
            self._parentHandle(),
        )

    def generateAuthorizedIdentity(
        self,
        authOptions: "typehints.AuthOptions",
        correlationId: Optional[CorrelationId] = None,
    ) -> CorrelationId:
        if correlationId is None:
            correlationId = CorrelationId()
        retcode = (
            internals.blpapi_AbstractSession_generateAuthorizedIdentityAsync(
                self._handle(), get_handle(authOptions), correlationId
            )
        )
        _ExceptionUtil.raiseOnError(retcode)
        return correlationId

    def getAuthorizedIdentity(
        self, correlationId: Optional[CorrelationId] = None
    ) -> Identity:
        if correlationId is None:
            correlationId = CorrelationId()
        (
            retcode,
            identity_handle,
        ) = internals.blpapi_AbstractSession_getAuthorizedIdentity(
            self._handle(), correlationId
        )
        _ExceptionUtil.raiseOnError(retcode)
        return Identity(identity_handle, self._parentHandle())

    def sessionName(self) -> str:
        result, sessionName = internals.blpapi_AbstractSession_sessionName(
            self._handle()
        )

        _ExceptionUtil.raiseOnError(result)
        return sessionName if sessionName is not None else ""
