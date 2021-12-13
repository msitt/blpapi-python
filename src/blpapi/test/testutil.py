# testutil.py

"""  This module provides a set of utility functions to allow SDK clients to
create events/messages for unit-testing their applications.
"""

from blpapi import internals
from blpapi import Event, Name, SchemaElementDefinition, Service, Topic
from blpapi.compat import conv2str, isstr
from blpapi.exception import _ExceptionUtil
from blpapi.utils import get_handle
from blpapi.test import MessageProperties, MessageFormatter


def createEvent(eventType):
    """ Create an :class:`blpapi.Event` with the specified ``eventType`` to be
    used for testing.

    Args:
        eventType (int): Specifies the type of event. See :class:`blpapi.Event`
            for a list of enumerated values (e.g., `Event.SUBSCRIPTION_DATA`).

    Returns:
        blpapi.Event: An event used for testing. It cannot be used for
        publishing.

    The behavior is undefined if :class:`blpapi.EventFormatter` is
    used with the returned :class:`blpapi.Event`.
    """
    rc, event_handle = internals.blpapi_TestUtil_createEvent(eventType)
    _ExceptionUtil.raiseOnError(rc)
    event = Event(event_handle, sessions=None)
    return event

def appendMessage(event, elementDef, properties=None):
    """ Create a new message and append it to the specified ``event``.
    Return a :class:`MessageFormatter` to format the last appended message.

    Args:
        event (blpapi.Event): The ``event`` to which the new message will
            be appended. The ``event`` must be a test :class:`blpapi.Event`
            created by :meth:`createEvent()`.
        elementDef (blpapi.SchemaElementDefinition): Used to verify and encode
            the contents of the message.
        properties (blpapi.test.MessageProperties): Used to set the metadata
            properties for the message.

    Returns:
        blpapi.test.MessageFormatter: The :class:`MessageFormatter` used to
        format the last appended message.

    Raises:
        Exception: If the method fails to append the message.
    """
    if properties is None:
        properties = MessageProperties()
    rc, formatter_handle = internals.blpapi_TestUtil_appendMessage(
        get_handle(event),
        get_handle(elementDef),
        get_handle(properties))
    _ExceptionUtil.raiseOnError(rc)
    message_formatter = MessageFormatter(formatter_handle)
    return message_formatter

def deserializeService(serviceXMLStr):
    """ Create a :class:`blpapi.Service` instance from the specified
    ``serviceXMLStr``.

    Args:
        serviceXMLStr (str): A ``str`` representation of a
            :class:`blpapi.Service` in ``XML`` format. The ``str`` should only
            contain ASCII characters without any embedded ``null`` characters.
    Returns:
        blpapi.Service: A :class:`blpapi.Service` created from
        ``serviceXMLStr``.

    Raises:
        Exception: If deserialization fails.
    """
    rc, service_handle = internals.blpapi_TestUtil_deserializeService(
        serviceXMLStr,
        len(serviceXMLStr))
    _ExceptionUtil.raiseOnError(rc)
    service = Service(service_handle, sessions=None)
    return service

def serializeService(service):
    """ Serialize the provided ``service`` in ``XML`` format.

    Args:
        service (blpapi.Service): The :class:`blpapi.Service` to be serialized.

    Returns:
        str: The ``service`` represented as an ``XML`` formatted ``str``.

    Raises:
        Exception: If the service can't be serialized successfully.
    """
    service_str = internals.blpapi_TestUtil_serializeServiceHelper(
        get_handle(service))
    return service_str

def createTopic(service, isActive=True):
    """ Create a valid :class:`blpapi.Topic` with the specified ``service`` to
    support testing publishers. The expected use case is to support returning a
    custom :class:`blpapi.Topic` while mocking
    :meth:`blpapi.ProviderSession.getTopic()` methods.

    Args:
        service (blpapi.Service): The :class:`blpapi.Service` to which the
            returned :class:`blpapi.Topic` will belong.
        isActive (bool): Optional. Specifies whether the returned
            :class:`blpapi.Topic` is active.

    Returns:
        blpapi.Topic: A valid :class:`blpapi.Topic` with the specified
        ``service``.
    """
    rc, topic_handle = internals.blpapi_TestUtil_createTopic(
        get_handle(service),
        isActive)
    _ExceptionUtil.raiseOnError(rc)
    topic = Topic(topic_handle, sessions=None)
    return topic

def getAdminMessageDefinition(messageName):
    """ Return the definition for an admin message of the specified
    ``messageName``.

    Args:
        messageName (blpapi.Name or str): The name of the desired admin message.

    Returns:
        blpapi.SchemaElementDefinition: The element definition for the message
        specified by ``messageName``.

    Raises:
        Exception: If ``messageName`` does not name an admin message.
    """
    if isstr(messageName):
        messageName = Name(conv2str(messageName))
    rc, schema_element_definition_handle = \
        internals.blpapi_TestUtil_getAdminMessageDefinition(
            get_handle(messageName))
    _ExceptionUtil.raiseOnError(rc)
    schema_definition = \
        SchemaElementDefinition(schema_element_definition_handle, sessions=None)
    return schema_definition


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
