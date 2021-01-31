"""Sample authorization related component."""

from __future__ import print_function

import datetime

import blpapi

AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
TOKEN = blpapi.Name("token")

# pylint: disable=too-few-public-methods, too-many-branches
class Authorizer():
    """Helper for authorization."""

    def __init__(self, session, token_generator):
        self._session = session
        self._token_generator = token_generator

    def _authorize(self, auth_service, identity, cid, event_queue=None):
        """Authorize the identity."""

        token = self._token_generator.generate()

        if token is None:
            print("Failed to get token")
            return False

        # Create and fill the authorization request
        auth_request = auth_service.createAuthorizationRequest()
        auth_request.set(TOKEN, token)

        if event_queue is None:
            event_queue = blpapi.EventQueue()

        # Send authorization request to "fill" the Identity
        self._session.sendAuthorizationRequest(
            auth_request, identity, cid, event_queue)

        # Process related responses
        start_time = datetime.datetime.today()
        WAIT_TIME_SECONDS = 10
        while True:
            event = event_queue.nextEvent(WAIT_TIME_SECONDS * 1000)
            if event.eventType() == blpapi.Event.RESPONSE or \
                    event.eventType() == blpapi.Event.REQUEST_STATUS or \
                    event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
                for msg in event:
                    print(msg)
                    if msg.messageType() == AUTHORIZATION_SUCCESS:
                        return True
                    print("Authorization failed")
                    return False

            end_time = datetime.datetime.today()
            max_time_diff = datetime.timedelta(seconds=WAIT_TIME_SECONDS)
            if end_time - start_time > max_time_diff:
                return False

    def authorize(self, identity, queue=None):
        """Authorize the provided identity.

        Return True on success and False on failure.
        """
        if self._session.openService("//blp/apiauth"):
            service = self._session.getService("//blp/apiauth")
            cid = blpapi.CorrelationId("auth")
            return self._authorize(service, identity, cid, queue)
        return False

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
