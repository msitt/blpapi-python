"""Sample unit test cases"""

import unittest

import blpapi

# pylint: disable=no-self-use
# unlike "proper" unit tests, the provided samples do not include any
# assertions, so there is no 'self' use in the tests.

# pylint: disable=too-many-public-methods


class TestEvents(unittest.TestCase):
    """The following test cases provide an example of how to mock different
    events supported by the blpapi-sdk. The code to set up the expectation and
    verification of values is omitted from example tests."""

    # =====================
    # SESSION STATUS EVENTS
    # =====================

    def testSessionStarted(self):
        """Sample SessionStarted message"""
        event = blpapi.test.createEvent(blpapi.Event.SESSION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SESSION_STARTED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "initialEndpoints": [
                {"address": "12.34.56.78:8194"},
                {"address": "98.76.54.32:8194"},
            ]
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSessionStartupFailure(self):
        """Sample SessionStartupFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.SESSION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SESSION_STARTUP_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSessionTerminated(self):
        """Sample SessionTerminated message"""
        event = blpapi.test.createEvent(blpapi.Event.SESSION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SESSION_TERMINATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSessionConnectionUp(self):
        """Sample SessionConnectionUp message"""
        event = blpapi.test.createEvent(blpapi.Event.SESSION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SESSION_CONNECTION_UP
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "server": "12.34.56.78:8194",
            "serverId": "ny-hostname",
            "encryptionStatus": "Clear",
            "compressionStatus": "Uncompressed",
            "socks5Proxy": "socks5Host:1080",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSessionConnectionDown(self):
        """Sample SessionConnectionDown message"""
        event = blpapi.test.createEvent(blpapi.Event.SESSION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SESSION_CONNECTION_DOWN
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "server": "12.34.56.78:8194",
            "serverId": "ny-hostname",
            "socks5Proxy": "socks5Host:1080",
            "description": "Connection down description",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    # ============
    # ADMIN EVENTS
    # ============

    def testSlowConsumerWarning(self):
        """Sample SlowConsumerWarning message"""
        event = blpapi.test.createEvent(blpapi.Event.ADMIN)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SLOW_CONSUMER_WARNING
        )
        blpapi.test.appendMessage(event, schema)

    def testSlowConsumerWarningCleared(self):
        """Sample SlowConsumerWarningCleared message"""
        event = blpapi.test.createEvent(blpapi.Event.ADMIN)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SLOW_CONSUMER_WARNING_CLEARED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"eventsDropped": 123}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testDataLoss(self):
        """Sample DataLoss message"""
        event = blpapi.test.createEvent(blpapi.Event.ADMIN)
        schema = blpapi.test.getAdminMessageDefinition(blpapi.Name("DataLoss"))

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"id": "id", "source": "Test", "numMessagesDropped": 123}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testRequestTemplateAvailable(self):
        """Sample RequestTemplateAvailable message"""
        event = blpapi.test.createEvent(blpapi.Event.ADMIN)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.REQUEST_TEMPLATE_AVAILABLE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "boundTo": {"dataConnection": [{"address": "12.34.56.78:8194"}]}
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testRequestTemplatePending(self):
        """Sample RequestTemplatePending message"""
        event = blpapi.test.createEvent(blpapi.Event.ADMIN)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.REQUEST_TEMPLATE_PENDING
        )

        blpapi.test.appendMessage(event, schema)

    def testRequestTemplateTerminated(self):
        """Sample RequestTemplateTerminated message"""
        event = blpapi.test.createEvent(blpapi.Event.ADMIN)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.REQUEST_TEMPLATE_TERMINATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    # =====================
    # SERVICE STATUS EVENTS
    # =====================

    def testServiceOpened(self):
        """Sample ServiceOpened message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SERVICE_OPENED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"serviceName": "//blp/myservice"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testServiceOpenFailure(self):
        """Sample ServiceOpenFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SERVICE_OPEN_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testServiceRegistered(self):
        """Sample ServiceRegistered message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SERVICE_REGISTERED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"serviceName": "//blp/myservice"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testServiceRegisterFailure(self):
        """Sample ServiceRegisterFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SERVICE_REGISTER_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testServiceDeregistered(self):
        """Sample ServiceDeregistered message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SERVICE_DEREGISTERED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"serviceName": "//blp/myservice"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testServiceDown(self):
        """Sample ServiceDown message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SERVICE_DOWN
        )

        formatter = blpapi.test.appendMessage(event, schema)

        # content = {
        #     "serviceName": "//blp/myservice",
        #     "servicePart": {
        #         "publishing": { }
        #     },
        #     "endpoint": "12.34.56.78"
        # }
        # formatter.formatMessageDict(content)

        # Existence of void types (e.g. "servicePart" elements") are not
        # well-supported by the JSON/XML interface. Instead, use the
        # `EventFormatter`-like interface provided by `MessageFormatter`.
        formatter.setElement(blpapi.Name("serviceName"), "//blp/myservice")
        formatter.pushElement(blpapi.Name("servicePart"))
        formatter.setElement(blpapi.Name("publishing"), None)
        formatter.popElement()
        formatter.setElement(blpapi.Name("endpoint"), "12.34.56.78")

    def testServiceUp(self):
        """Sample ServiceUp message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(blpapi.Names.SERVICE_UP)

        formatter = blpapi.test.appendMessage(event, schema)

        # content = {
        #     "serviceName": "//blp/myservice",
        #     "servicePart": {
        #         "publishing": { }
        #     },
        #     "endpoint": "12.34.56.78"
        # }
        # formatter.formatMessageDict(content)

        # Existence of void types (e.g. "servicePart" elements") are not
        # well-supported by the JSON/XML interface. Instead, use the
        # `EventFormatter`-like interface provided by `MessageFormatter`.
        formatter.setElement(blpapi.Name("serviceName"), "//blp/myservice")
        formatter.pushElement(blpapi.Name("servicePart"))
        formatter.setElement(blpapi.Name("publishing"), None)
        formatter.popElement()
        formatter.setElement(blpapi.Name("endpoint"), "12.34.56.78")

    def testServiceAvailabilityInfo(self):
        """Sample ServiceAvailabilityInfo message"""
        event = blpapi.test.createEvent(blpapi.Event.SERVICE_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SERVICE_AVAILABILITY_INFO
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "serviceName": "//blp/myservice",
            "serverAdded": {"address": "12.34.56.78"},
            "serverRemoved": {"address": "12.34.56.78"},
            "servers": ["12.34.56.78", "12.34.56.78"],
        }
        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    # ===================
    # TOKEN STATUS EVENTS
    # ===================

    def testTokenGenerationSuccess(self):
        """Sample TokenGenerationSuccess message"""
        event = blpapi.test.createEvent(blpapi.Event.TOKEN_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOKEN_GENERATION_SUCCESS
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"token": "mytoken"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTokenGenerationFailure(self):
        """Sample TokenGenerationFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.TOKEN_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOKEN_GENERATION_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    # ==========================
    # SUBSCRIPTION STATUS EVENTS
    # ==========================

    def testSubscriptionStarted(self):
        """Sample SubscriptionStarted message"""
        event = blpapi.test.createEvent(blpapi.Event.SUBSCRIPTION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SUBSCRIPTION_STARTED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "exceptions": [
                {
                    "fieldId": "field",
                    "reason": {
                        "source": "TestUtil",
                        "errorCode": -1,
                        "category": "CATEGORY",
                        "description": "for testing",
                        "subcategory": "SUBCATEGORY",
                    },
                }
            ],
            "resubscriptionId": 123,
            "streamIds": ["123", "456"],
            "receivedFrom": {"address": "12.34.56.78:81964"},
            "reason": "TestUtil",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSubscriptionFailure(self):
        """Sample SubscriptionFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.SUBSCRIPTION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SUBSCRIPTION_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            },
            "failureDetails": [
                {
                    "fieldId": "field",
                    "reason": {
                        "source": "TestUtil",
                        "errorCode": -1,
                        "category": "CATEGORY",
                        "description": "for testing",
                        "subcategory": "SUBCATEGORY",
                    },
                }
            ],
            "resubscriptionId": 123,
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSubscriptionStreamsActivated(self):
        """Sample SubscriptionStreamsActivated message"""
        event = blpapi.test.createEvent(blpapi.Event.SUBSCRIPTION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SUBSCRIPTION_STREAMS_ACTIVATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "streams": [
                {"id": "streamId", "endpoint": {"address": "12.34.56.78:8194"}}
            ],
            "reason": "TestUtil",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSubscriptionStreamsDeactivated(self):
        """Sample SubscriptionStreamsDeactivated message"""
        event = blpapi.test.createEvent(blpapi.Event.SUBSCRIPTION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SUBSCRIPTION_STREAMS_DEACTIVATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "streams": [
                {"id": "streamId", "endpoint": {"address": "12.34.56.78:8194"}}
            ],
            "reason": "TestUtil",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testSubscriptionTerminated(self):
        """Sample SubscriptionTerminated message"""
        event = blpapi.test.createEvent(blpapi.Event.SUBSCRIPTION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.SUBSCRIPTION_TERMINATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    # =====================
    # REQUEST STATUS EVENTS
    # =====================

    def testRequestFailure(self):
        """Sample RequestFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.REQUEST_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.REQUEST_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    # ========================
    # RESOLUTION STATUS EVENTS
    # ========================

    def testResolutionSuccess(self):
        """Sample ResolutionSuccess message"""
        event = blpapi.test.createEvent(blpapi.Event.RESOLUTION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.RESOLUTION_SUCCESS
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"resolvedTopic": "//blp/myservice/rtopic"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testResolutionFailure(self):
        """Sample ResolutionFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.RESOLUTION_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.RESOLUTION_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            }
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    # ============================
    # PERMISSION STATUS OPERATIONS
    # ============================

    def testPermissionRequest(self):
        """Sample PermissionRequest message"""
        event = blpapi.test.createEvent(blpapi.Event.REQUEST)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.PERMISSION_REQUEST
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "topics": ["topic1", "topic2"],
            "serviceName": "//blp/mytestservice",
            "uuid": 1234,
            "seatType": 1234,
            "applicationId": 1234,
            "userName": "someName",
            "appName": "myAppName",
            "deviceAddress": "myDevice",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testPermissionResponse(self):
        """Sample PermissionResponse message"""
        # Unlike the other admin messages, 'PermissionResponse' is not
        # delivered to applications by the SDK. It is used by resolvers to
        # respond to incoming 'PermissionRequest' messages. BLPAPI applications
        # are not expected to handle these messages.
        #
        # For testing if an application is publishing 'PermissionResponse'
        # messages with correct values, it is recommended to mock the related
        # `ProviderSession::publish()` method to capture the published events.
        # See the provided testing examples for more detail.

    # ===================
    # TOPIC STATUS EVENTS
    # ===================

    def testTopicCreated(self):
        """Sample TopicCreated message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_CREATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"topic": "mytopic"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicCreateFailure(self):
        """Sample TopicCreateFailure message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_CREATE_FAILURE
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "topic": "mytopic",
            "reason": {
                "source": "TestUtil",
                "errorCode": -1,
                "category": "CATEGORY",
                "description": "for testing",
                "subcategory": "SUBCATEGORY",
            },
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicDeleted(self):
        """Sample TopicDeleted message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_DELETED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"topic": "mytopic", "reason": "TestUtil"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicSubscribed(self):
        """Sample TopicSubscribed message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_SUBSCRIBED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"topic": "mytopic", "topicWithOptions": "topicwithopts"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicResubscribed(self):
        """Sample TopicResubscribed message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_RESUBSCRIBED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "topic": "mytopic",
            "topicWithOptions": "topicwithopts",
            "reason": "TestUtil",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicUnsubscribed(self):
        """Sample TopicUnsubscribed message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_UNSUBSCRIBED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"topic": "mytopic", "reason": "TestUtil"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicActivated(self):
        """Sample TopicActivated message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_ACTIVATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"topic": "mytopic"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicDeactivated(self):
        """Sample TopicDeactivated message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_DEACTIVATED
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {"topic": "mytopic", "reason": "TestUtil"}

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())

    def testTopicRecap(self):
        """Sample TopicRecap message"""
        event = blpapi.test.createEvent(blpapi.Event.TOPIC_STATUS)
        schema = blpapi.test.getAdminMessageDefinition(
            blpapi.Names.TOPIC_RECAP
        )

        formatter = blpapi.test.appendMessage(event, schema)

        content = {
            "topic": "mytopic",
            "isSolicited": True,
            "topicWithOptions": "topicwithopts",
        }

        formatter.formatMessageDict(content)
        for msg in event:
            self.assertEqual(content, msg.toPy())


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
