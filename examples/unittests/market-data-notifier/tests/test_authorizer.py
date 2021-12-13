""" Test suite for Authorizer. """

import unittest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import os
import sys
#pylint: disable=line-too-long,wrong-import-position
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from authorizer import Authorizer

import blpapi


APIAUTH_SCHEMA = \
"""<?xml version="1.0" encoding="UTF-8" ?>
<ServiceDefinition name="blp.apiauth" version="1.0.7.2">
    <service name="//blp/apiauth" version="1.0.7.2">
        <operation name="AuthorizationRequest" serviceId="99">
            <request>Request</request>
            <requestSelection>AuthorizationRequest</requestSelection>
            <response>Response</response>
            <responseSelection>AuthorizationSuccess</responseSelection>
            <responseSelection>AuthorizationFailure</responseSelection>
            <isAuthorizationRequest>true</isAuthorizationRequest>
        </operation>
        <operation name="TokenRequest" serviceId="99">
            <request>Request</request>
            <requestSelection>TokenRequest</requestSelection>
            <response>Response</response>
            <responseSelection>TokenResponse</responseSelection>
        </operation>
        <publisherSupportsRecap>false</publisherSupportsRecap>
        <authoritativeSourceSupportsRecap>false</authoritativeSourceSupportsRecap>
        <isInfrastructureService>false</isInfrastructureService>
        <isMetered>false</isMetered>
        <appendMtrId>false</appendMtrId>
    </service>
    <schema>
        <sequenceType name="AuthorizationRequest">
            <description>seqAuthorizationRequest</description>
            <element name="ipAddress" type="String" minOccurs="0"
                maxOccurs="1">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="token" type="String" minOccurs="0" maxOccurs="1">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
        </sequenceType>
        <sequenceType name="TokenRequest">
            <description>seqTokenRequest</description>
            <element name="uuid" type="Int32">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="label" type="String">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
        </sequenceType>
        <sequenceType name="ErrorInfo">
            <description>seqErrorInfo</description>
            <element name="code" type="Int32">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="message" type="String">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="category" type="String">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="subcategory" type="String">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="source" type="String">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
        </sequenceType>
        <sequenceType name="AuthorizationSuccess">
            <description>seqAuthorizationSuccess</description>
        </sequenceType>
        <sequenceType name="AuthorizationFailure">
            <description>seqAuthorizationFailure</description>
            <element name="reason" type="ErrorInfo">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
        </sequenceType>
        <sequenceType name="AuthorizationTokenResponse">
            <description>seqAuthorizationTokenResponse</description>
        </sequenceType>
        <sequenceType name="TokenResponse">
            <description>seqTokenResponse</description>
            <element name="token" type="String">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="key" type="String">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
        </sequenceType>
        <choiceType name="Request">
            <description>choiceRequest</description>
            <element name="AuthorizationRequest" type="AuthorizationRequest">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="TokenRequest" type="TokenRequest">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
        </choiceType>
        <choiceType name="Response">
            <description>choiceResponse</description>
            <element name="AuthorizationSuccess" type="AuthorizationSuccess">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="AuthorizationFailure" type="AuthorizationFailure">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
            <element name="TokenResponse" type="TokenResponse">
                <description></description>
                <cacheable>true</cacheable>
                <cachedOnlyOnInitialPaint>false</cachedOnlyOnInitialPaint>
            </element>
        </choiceType>
    </schema>
</ServiceDefinition>
"""

class TestAuthorizer(unittest.TestCase):
    """ Test cases for Authorizer. """

    def setUp(self):
        self.mock_session = Mock()
        self.mock_token_generator = Mock()
        self.authorizer = Authorizer(self.mock_session,
                                     self.mock_token_generator)
        self.mock_event_queue = Mock()

    def testAuthorizationSuccess(self):
        """ Verify that for a valid identity the authorization returns True.

        Plan:
        1. Create a service instance from the apiauth schema.
        2. Set the following expectations:
           b. Verify that service is opened and successfully retrieved.
        3. Create an admin event to represent the authorization success.
        4. Call authorize()
        4. Verify the following:
           a. The service is opened and retrieved.
           b. A token is generated.
           c. An authorization request is sent.
           d. authorize() returns True.
        """
        self.mock_session.openService.return_value = True

        service = blpapi.test.deserializeService(APIAUTH_SCHEMA)
        self.mock_session.getService.return_value = service

        token = "abcdefg"
        self.mock_token_generator.generate.return_value = token

        event = blpapi.test.createEvent(blpapi.Event.RESPONSE)
        authorization_success = blpapi.Name("AuthorizationSuccess")
        schema_def = \
            blpapi.test.getAdminMessageDefinition(authorization_success)

        blpapi.test.appendMessage(event, schema_def)

        # The AuthorizationSuccess message does not have any fields, therefore
        # no formatting is required.

        self.mock_event_queue.nextEvent.return_value = event

        identity = Mock()
        authorization_result = self.authorizer.authorize(identity,
                                                         self.mock_event_queue)

        self.mock_session.openService.assert_called_once()
        self.mock_session.getService.assert_called_once()
        self.mock_session.sendAuthorizationRequest.assert_called_once()

        self.mock_token_generator.generate.assert_called_once()
        self.mock_event_queue.nextEvent.assert_called_once()

        self.assertTrue(authorization_result)

    def testAuthorizationFailure(self):
        """ Verify that for a invalid identity the authorization returns False.

        Plan:
        1. Create a service instance from the apiauth schema.
        2. Create and format an event to represent the authorization failure.
        3. Call authorize()
        4. Verify the following:
           a. The service is opened and retrieved.
           b. A token is generated.
           c. An authorization request is sent.
           d. authorize() returns False.
        """
        self.mock_session.openService.return_value = True

        service = blpapi.test.deserializeService(APIAUTH_SCHEMA)
        self.mock_session.getService.return_value = service

        token = "abcdefg"
        self.mock_token_generator.generate.return_value = token

        event = blpapi.test.createEvent(blpapi.Event.RESPONSE)
        authorization_request = blpapi.Name("AuthorizationRequest")
        authorization_failure_index = 1
        schema_def = service \
                        .getOperation(authorization_request) \
                        .getResponseDefinitionAt(authorization_failure_index)

        formatter = blpapi.test.appendMessage(event, schema_def)

        message_content = {
            "reason": {
                "code": 101,
                "message": "Invalid user",
                "category": "BAD_ARGS",
                "subcategory": "INVALID_USER",
                "source": "test-source"
            }
        }

        formatter.formatMessageDict(message_content)

        self.mock_event_queue.nextEvent.return_value = event

        identity = Mock()
        authorization_result = self.authorizer.authorize(identity,
                                                         self.mock_event_queue)

        self.mock_session.openService.assert_called_once()
        self.mock_session.getService.assert_called_once()
        self.mock_session.sendAuthorizationRequest.assert_called_once()

        self.mock_token_generator.generate.assert_called_once()
        self.mock_event_queue.nextEvent.assert_called_once()

        self.assertFalse(authorization_result)


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
