""" Test suite for TokenGenerator. """

import unittest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import os
import sys
#pylint: disable=line-too-long,wrong-import-position
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from token_generator import TokenGenerator

import blpapi


class TestTokenGenerator(unittest.TestCase):
    """ Test cases for TokenGenerator. """

    def setUp(self):
        self.mock_session = Mock()
        self.mock_event_queue = Mock()
        self.token_generator = TokenGenerator(self.mock_session)

    def testTokenGenerationSuccess(self):
        """ Verify that on token generation success, the application receives
        a valid token.

        Plan:
        1. Create a TokenStatus admin event using blpapi.test.createEvent().
        2. Obtain the schema for TokenGenerationSuccess using
           blpapi.test.getAdminMessageDefinition().
        3. Append a message of type TokenGenerationSuccess using
           blpapi.test.appendMessage().
        4. Using the returned formatter, format the message. In this example
           the message has body { "token": "dummy_token" }.
           `token` is the element name, and `dummy_token` is the token value
           which will be delivered to the client application.
        5. Setup the event queue to return the appropriate event.
        6. Verify that the expected token value is generated.
        """
        event = blpapi.test.createEvent(blpapi.Event.TOKEN_STATUS)
        token_success = blpapi.Name("TokenGenerationSuccess")
        schema_def = blpapi.test.getAdminMessageDefinition(token_success)

        formatter = blpapi.test.appendMessage(event, schema_def)

        expected_token = "dummy_token"
        message_content = {
            "token": expected_token
        }

        formatter.formatMessageDict(message_content)

        self.mock_event_queue.nextEvent.return_value = event

        actual_token = self.token_generator.generate(self.mock_event_queue)

        self.mock_session.generateToken.assert_called_once()
        self.mock_event_queue.nextEvent.assert_called_once()
        self.assertEqual(expected_token, actual_token)

    def testTokenGenerationFailure(self):
        """ Verify that on token generation failure, the application receives an
        empty token.

        Plan:
        1. Create a TokenStatus admin event using blpapi.test.createEvent().
        2. Obtain schema for TokenGenerationFailure using
           blpapi.test.getAdminMessageDefinition().
        3. Append a message of type TokenGenerationFailure using
           blpapi.test.appendMessage().
        4. Using the returned formatter, format the message. In this example,
           the message body contains the reason for failure.
           The reason is delivered to the user application.
        5. Setup the event queue to return the appropriate event.
        6. Verify that the actual token is None.
        """
        message_content = {
            "reason": {
                "source": "apitkns (apiauth) on n795",
                "category": "NO_AUTH",
                "errorCode": 3,
                "description": "App not in emrs ...",
                "subcategory": "INVALID_APP"
            }
        }
        event = blpapi.test.createEvent(blpapi.Event.TOKEN_STATUS)

        token_failure = blpapi.Name("TokenGenerationFailure")
        schema_def = blpapi.test.getAdminMessageDefinition(token_failure)

        formatter = blpapi.test.appendMessage(event, schema_def)

        formatter.formatMessageDict(message_content)

        self.mock_event_queue.nextEvent.return_value = event

        actual_token = self.token_generator.generate(self.mock_event_queue)

        self.mock_session.generateToken.assert_called_once()
        self.mock_event_queue.nextEvent.assert_called_once()
        self.assertIsNone(actual_token)


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
