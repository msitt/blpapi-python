from typing import Callable
from blpapi_import_helper import blpapi


def printEvent(event: blpapi.Event):
    for message in event:
        service = message.service()
        if service:
            print(f"Service: {service.name()}")
        print(message)


class SessionRouter:

    EventHandler = Callable[[blpapi.AbstractSession, blpapi.Event], None]
    MessageHandler = Callable[[blpapi.AbstractSession, blpapi.Event, blpapi.Message], None]
    ExceptionHandler = Callable[[blpapi.AbstractSession, blpapi.Event, Exception], None]

    def __init__(self):
        super(SessionRouter, self).__init__()
        self._eventHandlersByEventType = {}
        self._messageHandlersByEventType = {}
        self._messageHandlersByMessageType = {}
        self._messageHandlersByCorrelationId = {}
        self._exceptionHandlers = []

    def processEvent(self,
                     event: blpapi.Event,
                     session: blpapi.AbstractSession):
        try:
            printEvent(event)

            eventHandler = self._eventHandlersByEventType.get(event.eventType())
            if eventHandler is not None:
                eventHandler(session, event)

            eventTypeMessageHandler = \
                self._messageHandlersByEventType.get(event.eventType())

            for message in event:
                for cid in message.correlationIds():
                    cidMessageHandler = self._messageHandlersByCorrelationId.get(cid)
                    if cidMessageHandler is not None:
                        cidMessageHandler(session, event, message)

                if eventTypeMessageHandler is not None:
                    eventTypeMessageHandler(session, event, message)

                messageTypeMessageHandler = \
                    self._messageHandlersByMessageType.get(message.messageType())
                if messageTypeMessageHandler is not None:
                    messageTypeMessageHandler(session, event, message)
        except Exception as exception:  # pylint: disable=broad-except
            for exceptionHandler in self._exceptionHandlers:
                exceptionHandler(session, event, exception)

    def addEventHandlerByEventType(self,
                                   eventType: int,
                                   eventHandler: EventHandler):
        self._eventHandlersByEventType[eventType] = eventHandler

    def addMessageHandlerByEventType(self,
                                     eventType: int,
                                     messageHandler: MessageHandler):
        self._messageHandlersByEventType[eventType] = messageHandler

    def addMessageHandlerByMessageType(self,
                                       messageType: blpapi.Name,
                                       messageHandler: MessageHandler):
        self._messageHandlersByMessageType[messageType] = messageHandler

    def addMessageHandlerByCorrelationId(self,
                                         correlationId: blpapi.CorrelationId,
                                         messageHandler: MessageHandler):
        self._messageHandlersByCorrelationId[correlationId] = messageHandler

    def addExceptionHandler(self, exceptionHandler: ExceptionHandler):
        self._exceptionHandlers.append(exceptionHandler)

    def removeMessageHandlerByCorrelationId(self,
                                            correlationId: blpapi.CorrelationId):
        self._messageHandlersByCorrelationId.pop(correlationId, None)


__copyright__ = """
Copyright 2021, Bloomberg Finance L.P.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions: The above copyright
notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
"""
