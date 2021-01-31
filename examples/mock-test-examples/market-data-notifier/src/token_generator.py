"""Sample token generator for testing."""

import blpapi

TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")
TOKEN = blpapi.Name("token")

# pylint: disable=too-few-public-methods
class TokenGenerator():
    """Generates a token for later authorization."""

    def __init__(self, session):
        self._session = session

    def generate(self, event_queue=None):
        """Generate a token."""

        token = None
        if event_queue is None:
            event_queue = blpapi.EventQueue()

        self._session.generateToken(blpapi.CorrelationId(), event_queue)

        event = event_queue.nextEvent()
        if event.eventType() == blpapi.Event.REQUEST_STATUS or \
                event.eventType() == blpapi.Event.TOKEN_STATUS:
            for msg in event:
                if msg.messageType() == TOKEN_SUCCESS:
                    token = msg.getElementAsString(TOKEN)
                    return token
                if msg.messageType() == TOKEN_FAILURE:
                    return None
        return None

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
