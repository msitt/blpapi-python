from blpapi_import_helper import blpapi

DEFAULT_SERVICE = "//blp/mktdata"
DEFAULT_TOPIC_PREFIX = "/ticker/"
DEFAULT_TOPIC = "IBM US Equity"


def addSubscriptionOptionsForSnapshot(parser):
    """
    Creates an instance for snapshot requests, which
    does not include interval option.
    """
    addSubscriptionOptions(parser, True)


def addSubscriptionOptions(parser, isSnapshot=False):
    """
    Helper function that adds the options for subscriptions to the argument
    parser.
    """
    subscription_group = parser.add_argument_group("Subscription Options")
    subscription_group.add_argument("-s",
                                    "--service",
                                    dest="service",
                                    help="service name (default: %(default)s)",
                                    metavar="service",
                                    default=DEFAULT_SERVICE)
    subscription_group.add_argument("-t",
                                    "--topic",
                                    dest="topics",
                                    help=f"""topic name (default: {DEFAULT_TOPIC}). Can be specified multiple times.
Can be one of the following:
* Instrument
* Instrument qualified with a prefix
* Instrument qualified with a service and a prefix
                                    """,
                                    metavar="topic",
                                    action="append",
                                    default=[])
    subscription_group.add_argument("-f",
                                    "--field",
                                    dest="fields",
                                    help="field to subscribe. Can be specified multiple times.",
                                    metavar="field",
                                    action="append",
                                    default=[])
    subscription_group.add_argument("-o",
                                    "--option",
                                    dest="options",
                                    help="subscription options. Can be specified multiple times.",
                                    metavar="option",
                                    action="append",
                                    default=[])
    subscription_group.add_argument("-x",
                                    "--topic-prefix",
                                    dest="topicPrefix",
                                    help="The topic prefix to be used for subscriptions (default: %(default)s)",
                                    metavar="prefix",
                                    default=DEFAULT_TOPIC_PREFIX)

    if not isSnapshot:
        subscription_group.add_argument("-i",
                                        "--interval",
                                        dest="interval",
                                        type=float,
                                        help="subscription option that specifies a time in seconds to "
                                             "intervalize the subscriptions",
                                        metavar="interval")


def setSubscriptionSessionOptions(sessionOptions, options):
    sessionOptions.setDefaultSubscriptionService(options.service)
    sessionOptions.setDefaultTopicPrefix(options.topicPrefix)


def createSubscriptionList(options):
    """
    Creates a SubscriptionList from the following command line arguments:
    - topic names
    - service name
    - fields to subscribe to
    - subscription options
    - subscription interval
    """
    if not options.topics:
        options.topics = [DEFAULT_TOPIC]

    if options.interval:
        options.options.append(f"interval={options.interval}")

    subscriptions = blpapi.SubscriptionList()
    for topic in options.topics:
        subscriptions.add(topic,
                          options.fields,
                          options.options,
                          blpapi.CorrelationId(topic))
    return subscriptions


def createSubscriptionStrings(options):
    """
    Creates a dict from the topics provided on the command line to their
    corresponding subscription strings.
    """
    if not options.topics:
        options.topics = [DEFAULT_TOPIC]

    subscriptionStrings = {}

    # Use SubscriptionList to help construct the subscription string
    subscriptionList = blpapi.SubscriptionList()
    for i, userTopic in enumerate(options.topics):
        subscriptionList.add(userTopic, options.fields, options.options)
        subscriptionStrings[userTopic] = subscriptionList.topicStringAt(i)
        print(f"topic: {userTopic} -> subscription string: "
              f"{subscriptionStrings[userTopic]}")

    return subscriptionStrings


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
