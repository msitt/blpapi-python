"""
Provides 'Name' constants for common message types.
"""

from .name import Name


class Names:
    """
    Provides 'Name' constants for common message types.
    """

    SLOW_CONSUMER_WARNING = Name("SlowConsumerWarning")
    SLOW_CONSUMER_WARNING_CLEARED = Name("SlowConsumerWarningCleared")
    DATA_LOSS = Name("DataLoss")
    REQUEST_TEMPLATE_AVAILABLE = Name("RequestTemplateAvailable")
    REQUEST_TEMPLATE_PENDING = Name("RequestTemplatePending")
    REQUEST_TEMPLATE_TERMINATED = Name("RequestTemplateTerminated")
    SUBSCRIPTION_TERMINATED = Name("SubscriptionTerminated")
    SUBSCRIPTION_STARTED = Name("SubscriptionStarted")
    SUBSCRIPTION_FAILURE = Name("SubscriptionFailure")
    SUBSCRIPTION_STREAMS_ACTIVATED = Name("SubscriptionStreamsActivated")
    SUBSCRIPTION_STREAMS_DEACTIVATED = Name("SubscriptionStreamsDeactivated")
    REQUEST_FAILURE = Name("RequestFailure")
    TOKEN_GENERATION_SUCCESS = Name("TokenGenerationSuccess")
    TOKEN_GENERATION_FAILURE = Name("TokenGenerationFailure")
    SESSION_STARTED = Name("SessionStarted")
    SESSION_TERMINATED = Name("SessionTerminated")
    SESSION_STARTUP_FAILURE = Name("SessionStartupFailure")
    SESSION_CONNECTION_UP = Name("SessionConnectionUp")
    SESSION_CONNECTION_DOWN = Name("SessionConnectionDown")
    SESSION_CLUSTER_INFO = Name("SessionClusterInfo")
    SESSION_CLUSTER_UPDATE = Name("SessionClusterUpdate")
    SERVICE_OPENED = Name("ServiceOpened")
    SERVICE_OPEN_FAILURE = Name("ServiceOpenFailure")
    SERVICE_REGISTERED = Name("ServiceRegistered")
    SERVICE_REGISTER_FAILURE = Name("ServiceRegisterFailure")
    SERVICE_DEREGISTERED = Name("ServiceDeregistered")
    SERVICE_UP = Name("ServiceUp")
    SERVICE_DOWN = Name("ServiceDown")
    SERVICE_AVAILABILITY_INFO = Name("ServiceAvailabilityInfo")
    RESOLUTION_SUCCESS = Name("ResolutionSuccess")
    RESOLUTION_FAILURE = Name("ResolutionFailure")
    TOPIC_SUBSCRIBED = Name("TopicSubscribed")
    TOPIC_UNSUBSCRIBED = Name("TopicUnsubscribed")
    TOPIC_RECAP = Name("TopicRecap")
    TOPIC_ACTIVATED = Name("TopicActivated")
    TOPIC_DEACTIVATED = Name("TopicDeactivated")
    TOPIC_CREATED = Name("TopicCreated")
    TOPIC_CREATE_FAILURE = Name("TopicCreateFailure")
    TOPIC_DELETED = Name("TopicDeleted")
    TOPIC_RESUBSCRIBED = Name("TopicResubscribed")
    PERMISSION_REQUEST = Name("PermissionRequest")
    PERMISSION_RESPONSE = Name("PermissionResponse")
    AUTHORIZATION_SUCCESS = Name("AuthorizationSuccess")
    AUTHORIZATION_FAILURE = Name("AuthorizationFailure")
    AUTHORIZATION_REVOKED = Name("AuthorizationRevoked")


__copyright__ = """
Copyright 2021. Bloomberg Finance L.P.

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
