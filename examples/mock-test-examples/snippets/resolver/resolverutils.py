""" Sample utility functions for registering a service and handling permission
requests. """

import blpapi

# 'blpapi.Name' objects are more expensive to construct than `str`, but
# are more efficient on use through the interface. By creating the
# 'blpapi.Name' objects in advance we can take advantage of the efficiency
# without paying the cost of constructing them when needed.
PERMISSION_REQUEST = blpapi.Name("PermissionRequest")
PERMISSION_RESPONSE = blpapi.Name("PermissionResponse")
TOPIC = blpapi.Name("topic")
TOPICS = blpapi.Name("topics")
TOPIC_PERMISSION = blpapi.Name("topicPermissions")
RESULT = blpapi.Name("result")
REASON = blpapi.Name("reason")
SOURCE = blpapi.Name("source")
CATEGORY = blpapi.Name("category")
SUBCATEGORY = blpapi.Name("subcategory")
DESCRIPTION = blpapi.Name("description")

ALLOWED_APP_ID = 1234
RESOLVER_ID = "service:hostname"
# This can be any string, but it's helpful to provide information on the
# instance of the resolver that responded to debug failures in production.

def resolutionServiceRegistration(providerSession,
                                  providerIdentity,
                                  serviceName):
    """ This helper demonstrates how to register a service.

    This helper assumes the following:
    * Specified `providerSession` is already started
    * Specified `providerIdentity` is already authorized if auth is needed or
      default-constructed if authorization is not required.

    Args:
        providerSession (ProviderSession): The session to register services.
        providerIdentity (Identity): Identity used to verify permissions to
            provide the service being registered.
        serviceName (str): Name of the service.

    Returns:
        bool: True if service registration succeeds; False otherwise.
    """
    serviceOptions = blpapi.ServiceRegistrationOptions()

    dummyPriority = 123
    serviceOptions.setServicePriority(dummyPriority)

    serviceOptions.setPartsToRegister(
        blpapi.ServiceRegistrationOptions.PART_PUBLISHER_RESOLUTION)

    if not providerSession.registerService(serviceName,
                                           providerIdentity,
                                           serviceOptions):
        print("Failed to register {}".format(serviceName))
        return False

    return True

def handlePermissionRequest(providerSession, service, request):
    """ Respond to a PermissionRequest.

    Only accept requests with applicationId `ALLOWED_APP_ID`.
    """
    assert request.messageType() == PERMISSION_REQUEST

    disallowed = 1
    if request.hasElement("applicationId") and \
            request.getElementAsInteger("applicationId") == ALLOWED_APP_ID:
        disallowed = 0

    response = service.createResponseEvent(request.correlationIds()[0])
    formatter = blpapi.EventFormatter(response)
    formatter.appendResponse(PERMISSION_RESPONSE)

    topics = request.getElement(TOPICS)
    formatter.pushElement(TOPIC_PERMISSION)

    for i in range(topics.numValues()):
        formatter.appendElement()
        formatter.setElement(TOPIC, topics.getValueAsString(i))
        formatter.setElement(RESULT, disallowed)
        if disallowed:
            formatter.pushElement(REASON)
            formatter.setElement(SOURCE, RESOLVER_ID)
            formatter.setElement(CATEGORY, "NOT_AUTHORIZED")
            formatter.setElement(SUBCATEGORY, "")
            formatter.setElement(DESCRIPTION, "Only app 1234 allowed")
            formatter.popElement()
        formatter.popElement()

    formatter.popElement()

    providerSession.sendResponse(response)
    return True


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
