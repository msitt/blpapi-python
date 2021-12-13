from argparse import Action
from collections import namedtuple
import datetime

REFDATA_SERVICE = "//blp/refdata"
INTRADAY_BAR_REQUEST = "IntradayBarRequest"
INTRADAY_TICK_REQUEST = "IntradayTickRequest"
REFERENCE_DATA_REQUEST = "ReferenceDataRequest"
REFERENCE_DATA_REQUEST_OVERRIDE = "ReferenceDataRequestOverride"
REFERENCE_DATA_REQUEST_TABLE_OVERRIDE = "ReferenceDataRequestTableOverride"
HISTORICAL_DATA_REQUEST = "HistoricalDataRequest"

# Defines a parameter override in a reference data request.
Override = namedtuple('Override', ['fieldId', 'value'])


class OverridesAction(Action):
    """The action that parses overrides options from user input"""

    def __call__(self, parser, args, values, option_string=None):
        vals = values.split('=', 1)
        overrides = getattr(args, self.dest)
        overrides.append(Override(vals[0], vals[1]))


def parseDatetime(value):
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def addRequestOptions(parser):
    """
    Helper function that adds the options that are used to
    create a blpapi request to the argument parser.
    """

    # Compute default start/end datetime
    defaultStartDateTime, defaultEndDateTime = computeDefaultStartAndEndDateTime()
    formattedDefaultStartDateTime = defaultStartDateTime.isoformat(
        timespec="seconds")
    formattedDefaultEndDateTime = defaultEndDateTime.isoformat(
        timespec="seconds")

    isoDatetimeFormat = "YYYY-MM-DDTHH:MM:SS"

    # Request options
    argGroupRequest = parser.add_argument_group("Request Options")
    argGroupRequest.add_argument("-s",
                                 "--service",
                                 dest="service",
                                 help="The service name (default: %(default)s)",
                                 metavar="service",
                                 default=REFDATA_SERVICE)
    argGroupRequest.add_argument("-S",
                                 "--security",
                                 dest="securities",
                                 help="Security to request. Can be specified multiple times.",
                                 metavar="security",
                                 action="append",
                                 default=[])
    argGroupRequest.add_argument("-f",
                                 "--field",
                                 dest="fields",
                                 help="Field to request. Can be specified multiple times.",
                                 metavar="field",
                                 action="append",
                                 default=[])
    argGroupRequest.add_argument("-e",
                                 "--event",
                                 dest="eventTypes",
                                 help="Event Type (default: ['TRADE']). Can be specified multiple times.",
                                 metavar="eventType",
                                 action="append",
                                 default=[])
    argGroupRequest.add_argument("-i",
                                 "--interval",
                                 dest="barInterval",
                                 type=int,
                                 help="Bar interval (default: %(default)d)",
                                 metavar="barInterval",
                                 default=60)
    argGroupRequest.add_argument("-I",
                                 "--include-condition-codes",
                                 dest="conditionCodes",
                                 help="Include condition codes",
                                 action='store_true',
                                 default=False)
    argGroupRequest.add_argument("-G",
                                 "--gap-fill-initial-bar",
                                 dest="gapFillInitialBar",
                                 help="Gap fill initial bar",
                                 action='store_true',
                                 default=False)
    argGroupRequest.add_argument("--start-date",
                                 dest="startDateTime",
                                 help="Start datetime in the format of "
                                 f"{isoDatetimeFormat} (default: {formattedDefaultStartDateTime})",
                                 metavar="startDateTime",
                                 type=parseDatetime,
                                 default=defaultStartDateTime)
    argGroupRequest.add_argument("--end-date",
                                 dest="endDateTime",
                                 help="End datetime in the format of "
                                 f"{isoDatetimeFormat} (default: {formattedDefaultEndDateTime})",
                                 metavar="endDateTime",
                                 type=parseDatetime,
                                 default=defaultEndDateTime)
    argGroupRequest.add_argument("-O",
                                 "--override",
                                 dest="overrides",
                                 help="Field to override. Can be specified multiple times.",
                                 metavar="<fieldId>=<value>",
                                 action=OverridesAction,
                                 default=[])
    argGroupRequest.add_argument("-r",
                                 "--request",
                                 dest="requestType",
                                 choices=[REFERENCE_DATA_REQUEST,
                                          REFERENCE_DATA_REQUEST_OVERRIDE,
                                          REFERENCE_DATA_REQUEST_TABLE_OVERRIDE,
                                          INTRADAY_BAR_REQUEST,
                                          INTRADAY_TICK_REQUEST,
                                          HISTORICAL_DATA_REQUEST],
                                 help=f"""Request Type (default: %(default)s)
To retrieve reference data:
    -r, --request {REFERENCE_DATA_REQUEST}
    [-S, --security <security = {{IBM US Equity, MSFT US Equity}}>]
    [-f, --field <field = PX_LAST>]
To retrieve reference data with overrides:
    -r, --request {REFERENCE_DATA_REQUEST_OVERRIDE}
    [-S, --security <security = {{IBM US Equity, MSFT US Equity}}>]
    [-f, --field <field = {{PX_LAST, DS002, EQY_WEIGHTED_AVG_PX}}>]
    [-O, --override <<fieldId>=<value> = {{VWAP_START_TIME=9:30, VWAP_END_TIME=11:30}}]
To retrieve reference data with table overrides:
    -r, --request {REFERENCE_DATA_REQUEST_TABLE_OVERRIDE}
    [-S, --security <security = FHR 3709 FA Mtge>]
    [-f, --field <field = {{MTG_CASH_FLOW, SETTLE_DT}}>]
To retrieve intraday bars:
    -r, --request {INTRADAY_BAR_REQUEST}
    [-S, --security <security = IBM US Equity>]
    [-e, --event <event = TRADE>]
    [-i, --interval <barInterval = 60>]
    [--start-date <startDateTime = {formattedDefaultStartDateTime}>]
    [--end-date <endDateTime = {formattedDefaultEndDateTime}>]
    [-G, --gap-fill-initial-bar]
        1) All times are in GMT.
        2) Only one security can be specified.
        3) Only one event can be specified.
To retrieve intraday raw ticks:
    -r, --request {INTRADAY_TICK_REQUEST}
    [-S, --security <security = IBM US Equity>]
    [-e, --event <event = TRADE>]
    [-i, --interval <barInterval = 60>]
    [--start-date <startDateTime = {formattedDefaultStartDateTime}>]
    [--end-date <endDateTime = {formattedDefaultEndDateTime}>]
    [--include-condition-codes <includeConditionCodes = false>]
        1) All times are in GMT.
        2) Only one security can be specified.
To retrieve historical data:
    -r, --request {HISTORICAL_DATA_REQUEST}
    [-S, --security <security = {{IBM US Equity, MSFT US Equity}}>]
    [-f, --field <field = PX_LAST>]""",
                                 metavar="requestType",
                                 default=REFERENCE_DATA_REQUEST)


