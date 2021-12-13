"""Sample script for subscribing to a security."""

import blpapi

import appconfig
from compute_engine import ComputeEngine
from notifier import Notifier
from event_processor import EventProcessor
from token_generator import TokenGenerator
from authorizer import Authorizer
from subscriber import Subscriber
from application import Application

if __name__ == "__main__":
    options = appconfig.parseCmdLine()
    compute_engine = ComputeEngine()
    notifier = Notifier()
    event_processor = EventProcessor(notifier, compute_engine)

    so = blpapi.SessionOptions()
    for i, host in enumerate(options.hosts):
        so.setServerAddress(host, options.port, i)

    so.setAuthenticationOptions(options.auth['option'])

    session = blpapi.Session(so, event_processor.processEvent)

    token_generator = TokenGenerator(session)
    authorizer = Authorizer(session, token_generator)

    subscriber = Subscriber(session)

    application = Application(session, authorizer, subscriber, options)

    application.run()

    input("Press Enter to continue...\n")


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
