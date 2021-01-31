""" Test suite for EventProcessor. """

import unittest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import os
import sys
#pylint: disable=line-too-long,wrong-import-position
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from event_processor import EventProcessor

import blpapi


MKTDATA_SCHEMA = \
"""<?xml version="1.0" encoding="UTF-8" ?>
<ServiceDefinition name="blp.mktdata" version="1.0.1.0">
   <service name="//blp/mktdata" version="1.0.0.0" authorizationService="//blp/apiauth">
      <event name="MarketDataEvents" eventType="MarketDataUpdate">
         <eventId>0</eventId>
         <eventId>1</eventId>
         <eventId>2</eventId>
         <eventId>3</eventId>
         <eventId>4</eventId>
         <eventId>9999</eventId>
      </event>
      <defaultServiceId>134217729</defaultServiceId> <!-- 0X8000001 -->
      <resolutionService></resolutionService>
      <recapEventId>9999</recapEventId>
   </service>
   <schema>
      <sequenceType name="MarketDataUpdate">
         <description>fields in subscription</description>
         <element name="LAST_PRICE" type="Float64" id="1" minOccurs="0" maxOccurs="1">
            <description>Last Trade/Last Price</description>
            <alternateId>65536</alternateId>
         </element>
         <element name="BID" type="Float64" id="2" minOccurs="0" maxOccurs="1">
            <description>Bid Price</description>
            <alternateId>131072</alternateId>
         </element>
         <element name="ASK" type="Float64" id="3" minOccurs="0" maxOccurs="1">
            <description>Ask Price</description>
            <alternateId>196608</alternateId>
         </element>
         <element name="VOLUME" type="Int64" id="4" minOccurs="0" maxOccurs="1">
            <description>Volume</description>
            <alternateId>458753</alternateId>
         </element>
      </sequenceType>
   </schema>
</ServiceDefinition>
"""

class TestEventProcessor(unittest.TestCase):
    """ Test cases for EventProcessor. """

    def setUp(self):
        self.mock_session = Mock()
        self.mock_notifier = Mock()
        self.mock_compute_engine = Mock()
        self.event_processor = EventProcessor(self.mock_notifier,
                                              self.mock_compute_engine)

    def testNotifierReceivesSessionStarted(self):
        """ Verify that notifier receives a `SessionStarted' message.

        Plan:
        1. Create a SessionStatus admin event using blpapi.test.createEvent().
        2. Obtain the message schema using
           blpapi.test.getAdminMessageDefinition().
        3. Append a message of type SessionStarted using
           blpapi.test.appendMessage().
        4. Verify that the expected message is passed to
           notifier.log_session_state().
        """
        event = blpapi.test.createEvent(blpapi.Event.SESSION_STATUS)
        session_started = blpapi.Name("SessionStarted")
        schema_def = blpapi.test.getAdminMessageDefinition(session_started)

        blpapi.test.appendMessage(event, schema_def)

        self.event_processor.processEvent(event, self.mock_session)

        self.mock_notifier.log_session_state.assert_called_once()
        actual_message = self.mock_notifier.log_session_state.call_args[0][0]
        self.assertEqual(session_started, actual_message.messageType())


    def testNotifierReceivesSubscriptionStarted(self):
        """ Verify that notifier receives a `SubscriptionStarted` message.

        Plan:
        1. Create a SubscriptionStatus admin event using
           blpapi.test.createEvent().
        2. Obtain the schema for SubscriptionStarted message using
           blpapi.test.getAdminMessageDefinition().
        3. Append a message of type `SubscriptionStarted` using
           blpapi.test.appendMessage().
        4. Verify that the expected message is passed to
           notifier.log_subscription_state().
        """
        event = blpapi.test.createEvent(blpapi.Event.SUBSCRIPTION_STATUS)
        subscription_started = blpapi.Name("SubscriptionStarted")
        schema_def = blpapi.test.getAdminMessageDefinition(subscription_started)

        blpapi.test.appendMessage(event, schema_def)

        self.event_processor.processEvent(event, self.mock_session)

        self.mock_notifier.log_subscription_state.assert_called_once()
        actual_message = \
            self.mock_notifier.log_subscription_state.call_args[0][0]
        self.assertEqual(subscription_started, actual_message.messageType())

    def testNotifierReceivesSubscriptionData(self):
        """ Verify that:
        1. Compute engine receives the correct LAST_PRICE.
        2. Compute engine performs the correct computation and returns the
           correct value.
        3. The correct value is sent to the terminal.

        Plan:
        1. Obtain the service by deserializing its schema.
        2. Create a SubscriptionEvent using blpapi.test.createEvent().
        3. Obtain the element schema definition from the service.
        4. Append a message of type `MarketDataEvents' using
           blpapi.test.appendMessage().
        5. Format the message using the formatter returned by appendMessage().
           In this example the message's body is represented by
           { LAST_PRICE: 142.80 }.
        6. Verify that the expected and actual values are the same.
        """
        event = blpapi.test.createEvent(blpapi.Event.SUBSCRIPTION_DATA)

        service = blpapi.test.deserializeService(MKTDATA_SCHEMA)
        mktdata_events = blpapi.Name("MarketDataEvents")
        schema_def = service.getEventDefinition(mktdata_events)

        formatter = blpapi.test.appendMessage(event, schema_def)

        expected_last_price = 142.80
        message_content = {
            "LAST_PRICE": expected_last_price
        }
        formatter.formatMessageDict(message_content)

        expected_compute_result = 200.00

        self.mock_compute_engine.someVeryComplexComputation.return_value = \
            expected_compute_result

        self.event_processor.processEvent(event, self.mock_session)

        self.mock_compute_engine.someVeryComplexComputation \
            .assert_called_once_with(expected_last_price)
        self.mock_notifier.send_to_terminal \
            .assert_called_once_with(expected_compute_result)


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
