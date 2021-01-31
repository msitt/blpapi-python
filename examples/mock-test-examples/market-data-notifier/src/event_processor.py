"""Simple class for handling incoming events from a session"""
import blpapi

TOKEN_SUCCESS = blpapi.Name("TokenSuccess")
TOKEN_FAILURE = blpapi.Name("TokenFailure")
TOKEN = blpapi.Name("token")

# pylint: disable=too-few-public-methods
class EventProcessor():
    """Custom EventHandler implementation for demonstration purposes."""

    def __init__(self, notifier, compute_engine):
        self._notifier = notifier
        self._compute_engine = compute_engine

    def processEvent(self, event, _):
        """Action for each event from the session."""
        for msg in event:
            if event.eventType() == blpapi.Event.SESSION_STATUS:
                self._notifier.log_session_state(msg)
            elif event.eventType() == blpapi.Event.SUBSCRIPTION_STATUS:
                self._notifier.log_subscription_state(msg)
            elif event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                last_price = msg.getElementAsFloat("LAST_PRICE")
                result = \
                    self._compute_engine.someVeryComplexComputation(last_price)
                self._notifier.send_to_terminal(result)

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
