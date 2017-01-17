# identity.py

"""Provide access to the entitlements for a user.

This component provides an identification of a user and implements the access
to the entitlements.
"""


from __future__ import absolute_import

from .element import Element
from .exception import _ExceptionUtil
from . import internals
from . import utils


class Identity(object):
    """Provides access to the entitlements for a specific user.

    An unauthorized Identity is created using Session.createIdentity(). Once
    a Identity has been created it can be authorized using
    Session.sendAuthorizationRequest(). The authorized Identity can then be
    queried or used in Session.subscribe() or Session.sendRequest() calls.

    Once authorized a Identity has access to the entitlements of the user which
    it was validated for.


    Seat types:

    INVALID_SEAT - Unknown seat type
    BPS          - Bloomberg Professional Service
    NONBPS       - Non-BPS
    """

    INVALID_SEAT = internals.SEATTYPE_INVALID_SEAT
    """Unknown seat type"""
    BPS = internals.SEATTYPE_BPS
    """Bloomberg Professional Service"""
    NONBPS = internals.SEATTYPE_NONBPS
    """Non-BPS"""

    def __init__(self, handle, sessions):
        """Create an Identity associated with the 'sessions'"""
        self.__handle = handle
        self.__sessions = sessions
        internals.blpapi_Identity_addRef(self.__handle)

    def __del__(self):
        """Destuctor.

        Destroying the last Identity for a specific user cancels any
        authorizations associated with it.
        """

        internals.blpapi_Identity_release(self.__handle)

    def hasEntitlements(self, service, entitlements):
        """Return True if authorized for the specified Service and EIDs.

        Return True if this 'Identity' is authorized for the specified
        'service' and for each of the entitlement IDs contained in the
        specified 'entitlements', which must be a list of integers, or
        an 'Element' which is an array of integers.
        """
        if isinstance(entitlements, Element):
            res = internals.blpapi_Identity_hasEntitlements(
                self.__handle,
                service._handle(),
                entitlements._handle(),
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
                service._handle(),
                None,
                carrayOfEIDs,
                numberOfEIDs,
                None,
                None)
        return True if res else False

    def getFailedEntitlements(self, service, entitlements):
        """Return a tuple containing a boolean and a list of integers.

        Return a tuple containing a boolean and a list of integers, where
        the returned boolean is true if this 'Identity' is authorized for the
        specified 'service' and all of the specified 'entitlements', which must
        be either a list of integers or an 'Element' which is an array of
        integers, and the returned list is the subset of 'entitlements' for
        which this identity is not authorized. The contents of the returned
        list are not specified if this identity is not authorized for
        'service'.
        """
        if isinstance(entitlements, Element):
            maxFailedEIDs = entitlements.numValues()
            failedEIDs = internals.intArray(maxFailedEIDs)
            failedEIDsSize = internals.intArray(1)
            failedEIDsSize[0] = maxFailedEIDs
            res = internals.blpapi_Identity_hasEntitlements(
                self.__handle,
                service._handle(),
                entitlements._handle(),
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
                service._handle(),
                None,
                carrayOfEIDs,
                numberOfEIDs,
                failedEIDs,
                failedEIDsSize)
        result = []
        for i in xrange(failedEIDsSize[0]):
            result.append(failedEIDs[i])
        return (True if res else False, result)

    def isAuthorized(self, service):
        """Return True if the handle is authorized for the specified Service.

        Return True if the user handle is authorized for the specified
        Service. Use hasEntitlements() to determine what (if anything)
        entitlements a Identity has.
        """

        res = internals.blpapi_Identity_isAuthorized(self.__handle,
                                                     service._handle())
        return True if res else False

    def getSeatType(self):
        """Return seat type of this identity."""
        res = internals.blpapi_Identity_getSeatType(self.__handle)
        _ExceptionUtil.raiseOnError(res[0])
        return res[1]

    def _handle(self):
        """Return the internal implementation."""
        return self.__handle

    # Protect enumeration constant(s) defined in this class and in classes
    # derived from this class from changes:
    __metaclass__ = utils.MetaClassForClassesWithEnums

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
