""" Sample test cases for mocking `blpapi` objects and using the `blpapi.test`
submodule in the context of resolvers.
"""

import unittest

try:
    from unittest.mock import ANY, Mock
except ImportError:
    from mock import ANY, Mock

import blpapi

from resolverutils import \
    resolutionServiceRegistration, \
    handlePermissionRequest


RESULT = blpapi.Name("result")
REASON = blpapi.Name("reason")
CATEGORY = blpapi.Name("category")
NOT_AUTHORIZED = blpapi.Name("NOT_AUTHORIZED")
TOPIC_PERMISSIONS = blpapi.Name("topicPermissions")
PERMISSION_REQUEST = blpapi.Name("PermissionRequest")
PERMISSION_RESPONSE = blpapi.Name("PermissionResponse")

ALLOWED_APP_ID = 1234
INVALID_APP_ID = 4321

def createPermissionEvent(cid, applicationId):
    """ Create a mock PermissionRequest `event`. """
    props = blpapi.test.MessageProperties()
    props.setCorrelationIds([cid])

    request = blpapi.test.createEvent(blpapi.Event.REQUEST)

    schemaDef = blpapi.test.getAdminMessageDefinition(PERMISSION_REQUEST)

    content = {
        "topics": [
            "topic1",
            "topic2"
        ],
        "serviceName": "//blp/mytestservice",
        "applicationId": applicationId
    }

    formatter = blpapi.test.appendMessage(request, schemaDef, props)

    formatter.formatMessageDict(content)

    return request


def getFirstMessage(event):
    """ Retrieve the first `Message` from the provided `event`. """
    for msg in event:
        return msg
    raise Exception("No messages in event")

#pylint: disable=line-too-long
def getService():
    """ Create a basic `Service` instance by deserializing a schema string. """
    schema = """
        <ServiceDefinition xsi:schemaLocation="http://bloomberg.com/schemas/apidd apidd.xsd"
                           name="test-svc"
                           version="1.0.0.0"
                           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <service name="//blp-test/test-svc" version="1.0.0.0">
            <event name="Events" eventType="EventType"/>
            <defaultServiceId>12345</defaultServiceId>
            <publisherSupportsRecap>false</publisherSupportsRecap>
            <authoritativeSourceSupportsRecap>false</authoritativeSourceSupportsRecap>
            <SubscriberResolutionServiceId>12346</SubscriberResolutionServiceId>
          </service>
          <schema>
              <sequenceType name="EventType">
                 <element name="price" type="Float64" minOccurs="0" maxOccurs="1"/>
              </sequenceType>
           </schema>
        </ServiceDefinition>
    """
    return blpapi.test.deserializeService(schema)

class TestResolverUtils(unittest.TestCase):
    """ Test suite for resolverutils. """

    def testResolutionServiceRegistration(self):
        """ This test demonstrates how to mock interactions on objects of type
        `ProviderSession`.
        In this test, we are setting the return value of the function, and
        verifying our input parameters.
        """
        mockSession = Mock()
        mockIdentity = Mock()

        serviceName = "//blp/mytestservice"

        mockSession.registerService.return_value = True

        registrationResult = resolutionServiceRegistration(mockSession,
                                                           mockIdentity,
                                                           serviceName)
        serviceRegistrationOptions = \
            mockSession.registerService.call_args[0][2]

        self.assertTrue(registrationResult)

        mockSession.registerService.assert_called_once_with(serviceName,
                                                            mockIdentity,
                                                            ANY)
        expectedPriority = 123
        self.assertEqual(expectedPriority,
                         serviceRegistrationOptions.getServicePriority())
        self.assertTrue(serviceRegistrationOptions.getPartsToRegister() &
                        blpapi.ServiceRegistrationOptions.PART_PUBLISHER_RESOLUTION)

    def testSuccessfulResolution(self):
        """ Test the creation of a successful permission response. """
        mockSession = Mock()
        service = getService()

        cid = blpapi.CorrelationId(1)
        permissionEvent = createPermissionEvent(cid, ALLOWED_APP_ID)
        permissionRequest = getFirstMessage(permissionEvent)

        handlePermissionRequest(mockSession, service, permissionRequest)

        mockSession.sendResponse.assert_called_once()
        response = mockSession.sendResponse.call_args[0][0]
        self.assertEqual(blpapi.Event.RESPONSE, response.eventType())

        permissionResponse = getFirstMessage(response)
        self.assertEqual(cid, permissionResponse.correlationIds()[0])
        self.assertEqual(PERMISSION_RESPONSE, permissionResponse.messageType())
        self.assertTrue(permissionResponse.hasElement(TOPIC_PERMISSIONS))

        topicPermissions = permissionResponse.getElement(TOPIC_PERMISSIONS)

        topicCount = 2
        self.assertEqual(topicCount, topicPermissions.numValues())

        for i in range(topicCount):
            topicPermission = topicPermissions.getValueAsElement(i)
            self.assertTrue(topicPermission.hasElement(RESULT))
            self.assertEqual(0, topicPermission.getElementAsInteger(RESULT))

    def testFailedResolution(self):
        """ Test the creation of a failed permission response. """
        mockSession = Mock()
        service = getService()

        cid = blpapi.CorrelationId(1)
        permissionEvent = createPermissionEvent(cid, INVALID_APP_ID)
        permissionRequest = getFirstMessage(permissionEvent)

        handlePermissionRequest(mockSession, service, permissionRequest)

        mockSession.sendResponse.assert_called_once()
        response = mockSession.sendResponse.call_args[0][0]
        self.assertEqual(blpapi.Event.RESPONSE, response.eventType())

        permissionResponse = getFirstMessage(response)
        self.assertEqual(cid, permissionResponse.correlationIds()[0])
        self.assertEqual(PERMISSION_RESPONSE, permissionResponse.messageType())
        self.assertTrue(permissionResponse.hasElement(TOPIC_PERMISSIONS))

        topicPermissions = permissionResponse.getElement(TOPIC_PERMISSIONS)

        topicCount = 2
        self.assertEqual(topicCount, topicPermissions.numValues())

        for i in range(topicCount):
            topicPermission = topicPermissions.getValueAsElement(i)
            self.assertTrue(topicPermission.hasElement(RESULT))
            self.assertEqual(1, topicPermission.getElementAsInteger(RESULT))

            self.assertTrue(topicPermission.hasElement(REASON))
            reason = topicPermission.getElement(REASON)

            self.assertTrue(reason.hasElement(CATEGORY))
            self.assertEqual(NOT_AUTHORIZED,
                             reason.getElementAsString(CATEGORY))


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
