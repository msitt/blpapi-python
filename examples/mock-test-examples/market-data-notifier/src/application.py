"""Sample application."""

from __future__ import print_function

# pylint: disable=too-few-public-methods
class Application():
    """Custom application for demonstration purposes."""

    def __init__(self, session, authorizer, subscriber, options):
        self._session = session
        self._authorizer = authorizer
        self._subscriber = subscriber
        self._options = options

    def run(self):
        """Start the application."""
        if not self._session.start():
            print("Failed to start session")
            return

        identity = self._session.createIdentity()
        if not self._authorizer.authorize(identity):
            print("No authorization")
            return

        self._subscriber.subscribe(
            self._options.topics, self._options.fields,
            self._options.options, identity)

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
