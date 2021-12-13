# identity.py

"""Provide access to the entitlements for a user.

This component provides an identification of a user and implements the access
to the entitlements.
"""

from .element import Element
from .exception import _ExceptionUtil
from . import internals
from . import utils
from .utils import get_handle
from .compat import with_metaclass
from .chandle import CHandle

@with_metaclass(utils.MetaClassForClassesWithEnums)
class Identity(CHandle):
    """Provides access to the entitlements for a specific user.

    An unauthorized Identity is created using
    :meth:`~Session.createIdentity()`. Once an :class:`Identity` has been
    created it can be authorized using
    :meth:`~Session.sendAuthorizationRequest()`. The authorized
    :class:`Identity` can then be queried or used in
    :meth:`~Session.subscribe()` or :meth:`~Session.sendRequest()` calls.

    Once authorized, an :class:`Identity` has access to the entitlements of the
    user which it was validated for.

    :class:`Identity` objects are always created by the API, never directly by
    the application.

    The class attributes represent the various seat types.
    """

    INVALID_SEAT = internals.SEATTYPE_INVALID_SEAT
    """Unknown seat type"""
    BPS = internals.SEATTYPE_BPS
    """Bloomberg Professional Service"""
    NONBPS = internals.SEATTYPE_NONBPS
    """Non-BPS"""

    def __init__(self, handle, sessions):
        """Create an :class:`Identity` associated with the ``sessions``

        Args:
            handle: Handle to the internal implementation
            sessions: Sessions associated with this object
        """
        super(Identity, self).__init__(
            handle, internals.blpapi_Identity_release)
        self.__handle = handle  # pylint: disable=unused-private-member
        self.__sessions = sessions # pylint: disable=unused-private-member

        internals.blpapi_Identity_addRef(self.__handle)

    def hasEntitlements(self, service, entitlements):
        """
        Args:
            service (Service): Service to check authorization for
            entitlements ([int] or Element): EIDs to check authorization for

        Returns:
            bool: ``True`` if this :class:`Identity` is authorized for the
            specified ``service`` and for each of the entitlement IDs contained
            in the specified ``entitlements``.

        If :class:`Element` is supplied for ``entitlements``, it must be an
        array of integers.
        """
        if isinstance(entitlements, Element):
            res = internals.blpapi_Identity_hasEntitlements(
                self.__handle,
                get_handle(service),
                get_handle(entitlements),
                None,
                0,
                None,
                None)
        else:
            # Otherwise, assume entitlements is a list, or tuple, etc
            numberOfEIDs = len(entitlements)
            carrayOfEIDs = internals.intArray(numberOfEIDs)
            for i, eid in enumerate(entitlements):
                carrayOfEIDs[i] = eid
            res = internals.blpapi_Identity_hasEntitlements(
                self.__handle,
                get_handle(service),
                None,
                carrayOfEIDs,
                numberOfEIDs,
                None,
                None)
        return True if res else False

    def getFailedEntitlements(self, service, entitlements):
        """
        Args:
            service (Service): Service to check authorization for
            entitlements ([int] or Element): EIDs to check authorization for

        Returns:
            (bool, [int]): Tuple where the boolean is True if this
            :class:`Identity` is authorized for the specified ``service`` and
            all of the specified ``entitlements``, and the list is a subset of
            ``entitlements`` for which this :class:`Identity` is not
            authorized.

        Note:
            The contents of the returned list are not specified if this
            identity is not authorized for ``service``.
        """
        if isinstance(entitlements, Element):
            maxFailedEIDs = entitlements.numValues()
            failedEIDs = internals.intArray(maxFailedEIDs)
            failedEIDsSize = internals.intArray(1)
            failedEIDsSize[0] = maxFailedEIDs
            res = internals.blpapi_Identity_hasEntitlements(
                self.__handle,
                get_handle(service),
                get_handle(entitlements),
                None,
                0,
                failedEIDs,
                failedEIDsSize)
        else:
            # Otherwise, assume entitlements is a list, or tuple, etc
            numberOfEIDs = len(entitlements)
            carrayOfEIDs = internals.intArray(numberOfEIDs)
            for i, eid in enumerate(entitlements):
                carrayOfEIDs[i] = eid
            maxFailedEIDs = numberOfEIDs
            failedEIDs = internals.intArray(maxFailedEIDs)
            failedEIDsSize = internals.intArray(1)
            failedEIDsSize[0] = maxFailedEIDs
            res = internals.blpapi_Identity_hasEntitlements(
                self.__handle,
                get_handle(service),
                None,
                carrayOfEIDs,
                numberOfEIDs,
                failedEIDs,
                failedEIDsSize)
        result = []
        for i in range(failedEIDsSize[0]):
            result.append(failedEIDs[i])
        return (True if res else False, result)

    def isAuthorized(self, service):
        """
        Args:
            service (Service): Service to check authorization for

        Returns:
            bool: ``True`` if this :class:`Identity` is authorized for the
            specified ``service``, ``False`` otherwise.
        """
        res = internals.blpapi_Identity_isAuthorized(
            self.__handle,
            get_handle(service))
        return True if res else False

    def getSeatType(self):
        """
        Returns:
            int: Seat type of this identity.

        The class attributes of :class:`Identity` represent the seat types.
        """
        res = internals.blpapi_Identity_getSeatType(self.__handle)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:

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