def setDefaultValues(options):
    if not options.eventTypes:
        options.eventTypes = ["TRADE"]

    if not options.securities:
        if options.requestType == REFERENCE_DATA_REQUEST_TABLE_OVERRIDE:
            options.securities = ["FHR 3709 FA Mtge"]
        else:
            options.securities = ["IBM US Equity", "MSFT US Equity"]

    if not options.fields:
        if options.requestType == REFERENCE_DATA_REQUEST_TABLE_OVERRIDE:
            options.fields = ["MTG_CASH_FLOW", "SETTLE_DT"]
        else:
            options.fields = ["PX_LAST"]
            if options.requestType == REFERENCE_DATA_REQUEST_OVERRIDE:
                options.fields += ["DS002", "EQY_WEIGHTED_AVG_PX"]

    if not options.overrides and options.requestType is REFERENCE_DATA_REQUEST_OVERRIDE:
        options.overrides = [Override("VWAP_START_TIME", "9:30"),
                             Override("VWAP_END_TIME", "11:30")]

    startDatetime, endDatetime = computeDefaultStartAndEndDateTime()
    if not options.startDateTime:
        options.startDateTime = startDatetime

    if not options.endDateTime:
        options.endDateTime = endDatetime


def computeDefaultStartAndEndDateTime():
    today = datetime.datetime.today()
    previousTradingDate = today - datetime.timedelta(days=1)
    if datetime.date.weekday(previousTradingDate.date()) == 5:  # if Saturday
        previousTradingDate = previousTradingDate - datetime.timedelta(days=1)
    elif datetime.date.weekday(previousTradingDate.date()) == 6:  # if Sunday
        previousTradingDate = previousTradingDate - datetime.timedelta(days=2)

    previousTradingDate = previousTradingDate.replace(
        hour=13, minute=30, second=0)
    nextFiveMinutes = previousTradingDate + datetime.timedelta(minutes=5)

    return previousTradingDate, nextFiveMinutes


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
