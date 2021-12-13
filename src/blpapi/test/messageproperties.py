# messageproperties.py

""" Class for defining properties of mock messages. """

import blpapi
from blpapi import internals
from blpapi.exception import _ExceptionUtil
from blpapi.datetime import _DatetimeUtil
from ..utils import get_handle

class MessageProperties():
    """
    This class represents properties of a message that are not part of the
    message contents, such as the correlation ids or timestamp.
    """

    def __init__(self):
        """
        Create 'MessageProperties' with default values.

        Default value for the 'CorrelationId' property is an empty list.
        Default value for the 'recapType' property is 'Message.RECAPTYPE_NONE'.
        Default value for the 'fragmentType' property is
        'Message.FRAGMENT_NONE'.
        Default value for the 'Service' and 'timeReceived' is "unset".
        """
        rc, self.__handle = internals.blpapi_MessageProperties_create()
        _ExceptionUtil.raiseOnError(rc)

    def __del__(self):
        try:
            self.destroy()
        except (NameError, AttributeError):
            pass

    def destroy(self):
        """Destroy this :class:`MessageProperties`."""
        if self.__handle:
            internals.blpapi_MessageProperties_destroy(self.__handle)
            self.__handle = None

    def setCorrelationIds(self, cids):
        """
        Set the `correlationIds` properties of the message.

        Args:
            cids ([blpapi.CorrelationId]): list of correlation ids of the
                message.
        """
        errorCode = internals.blpapi_MessageProperties_setCorrelationIds(
            self.__handle, list(cids))
        _ExceptionUtil.raiseOnError(errorCode)

    def setRecapType(self, recapType,
                     fragmentType=blpapi.Message.FRAGMENT_NONE):
        """
        Set the `recapType` and `fragmentType` properties of the message.

        Args:
            recapType (int): Recap type of the message. See
                :class:`blpapi.Message` for valid values.
            fragmentType (int): Optional. Fragment type of the message. See
                :class:`blpapi.Message` for valid values. The default value is
                ``blpapi.Message.FRAGMENT_NONE``.
        """
        errorCode = internals.blpapi_MessageProperties_setRecapType(
            self.__handle, recapType, fragmentType)
        _ExceptionUtil.raiseOnError(errorCode)

    def setTimeReceived(self, timestamp):
        """
        Set the `timeReceived` property of the message.

        Args:
            timestamp (datetime.datetime): Timestamp of the message.
        """
        ts = _DatetimeUtil.convertToBlpapi(timestamp)
        errorCode = internals.blpapi_MessageProperties_setTimeReceived(
            self.__handle, ts)
        _ExceptionUtil.raiseOnError(errorCode)

    def setRequestId(self, requestId):
        """
        Set the `requestId` property.
        A copy of this string is expected to be returned
        by :meth:`blpapi.Message.getRequestId()`.
        If `requestId` is empty or `None`, the method throws.

        Args:
            requestId (str): RequestId of the message.
        """
        errorCode = internals.blpapi_MessageProperties_setRequestId(
            self.__handle, requestId)
        _ExceptionUtil.raiseOnError(errorCode)


    def setService(self, service):
        """
        Set the `service` property of the message.

        Args:
            service (blpapi.Service): Service of the message.
        """
        errorCode = internals.blpapi_MessageProperties_setService(
            self.__handle, get_handle(service))
        _ExceptionUtil.raiseOnError(errorCode)

    def _handle(self):
        """For internal use only."""
        return self.__handle


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
