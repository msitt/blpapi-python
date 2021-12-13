from argparse import ArgumentParser, RawTextHelpFormatter

from blpapi_import_helper import blpapi
from blpapi import Session, Names, CorrelationId
from util.ConnectionAndAuthOptions import \
    addConnectionAndAuthOptions, \
    createClientServerSetupAuthOptions, \
    createSessionOptions
from util.events.SessionRouter import SessionRouter

from functools import partial
from threading import Event as ThreadingEvent
from time import sleep

REFDATA_SVC_NAME = "//blp/refdata"


class UserModeExample:
    """User Mode Example"""

    def __init__(self, options):
        self._sessionTerminatedSignal = ThreadingEvent()
        self._router = SessionRouter()
        self._session = None
        self._options = options
        self._refDataService = None
        self._identitiesByCorrelationId = {}

        self._router.addExceptionHandler(self._handleException)

        self._router.addMessageHandlerByMessageType(
            Names.SESSION_STARTED, self._handleSessionStarted)
        self._router.addMessageHandlerByMessageType(
            Names.SESSION_STARTUP_FAILURE, self._handleSessionStartupFailure)
        self._router.addMessageHandlerByMessageType(
            Names.SESSION_TERMINATED, self._handleSessionTerminated)

        self._router.addMessageHandlerByMessageType(
            Names.SERVICE_OPENED, self._handleServiceOpened)
        self._router.addMessageHandlerByMessageType(
            Names.SERVICE_OPEN_FAILURE, self._handleServiceOpenFailure)

    @property
    def stopped(self):
        return self._sessionTerminatedSignal.is_set()

    def createAndStartSession(self):
        # Use the specified application as the session identity to
        # authorize. This may cause the session to stop and the example
        # to terminate, if the identity is revoked.
        sessionOptions = createSessionOptions(self._options)
        self._session = Session(sessionOptions, self._router.processEvent)
        self._session.startAsync()

    def _stop(self):
        # Cancel all the authorized identities
        self._session.cancel(self._identitiesByCorrelationId.keys())
        self._session.stopAsync()

    def _handleException(self, _session, _event, exception):
        print(exception)
        self._stop()

    def _handleSessionStarted(self,
                              _session: blpapi.AbstractSession,
                              _event: blpapi.Event,
                              _msg: blpapi.Message):

        # Add the authorization messages handlers after the session
        # started to only react to the authorization messages of users,
        # i.e., avoid those of the session identity.
        self._router.addMessageHandlerByMessageType(
            Names.AUTHORIZATION_SUCCESS, self._handleAuthorizationSuccess)
        self._router.addMessageHandlerByMessageType(
            Names.AUTHORIZATION_FAILURE, self._handleAuthorizationFailure)
        self._router.addMessageHandlerByMessageType(
            Names.AUTHORIZATION_REVOKED, self._handleAuthorizationRevoked)

        # both actions will run concurrently
        self._openServices()
        self._authorizeUsers()

    def _handleSessionStartupFailure(self,
                                     _session: blpapi.AbstractSession,
                                     _event: blpapi.Event,
                                     _msg: blpapi.Message):
        print("Failed to start session. Exiting...")
        self._sessionTerminatedSignal.set()

    def _handleSessionTerminated(self,
                                 _session: blpapi.AbstractSession,
                                 _event: blpapi.Event,
                                 _msg: blpapi.Message):
        print("Session terminated. Exiting...")
        self._sessionTerminatedSignal.set()

    def _handleServiceOpened(self,
                             session: blpapi.AbstractSession,
                             _event: blpapi.Event,
                             message: blpapi.Message):
        serviceName = message["serviceName"]
        self._refDataService = session.getService(serviceName)

        if serviceName == REFDATA_SVC_NAME:
            # it is possible that by now some identities are already authorised
            # we are sending a request on their behalf here
            for cid, identity in self._identitiesByCorrelationId.items():
                userIdentifier = cid.value()
                self._sendRefDataRequest(identity, userIdentifier)
        print(f"A service was opened: {serviceName}")

    def _handleServiceOpenFailure(self,
                                  _session: blpapi.AbstractSession,
                                  _event: blpapi.Event,
                                  message: blpapi.Message):
        serviceName = message["serviceName"]
        if serviceName == REFDATA_SVC_NAME:
            print(f"Failed to open service '{serviceName}', stopping...")
            self._stop()
            return

        raise RuntimeError(f"An unknown service failed to open: {serviceName}")

    def _handleAuthorizationSuccess(self,
                                    session: blpapi.AbstractSession,
                                    _event: blpapi.Event,
                                    message: blpapi.Message):
        correlationId = message.correlationId()
        userIdentifier = correlationId.value()
        print(f"Successfully authorized {userIdentifier}")

        identity = session.getAuthorizedIdentity(correlationId)
        self._identitiesByCorrelationId[correlationId] = identity

        if self._refDataService:
            # it is possible that the service is already open by now
            # in this case we must send the request on behalf of the identity
            userIdentifier = correlationId.value()
            self._sendRefDataRequest(identity, userIdentifier)
        else:
            pass # the request will be sent by open service handler

    def _handleAuthorizationFailure(self,
                                    _session: blpapi.AbstractSession,
                                    _event: blpapi.Event,
                                    message: blpapi.Message):
        correlationId = message.correlationId()
        self._router.removeMessageHandlerByCorrelationId(correlationId)

        userIdentifier = correlationId.value()
        print(f"Failed to authorize {userIdentifier}")

    def _handleAuthorizationRevoked(self,
                                    _session: blpapi.AbstractSession,
                                    _event: blpapi.Event,
                                    message: blpapi.Message):
        correlationId = message.correlationId()
        self._router.removeMessageHandlerByCorrelationId(correlationId)

        userIdentifier = correlationId.value()
        print(f"Authorization revoked for {userIdentifier}")

        # Remove the identity
        self._identitiesByCorrelationId.pop(correlationId, None)

    def _authorizeUsers(self):
        # Authorize each of the users
        authOptionsByIdentifier = createClientServerSetupAuthOptions(
            self._options)
        for userIdentifier, authOptions in authOptionsByIdentifier.items():
            correlationId = blpapi.CorrelationId(userIdentifier)
            self._session.generateAuthorizedIdentity(
                authOptions, correlationId)

    def _openServices(self):
        self._session.openServiceAsync(REFDATA_SVC_NAME)

    def _sendRefDataRequest(self, identity, userId):
        # To send a reference data request on behalf of a user
        # we need 1) the identity to be authorised 2) the service be opened.
        # Due to asynchronous nature of this example the messages
        # for successful service opening and successful authorization
        # may arrive in any possible order.
        # Hence, we call this method in both handlers.
        # For open service handler to cover the identities authorised (before),
        # and in authorization handler if the service is open (after).
        request = self._refDataService.createRequest("ReferenceDataRequest")
        requestDict = {
            "securities": self._options.securities,
            "fields": ["PX_LAST", "DS002"],
            "returnEids": True
        }

        request.fromPy(requestDict)

        print(f"Sending RefDataRequest on behalf of {userId}:\n{request}")
        correlationId = CorrelationId("example")
        self._router.addMessageHandlerByCorrelationId(
            correlationId,
            partial(UserModeExample._processResponseMessage, userId))
        self._session.sendRequest(request, identity, correlationId)

    @staticmethod
    def _processResponseMessage(userId,
                                _session: blpapi.Session,
                                _event: blpapi.Event,
                                message: blpapi.Message):
        if message.messageType() == Names.REQUEST_FAILURE:
            print(f"Request failed for {userId}.")
        else:
            print(f"Received response for {userId}.")


def parseCmdLine():
    """Parse command line arguments"""
    parser = ArgumentParser(
        description="User Mode Example",
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

    example = UserModeExample(options)
    example.createAndStartSession()

    # The main thread is not blocked and the example is running asynchronously.
    while not example.stopped:
        sleep(0.1)


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
