# auth.py

"""Provide a configuration to specify the settings used for authorization."""

from typing import Callable, Any
from .typehints import BlpapiAuthOptionsHandle, BlpapiAuthUserHandle
from . import internals
from .utils import get_handle
from .exception import _ExceptionUtil
from .chandle import CHandle

class AuthOptions(CHandle):
    """Defines the authorization options which the user can set on
    :class:`SessionOptions` as the authorization options for the session
    identity or use to authorize other identities.
    """

    def __init__(self,
                 handle: BlpapiAuthOptionsHandle,
                 **kwargs) -> None:
        """For internal use only."""
        noop = lambda *args: None
        super(AuthOptions, self).__init__(handle, noop)
        self.__handle = handle
        self.__app_handle = kwargs.get("app_handle")
        self.__token_handle = kwargs.get("token_handle")
        self._options_dtor = internals.blpapi_AuthOptions_destroy
        self._app_dtor = internals.blpapi_AuthApplication_destroy
        self._token_dtor = internals.blpapi_AuthToken_destroy

    @classmethod
    def createWithUser(cls: Callable,
                       user: "AuthUser") -> "AuthOptions":
        """Creates an :class:`AuthOptions` instance for User Mode with the
        Operating System Login (Domain/User), Active Directory, or Email.

        Args:
            user: user-specific authorization option.

        Returns:
            Specifies User Mode with the Operating System Login
            (Domain/User), Active Directory, or Email.

        The behavior is undefined when ``user`` was created with
        :meth:`AuthUser.createWithManualOptions` or is ``None``.
        """
        retcode, authOptions_handle = internals \
            .blpapi_AuthOptions_create_forUserMode(get_handle(user))
        _ExceptionUtil.raiseOnError(retcode)
        return cls(authOptions_handle)

    @classmethod
    def createWithApp(cls: Callable, appName: str) -> "AuthOptions":
        """Create an :class:`AuthOptions` instance for Application Mode.

        Args:
            appName: app name used for Application Mode.

        Returns:
            Specifies Application Mode.

        The behavior is undefined when ``appName`` is ``None`` or ``""``.
        """
        app_handle = AuthOptions._create_app_handle(appName)
        retcode, authOptions_handle = internals \
            .blpapi_AuthOptions_create_forAppMode(app_handle)
        _ExceptionUtil.raiseOnError(retcode)
        return cls(authOptions_handle, app_handle=app_handle)

    @classmethod
    def createWithToken(cls: Callable, token: str) -> "AuthOptions":
        """Create an :class:`AuthOptions` instance for Manual Token Mode.

        Args:
            token: token to use for Manual Token Mode.

        Returns:
            Specifies Manual Token Mode.

        The behavior is undefined when ``token`` is ``None`` or ``""``.
        """
        token_handle = AuthOptions._create_token_handle(token)
        retcode, authOptions_handle = internals \
            .blpapi_AuthOptions_create_forToken(token_handle)
        _ExceptionUtil.raiseOnError(retcode)
        return cls(authOptions_handle, token_handle=token_handle)

    @classmethod
    def createWithUserAndApp(cls: Callable,
                             user: "AuthUser",
                             appName: str) -> "AuthOptions":
        """Create an :class:`AuthOptions` instance for User and Application
        Mode.

        Args:
            user: user-specific authorization option.
            appName: app name used for Application Mode.

        Returns:
            AuthOptions: an :class:`AuthOptions` that contains the
            authorization option for the User+Application authorization
            mode.

        The behavior is undefined when ``appName`` is ``None`` or ``""``.
        """
        app_handle = AuthOptions._create_app_handle(appName)
        retcode, authOptions_handle = internals \
            .blpapi_AuthOptions_create_forUserAndAppMode(get_handle(user),
                                                         app_handle)
        _ExceptionUtil.raiseOnError(retcode)
        return cls(authOptions_handle, app_handle=app_handle)

    def destroy(self) -> None:
        """Destroy this :class:`AuthOptions`."""
        if self.__handle:
            self._options_dtor(self.__handle)
            self.__handle = None
        if self.__app_handle:
            self._app_dtor(self.__app_handle)
            self.__app_handle = None
        if self.__token_handle:
            self._token_dtor(self.__token_handle)
            self.__token_handle = None

    @staticmethod
    def _create_app_handle(appName: str) -> Any:
        """For internal use only."""
        retcode, app_handle = internals \
            .blpapi_AuthApplication_create(appName)
        _ExceptionUtil.raiseOnError(retcode)
        return app_handle

    @staticmethod
    def _create_token_handle(token: str) -> Any:
        """For internal use only."""
        retcode, token_handle = internals \
            .blpapi_AuthToken_create(token)
        _ExceptionUtil.raiseOnError(retcode)
        return token_handle


class AuthUser(CHandle):
    """Contains user-specific authorization options."""

    def __init__(self, handle: BlpapiAuthUserHandle) -> None:
        """For internal use only."""
        super(AuthUser, self).__init__(
            handle, internals.blpapi_AuthUser_destroy)
        self.__handle = handle # pylint: disable=unused-private-member

    @classmethod
    def createWithLogonName(cls: Callable) -> "AuthUser":
        """Creates an :class:`AuthUser` instance configured for Operating
        System Login (Domain/User) authorization mode (OS_LOGON).

        Returns:
            Configured for Operating System Login (Domain/User) mode.
        """
        retcode, handle = internals \
            .blpapi_AuthUser_createWithLogonName()
        _ExceptionUtil.raiseOnError(retcode)
        return cls(handle)

    @classmethod
    def createWithActiveDirectoryProperty(
            cls: Callable,
            propertyName: str) -> "AuthUser":
        """Creates an :class:`AuthUser` instance configured for Active
        Directory authorization mode (DIRECTORY_SERVICE).

        Args:
            propertyName: Active Directory property.

        Returns:
            Configured for Active Directory (DIRECTORY_SERVICE)
            authorization mode.

        The behavior is undefined when ``propertyName`` is ``""`` or
        ``None``.
        """
        retcode, handle = internals \
            .blpapi_AuthUser_createWithActiveDirectoryProperty(
                propertyName)
        _ExceptionUtil.raiseOnError(retcode)
        return cls(handle)

    @classmethod
    def createWithManualOptions(
            cls: Callable, userId: str, ipAddress:str) -> "AuthUser":
        """Creates an :class:`AuthUser` instance configured for manual
        authorization.

        Args:
            userId: user id.
            ipAddress: IP address.

        Returns:
            Configured for manual authorization.

        The behavior is undefined when either ``userId`` or ``ipAddress`` is
        ``""`` or ``None``.
        """
        retcode, handle = internals \
            .blpapi_AuthUser_createWithManualOptions(userId, ipAddress)
        _ExceptionUtil.raiseOnError(retcode)
        return cls(handle)

__copyright__ = """
Copyright 2020. Bloomberg Finance L.P.

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
