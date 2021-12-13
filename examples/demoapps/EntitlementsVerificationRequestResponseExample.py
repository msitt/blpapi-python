from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi
from blpapi import CorrelationId, Event, Name, Names, Session
from util.ConnectionAndAuthOptions import \
    addConnectionAndAuthOptions, \
    createClientServerSetupAuthOptions, \
    createSessionOptions
from util.events.SessionRouter import SessionRouter
from threading import Event as ThreadingEvent
from time import sleep

REFDATA_SVC_NAME = "//blp/refdata"

RESPONSE_ERROR = Name("responseError")
SECURITY_DATA = Name("securityData")
SECURITY = Name("security")
EID_DATA = Name("eidData")
ENTITLEMENT_CHANGED = Name("EntitlementChanged")


class EntitlementsVerificationRequestResponseExample:

    def __init__(self, options):
        self._options = options
        self._router = SessionRouter()
        self._exampleStoppedThreadingEvent = ThreadingEvent()
        self._identitiesByCorrelationId = {}
        self._responses = []
        self._finalResponseReceived = False

        self._router.addExceptionHandler(self._handleException)

        self._router.addMessageHandlerByMessageType(
            Names.SESSION_STARTED, self._handleSessionStarted)
        self._router.addMessageHandlerByMessageType(
            Names.SESSION_STARTUP_FAILURE,
            self._handleSessionStartupFailure)
        self._router.addMessageHandlerByMessageType(
            Names.SESSION_TERMINATED, self._handleSessionTerminated)

        self._router.addMessageHandlerByMessageType(
            Names.SERVICE_OPENED, self._handleServiceOpened)
        self._router.addMessageHandlerByMessageType(
            Names.SERVICE_OPEN_FAILURE, self._handleServiceOpenFailure)
        self._router.addMessageHandlerByMessageType(
            ENTITLEMENT_CHANGED, self._handleEntitlementChanged)

    @property
    def stopped(self):
        return self._exampleStoppedThreadingEvent.is_set()

    def createAndStartSession(self):
        # Use the specified application as the session identity to
        # authorize. This may cause the session to stop and the example
        # to terminate if the identity is revoked.
        sessionOptions = createSessionOptions(self._options)
        session = Session(sessionOptions, self._router.processEvent)
        session.startAsync()

    def _stop(self, session):
        # Cancel all the authorized identities
        session.cancel(self._identitiesByCorrelationId.keys())
        session.stopAsync()

    def _handleException(self, session, _2, exception):
        print(exception)
        self._stop(session)

    def _handleSessionStarted(self, session, _1, _2):

        # Add the authorization message handlers after the session
        # started to only react to the authorization messages of users,
        # i.e., avoid those of the session identity.
        self._router.addMessageHandlerByMessageType(
            Names.AUTHORIZATION_SUCCESS,
            self._handleAuthorizationSuccess)
        self._router.addMessageHandlerByMessageType(
            Names.AUTHORIZATION_FAILURE,
            self._handleAuthorizationFailure)
        self._router.addMessageHandlerByMessageType(
            Names.AUTHORIZATION_REVOKED,
            self._handleAuthorizationRevoked)

        self._authorizeUsers(session)
        self._openServices(session)

    def _handleSessionStartupFailure(self, _1, _2, _3):
        print("Failed to start session. Exiting...")
        self._exampleStoppedThreadingEvent.set()

    def _handleSessionTerminated(self, _1, _2, _3):
        print("Session terminated. Exiting...")
        self._exampleStoppedThreadingEvent.set()

    @staticmethod
    def _openServices(session):
        session.openServiceAsync(REFDATA_SVC_NAME)

    def _handleServiceOpened(self, session, _1, message):
        serviceName = message["serviceName"]
        service = session.getService(serviceName)

        if serviceName == REFDATA_SVC_NAME:
            self._sendRefDataRequest(session, service)
            return

    def _handleServiceOpenFailure(self, session, _1, message):
        serviceName = message["serviceName"]
        if serviceName == REFDATA_SVC_NAME:
            print(f"Failed to open service '{serviceName}', stopping...")
            self._stop(session)
            return

        raise RuntimeError(f"A unknown service failed to open: {serviceName}")

    def _sendRefDataRequest(self, session, refDataService):
        request = refDataService.createRequest("ReferenceDataRequest")
        requestDict = {
            "securities": self._options.securities,
            "fields": ["PX_LAST", "DS002"],
            "returnEids": True
        }

        request.fromPy(requestDict)

        print(f"Sending RefDataRequest {request}")
        correlationId = CorrelationId("example")
        self._router.addMessageHandlerByCorrelationId(
            correlationId, self._processResponseMessage)
        session.sendRequest(request, correlationId=correlationId)

    def _processResponseMessage(self, session, event, message):
        if message.messageType() == Names.REQUEST_FAILURE:
            print("Request failed, stopping...")
            self._stop(session)
            return

        if event.eventType() == Event.PARTIAL_RESPONSE:
            print("Received partial response")

            # Save the response
            self._responses.append(event)
        elif event.eventType() == Event.RESPONSE:
            print("Received final response")
            self._finalResponseReceived = True

            # Save the response
            self._responses.append(event)

            # Distributes all the cached responses to the identities that have
            # been authorized so far.
            for correlationId, identity in self._identitiesByCorrelationId.items():
                userIdentifier = correlationId.value()
                self._distributeResponses(userIdentifier, identity)

    def _authorizeUsers(self, session):
        # Authorize each of the users
        authOptionsByIdentifier = createClientServerSetupAuthOptions(
            self._options)
        for userIdentifier, authOptions in authOptionsByIdentifier.items():
            correlationId = blpapi.CorrelationId(userIdentifier)
            session.generateAuthorizedIdentity(authOptions, correlationId)

    def _handleAuthorizationSuccess(self, session, _1, message):
        correlationId = message.correlationId()
        userIdentifier = correlationId.value()
        print(f"Successfully authorized {userIdentifier}")
        identity = session.getAuthorizedIdentity(correlationId)
        self._identitiesByCorrelationId[correlationId] = identity

        if self._finalResponseReceived:
            self._distributeResponses(userIdentifier, identity)

    def _handleAuthorizationFailure(self, _1, _2, message):
        correlationId = message.correlationId()
        self._router.removeMessageHandlerByCorrelationId(correlationId)

        userIdentifier = correlationId.value()
        print(f"Failed to authorize {userIdentifier}")

    def _handleAuthorizationRevoked(self, _1, _2, message):
        correlationId = message.correlationId()
        self._router.removeMessageHandlerByCorrelationId(correlationId)

        userIdentifier = correlationId.value()
        print(f"Authorization revoked for {userIdentifier}")

        # Remove the identity
        self._identitiesByCorrelationId.pop(correlationId, None)

    def _handleEntitlementChanged(self, _1, _2, message):
        # This is just informational. Continue to use existing identity.
        correlationId = message.correlationId()
        userIdentifier = correlationId.value()
        print(f"Entitlements updated for {userIdentifier}")

    def _distributeResponses(self, userIdentifier, identity):
        for event in self._responses:
            self._distributeResponse(event, userIdentifier, identity)

    def _distributeResponse(self, event, userIdentifier, identity):

        for msg in event:
            if msg.hasElement(RESPONSE_ERROR, excludeNullElements=True):
                continue

            service = msg.service()
            securityDataElement = msg[SECURITY_DATA]

            print(f"Processing {securityDataElement.numValues()} securities:")
            for securityData in securityDataElement:
                ticker = securityData[SECURITY]

                if securityData.hasElement(EID_DATA, excludeNullElements=True):
                    # Entitlements are required to access this data
                    entitlements = securityData[EID_DATA]

                    entitled, failedEntitlements = identity.getFailedEntitlements(
                        service,
                        entitlements)
                    if entitled:
                        print(f"{userIdentifier} is entitled to get data "
                              f"for: {ticker}")

                        # Now Distribute message to the user.
                    else:
                        print(f"{userIdentifier} is NOT entitled to get "
                              f"data for: {ticker} - Failed EIDs: {failedEntitlements}")
                else:
                    print(f"No entitlements are required for: {ticker}")

                    # Now Distribute message to the user.


def parseCmdLine():
    parser = ArgumentParser(
        description="Entitlements Verification Request/Response Example",
        formatter_class=RawTextHelpFormatter)
    addConnectionAndAuthOptions(parser, forClientServerSetup=True)

    parser.add_argument("-S", "--security",
                        dest="securities",
                        help="security used in ReferenceDataRequest (default:"
                        " IBM US Equity). Can be specified multiple times",
                        metavar="security",
                        action="append",
                        default=[])

    options = parser.parse_args()

    if not options.securities:
        options.securities.append("IBM US Equity")

    if not options.userIdAndIps and not options.tokens:
        parser.error("No userId:IP or token specified")

    return options


def main():
    options = parseCmdLine()

    example = EntitlementsVerificationRequestResponseExample(options)
    example.createAndStartSession()

    # The main thread is not blocked and the example is running asynchronously.
    while not example.stopped:
        sleep(1)


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
