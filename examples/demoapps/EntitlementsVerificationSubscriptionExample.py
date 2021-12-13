from argparse import ArgumentParser, RawTextHelpFormatter
from threading import Event as ThreadingEvent
import time

from blpapi_import_helper import blpapi
from blpapi import AbstractSession, Message, Name, Names, Session
from util.ConnectionAndAuthOptions import \
    addConnectionAndAuthOptions, \
    createClientServerSetupAuthOptions, \
    createSessionOptions
from util.SubscriptionOptions import \
    addSubscriptionOptions, \
    createSubscriptionList
from util.events.SessionRouter import SessionRouter


EID = Name("EID")
ENTITLEMENT_CHANGED = Name("EntitlementChanged")


def parseCmdLine():
    parser = ArgumentParser(
            formatter_class=RawTextHelpFormatter,
            description="Entitlements verification subscription example")
    addConnectionAndAuthOptions(parser, forClientServerSetup=True)
    addSubscriptionOptions(parser)

    options = parser.parse_args()

    if not options.userIdAndIps and not options.tokens:
        parser.error("No userId:IP or token specified")

    if str(EID) not in options.fields:
        options.fields.append(str(EID))

    return options


class EntitlementsVerificationSubscriptionExample:

    def __init__(self, options):
        self._options = options
        self._router = SessionRouter()
        self._exampleStoppedThreadingEvent = ThreadingEvent()
        self._identitiesByCorrelationId = {}
        self._session = None

        self._router.addExceptionHandler(self._handleException)

        self._router.addMessageHandlerByMessageType(Names.SESSION_STARTED,
                                                    self._handleSessionStarted)
        self._router.addMessageHandlerByMessageType(Names.SESSION_STARTUP_FAILURE,
                                                    self._handleSessionStartupFailure)
        self._router.addMessageHandlerByMessageType(Names.SESSION_TERMINATED,
                                                    self._handleSessionTerminated)
        self._router.addMessageHandlerByMessageType(Names.SERVICE_OPENED,
                                                    self._handleServiceOpened)
        self._router.addMessageHandlerByMessageType(Names.SERVICE_OPEN_FAILURE,
                                                    self._handleServiceOpenFailure)
        self._router.addMessageHandlerByMessageType(Name("EntitlementChanged"),
                                                    self._handleEntitlementChanged)

    @property
    def stopped(self):
        return self._exampleStoppedThreadingEvent.is_set()

    def run(self):
        self._createAndStartSession()

    def _createAndStartSession(self):
        # Use the specified application as the session identity to authorize.
        # This may cause the session to stop and the example to terminate if
        # the identity is revoked.
        sessionOptions = createSessionOptions(self._options)
        self._session = Session(sessionOptions, self._router.processEvent)
        self._session.startAsync()

    def _openServices(self):
        self._session.openServiceAsync(self._options.service)

    def _authorizeUsers(self):
        # Authorize each of the users
        authOptionsByIdentifier = \
            createClientServerSetupAuthOptions(self._options)

        for identifier, authOptions in authOptionsByIdentifier.items():
            cid = blpapi.CorrelationId(identifier)
            self._session.generateAuthorizedIdentity(authOptions, cid)

    def _subscribe(self):
        self._router.addMessageHandlerByEventType(blpapi.Event.SUBSCRIPTION_DATA,
                                                  self._handleSubscriptionData)
        self._router.addMessageHandlerByMessageType(Names.SUBSCRIPTION_FAILURE,
                                                    self._handleSubscriptionFailure)
        self._router.addMessageHandlerByMessageType(Names.SUBSCRIPTION_TERMINATED,
                                                    self._handleSubscriptionTerminated)

        print("Subscribing...")
        subscriptionList = createSubscriptionList(self._options)
        self._session.subscribe(subscriptionList)

    def _handleException(self, _1, _2, exception: Exception):
        print(exception)
        self._stop()

    def _handleSessionStarted(self, *_):
        # Add the authorization messages handlers after the session
        # started to only react to the authorization messages of users,
        # i.e., avoid those of the session identity.
        self._router.addMessageHandlerByMessageType(Names.AUTHORIZATION_SUCCESS,
                                                    self._handleAuthorizationSuccess)
        self._router.addMessageHandlerByMessageType(Names.AUTHORIZATION_FAILURE,
                                                    self._handleAuthorizationFailure)
        self._router.addMessageHandlerByMessageType(Names.AUTHORIZATION_REVOKED,
                                                    self._handleAuthorizationRevoked)

        self._authorizeUsers()
        self._openServices()

    def _handleSessionStartupFailure(self, *_):
        print("Failed to start session. Exiting...")
        self._exampleStoppedThreadingEvent.set()

    def _handleSessionTerminated(self, *_):
        print("Session terminated. Exiting...")
        self._exampleStoppedThreadingEvent.set()

    def _handleServiceOpened(self, _1, _2, message: Message):
        serviceName = message.getElementAsString("serviceName")
        if serviceName == self._options.service:
            self._subscribe()
        else:
            print(f"A service was opened: {serviceName}")

    def _stop(self):
        # Cancel all the authorized identities
        self._session.cancel(list(self._identitiesByCorrelationId.keys()))

        try:
            self._session.stopAsync()
        except InterruptedError as exc:
            print(exc)

    def _handleServiceOpenFailure(self, _1, _2, message: Message):
        serviceName = message.getElementAsString("serviceName")
        if serviceName == self._options.service:
            self._stop()
        else:
            raise Exception(f"A service which is unknown failed to open: {serviceName}")

    @staticmethod
    def _handleEntitlementChanged(_1, _2, message: Message):
        # This is just informational. Continue to use existing identity.
        correlationId = message.correlationId()
        userIdentifier = correlationId.value()
        print(f"Entitlements updated for {userIdentifier}")

    def _handleSubscriptionData(self, _1, _2, message: Message):
        topic = message.correlationId().value()

        service = message.service()

        if message.hasElement(EID, excludeNullElements=True):
            entitlements = message.getElement(EID)

            for cid, identity in self._identitiesByCorrelationId.items():
                userIdentifier = cid.value()
                isAuthorizedForAllEntitlements, failedEntitlements = \
                    identity.getFailedEntitlements(service, entitlements)
                if isAuthorizedForAllEntitlements:
                    print(f"{userIdentifier} is entitled to get data for: {topic}")

                    # Now distribute the message to the user.
                else:
                    print(f"{userIdentifier} is NOT entitled to get data for: "
                          f"{topic} - Failed eids: {failedEntitlements}")

        else:
            print(f"No entitlements are required for: {topic}")

            # Now distribute the message to the authorized users.

        print()

    @staticmethod
    def _handleSubscriptionFailure(_1, _2, message: Message):
        topic = message.correlationId().value()
        print(f"Subscription failed: {topic}")

    @staticmethod
    def _handleSubscriptionTerminated(_1, _2, message: Message):
        topic = message.correlationId().value()
        print(f"Subscription terminated: {topic}")

    def _handleAuthorizationSuccess(self,
                                    session: AbstractSession,
                                    _,
                                    message: Message):
        correlationId = message.correlationId()
        userIdentifier = correlationId.value()
        print(f"Successfully authorized {userIdentifier}")
        identity = session.getAuthorizedIdentity(correlationId)
        self._identitiesByCorrelationId[correlationId] = identity

        # Deliver init paint to the user. For the purpose of simplicity,
        # this example doesn't maintain an init paint cache.

    def _handleAuthorizationFailure(self, _1, _2, message: Message):
        correlationId = message.correlationId()
        self._router.removeMessageHandlerByCorrelationId(correlationId)

        userIdentifier = correlationId.value()
        print(f"Failed to authorize {userIdentifier}")

    def _handleAuthorizationRevoked(self, _1, _2, message: Message):
        correlationId = message.correlationId()
        self._router.removeMessageHandlerByCorrelationId(correlationId)

        userIdentifier = correlationId.value()
        print(f"Authorization revoked for {userIdentifier}: {message}")

        # Remove the identity
        del self._identitiesByCorrelationId[correlationId]


def main():
    options = parseCmdLine()

    example = EntitlementsVerificationSubscriptionExample(options)
    example.run()

    # The main thread is not blocked while the example runs asynchronously.
    while not example.stopped:
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
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
