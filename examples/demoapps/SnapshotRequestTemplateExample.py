from argparse import ArgumentParser, RawTextHelpFormatter
from threading import Condition, Lock
from blpapi_import_helper import blpapi
from blpapi import Names
from util.ConnectionAndAuthOptions import \
    addConnectionAndAuthOptions, \
    createSessionOptions
from util.SubscriptionOptions import \
    addSubscriptionOptionsForSnapshot, \
    setSubscriptionSessionOptions, \
    createSubscriptionStrings
import time

# Requests are throttled in the infrastructure. Snapshot request templates send
# one resolution request per topic (unlike normal subscriptions where multiple
# topics are resolved at once), which is likely to cause request throttling.
# It is therefore recommended to create request templates in batches.
TEMPLATE_BATCH_SIZE = 50


class MyCorrelation:
    """The object that stores the topic of a snapshot.
    Used to avoid duplicate correlation id exception.
    """

    # To be able to retrieve the topic associated with a
    # response message, the correlationId of the request
    # is created with the topic string. This will eventually
    # lead to `DuplicateCorrelationIdException` for requests
    # having the same topic strings.
    #
    # This class therefore encapsulates the topic string inside
    # an object which will be different (by reference) each time
    # it is instantiated, regardless of the topic string saved
    # within it. When the response is received, the topic string
    # is extracted from it.

    def __init__(self, topic):
        self.topic = topic

    def __str__(self):
        return self.topic


def parseCmdLine():
    """Parse command line arguments"""

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Retrieve Snapshots")
    addConnectionAndAuthOptions(parser)
    addSubscriptionOptionsForSnapshot(parser)

    options = parser.parse_args()

    return options


class SnapshotRequestTemplateExample:

    def __init__(self):
        self._snapshots = {}

        # Lock and conditions are used to synchronize requests and responses,
        # i.e., the next requests are only sent after all the responses
        # of the current requests have been received.
        self._lock = Lock()
        self._responseCount = 0
        self._responseCondition = Condition(self._lock)

        self._templateCount = 0
        self.d_templateBatchingCondition = Condition(self._lock)

        self._running = True

    def _createTemplates(self, session, options):
        # NOTE: resources used by a snapshot request template are released
        # only when a 'RequestTemplateTerminated' message is received or when
        # the session is destroyed. In order to release resources when a
        # request template is not needed anymore, the user should call
        # 'Session.cancel' and pass the correlation id used when creating the
        # request template, or call 'RequestTemplate.close'. If 'Session.cancel'
        # is used, all outstanding requests are canceled and the underlying
        # subscription is closed immediately. If the handle is closed with
        # 'RequestTemplate.close', the underlying subscription is closed
        # only when all outstanding requests are served.

        subscriptionStrings = createSubscriptionStrings(options)
        with self._lock:
            self._responseCount = len(subscriptionStrings)
            for userTopic, subscriptionString in subscriptionStrings.items():
                self.d_templateBatchingCondition.wait_for(
                    lambda: not self._running or self._templateCount < TEMPLATE_BATCH_SIZE)

                if not self._running:
                    break

                # Create the template
                print(f"Creating snapshot request template for {userTopic}")

                statusCid = blpapi.CorrelationId(MyCorrelation(userTopic))
                requestTemplate = session.createSnapshotRequestTemplate(
                    subscriptionString,
                    statusCid)
                self._snapshots[statusCid] = requestTemplate

            # Wait until all the request templates have finished, either
            # success or failure.
            self._responseCondition.wait_for(
                lambda: not self._running or self._responseCount == 0)

    def _sendRequests(self, session):
        while True:
            print("Sending requests using the request templates")

            with self._lock:
                if not self._running:
                    break

                self._responseCount = len(self._snapshots)
                for cid, template in self._snapshots.items():
                    userTopic = cid.value().topic
                    print(f"Sending request for {userTopic}")
                    session.sendRequestTemplate(
                        template,
                        blpapi.CorrelationId(MyCorrelation(userTopic)))

                print("Waiting for the responses..., Press [Ctrl-C] to exit\n")
                self._responseCondition.wait_for(
                    lambda: not self._running or self._responseCount == 0)

            print("Received all the responses, will send next request in 5 seconds\n")
            time.sleep(5)

    def run(self):
        """main entry point"""
        options = parseCmdLine()

        sessionOptions = createSessionOptions(options)
        setSubscriptionSessionOptions(sessionOptions, options)
        session = blpapi.Session(sessionOptions, self.processEvent)

        try:
            if not session.start():
                print("Failed to start session.")
                return

            if not session.openService(options.service):
                print(f"Failed to open service '{options.service}'.")
                return

            self._createTemplates(session, options)

            if self._snapshots:
                self._sendRequests(session)
            else:
                print("Failed to create all the request templates, stopping...")
        finally:
            session.stop()

    def processEvent(self, event, _):
        """Process session event"""

        eventType = event.eventType()

        for msg in event:
            messageType = msg.messageType()
            cid = msg.correlationId()
            myCorrelation = cid.value()
            if messageType == Names.REQUEST_TEMPLATE_AVAILABLE:
                print("Request template is successfully created for topic"
                      f" {myCorrelation}")
                print(msg)

                with self._lock:
                    # Decrease template count
                    self._templateCount -= 1
                    self.d_templateBatchingCondition.notify_all()

                    # Decrease response count
                    self._responseCount -= 1
                    self._responseCondition.notify_all()
            elif messageType == Names.REQUEST_TEMPLATE_TERMINATED:
                # Will also receive a 'RequestFailure' message preceding
                # 'RequestTemplateTerminated' for every pending request.
                print(f"Request template terminated for topic {myCorrelation}")
                print(msg)

                with self._lock:
                    # Remove the template
                    del self._snapshots[myCorrelation]

                    # Decrease template count
                    self._templateCount -= 1
                    self.d_templateBatchingCondition.notify_all()

                    # Decrease response count
                    self._responseCount -= 1
                    self._responseCondition.notify_all()
            elif eventType == blpapi.Event.PARTIAL_RESPONSE:
                print(f"Received partial response for topic {myCorrelation}")
                print(msg)
            elif eventType == blpapi.Event.RESPONSE:
                print(f"Received response for topic {myCorrelation}")
                print(msg)

                with self._lock:
                    self._responseCount -= 1
                    self._responseCondition.notify_all()
            elif msg.messageType() == Names.SESSION_TERMINATED:
                with self._lock:
                    self._running = False
                    self.d_templateBatchingCondition.notify_all()
                    self._responseCondition.notify_all()


if __name__ == "__main__":
    try:
        example = SnapshotRequestTemplateExample()
        example.run()
    except Exception as e:  # pylint: disable=broad-except
        print(e)

__copyright__ = """
Copyright 2021, Bloomberg Finance L.P.

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
