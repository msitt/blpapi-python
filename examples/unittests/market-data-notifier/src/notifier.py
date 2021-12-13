"""Sample class for testing purposes."""
from __future__ import print_function

# pylint: disable=no-init,no-self-use
class Notifier():
    """
    Notifier is an approximation of a class that attempts to:
    1. Log all session events (for example SessionStartupFailure).
    2. Log all subscription events (for example SubscriptionStarted).
    3. Deliver subscription data to terminal ("Bloomberg terminal").
    """

    def log_session_state(self, msg):
        """Print the provided message."""
        print("Logging Session state with " + str(msg))

    def log_subscription_state(self, msg):
        """Print the provided message."""
        print("Logging Subscription state with " + str(msg))

    def send_to_terminal(self, value):
        """Print the provided value."""
        print("VALUE = " + str(value))

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
