""" Test suite for Application. """

import unittest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import os
import sys
#pylint: disable=line-too-long,wrong-import-position
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from application import Application


class TestApplication(unittest.TestCase):
    """ Test cases for Application. """

    def setUp(self):
        self.mock_session = Mock()
        self.mock_authorizer = Mock()
        self.mock_subscriber = Mock()
        self.mock_options = Mock()

    def testSessionStartFail(self):
        """ Verify that if the session fails to start, no authorization or
        subscriptions are made.

        Plan:
        Set up and verify the following mocks:
        a. start() returns False.
        b. authorize() is not called.
        c. subscribe() is not called.
        """
        application = Application(self.mock_session,
                                  self.mock_authorizer,
                                  self.mock_subscriber,
                                  self.mock_options)

        self.mock_session.start.return_value = False
        application.run()

        self.mock_session.start.assert_called_once()
        self.mock_authorizer.authorize.assert_not_called()
        self.mock_subscriber.subscribe.assert_not_called()

    def testSessionAuthorizeFail(self):
        """ Verify that if authorization fails, no subscriptions are made.

        Plan:
        Set up and verify the following mocks:
        a. start() returns True.
        b. authorize() fails and returns False.
        c. subscribe() is not called.
        """
        application = Application(self.mock_session,
                                  self.mock_authorizer,
                                  self.mock_subscriber,
                                  self.mock_options)

        self.mock_session.start.return_value = True
        self.mock_authorizer.authorize.return_value = False

        application.run()

        self.mock_session.start.assert_called_once()
        self.mock_authorizer.authorize.assert_called_once()
        self.mock_subscriber.subscribe.assert_not_called()

    def testSubscribeWithConfig(self):
        """ Verify the correct topics and fields are used when subscribing on
        the session.

        Plan:
        Set up and verify the following mocks:
        a. start() returns True.
        b. authorize() succeeds and returns True.
        c. subscribe() is called with the same topics and fields configured in
           the options.
        """
        expected_topics = ["IBM US Equity", "MSFT US Equity"]
        expected_fields = ["LAST_PRICE", "BID", "ASK"]
        service_name = "//blp/mktdata"

        self.mock_options.configure_mock(**{
            "service": service_name,
            "topics": expected_topics,
            "fields": expected_fields
        })

        application = Application(self.mock_session,
                                  self.mock_authorizer,
                                  self.mock_subscriber,
                                  self.mock_options)

        self.mock_session.start.return_value = True
        self.mock_authorizer.authorize.return_value = True

        application.run()

        self.mock_session.start.assert_called_once()
        self.mock_authorizer.authorize.assert_called_once()

        actual_topics = self.mock_subscriber.subscribe.call_args[0][0]
        actual_fields = self.mock_subscriber.subscribe.call_args[0][1]
        self.assertEqual(expected_topics, actual_topics)
        self.assertEqual(expected_fields, actual_fields)


if __name__ == "__main__":
    unittest.main()

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
