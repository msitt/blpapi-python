# BLPAPI Examples
| Example | Keywords |
|---------|----------|
| [ApiFieldsExample](#apifieldsexample) | `apiflds`, `fields`, `request` |
| [BroadcastPublisherExample](#broadcastpublisherexample) | `publisher` |
| [ContributionsExample](#contributionsexample) | `contributions` |
| [EntitlementsVerificationSubscriptionExample](#entitlementsverificationsubscriptionexample) | `asynchronous`, `subscription`, `client-server` |
| [EntitlementsVerificationRequestResponseExample](#entitlementsverificationrequestresponseexample) | `asynchronous`, `request`, `client-server` |
| [GenerateTokenExample](#generatetokenexample) | `token`, `client-server` |
| [InteractivePublisherExample](#interactivepublisherexample) | `publisher` |
| [MultipleRequestsOverrideExample](#multiplerequestsoverrideexample) | `request`, `overrides` |
| [RequestResponseExample](#requestresponseexample) | `request`, `refdata`, `overrides`, `historical`, `intraday` |
| [RequestServiceConsumerExample](#requestserviceconsumerexample) | `request`, `custom service` |
| [RequestServiceProviderExample](#requestserviceproviderexample) | `response`, `custom service` |
| [SecurityLookupExample](#securitylookupexample) | `request`, `instruments` |
| [SnapshotRequestTemplateExample](#snapshotrequesttemplateexample) | `snapshot`, `subscription` |
| [SubscriptionExample](#subscriptionexample) | `asynchronous`, `subscription` |
| [SubscriptionWithEventPollingExample](#subscriptionwitheventpollingexample) | `synchronous`, `subscription` |
| [UserModeExample](#usermodeexample) | `asynchronous`, `request`, `client-server` |


## ApiFieldsExample
---
Sends a request for the fields available for accessing market data and reference data.

#### Useful for

- Discovering available fields when subscribing to market data or making requests for reference data.

#### Sample Arguments

`-H  <host>:<ip> --auth <auth> --request <requestType>`

There are 4 types of requests: CategorizedFieldSearchRequest, FieldInfoRequest, FieldListRequest, and FieldSearchRequest.

## BroadcastPublisherExample
---
Demonstrates a broadcast publisher that publishes data regardless of whether there are active subscriptions or not. By default, market data is published. Page data can be published with the `--page` option.

#### Useful for

- Creating services that publish data regardless of whether there are active subscriptions, e.g. alerting

#### Sample Arguments
`-H  <host>:<ip> -s <service> --auth <auth>`

`-H  <host>:<ip> -s <service> --auth <auth> --page --max-events <max>`

## ContributionsExample
---
Demonstrates contributing your own data to Bloomberg.

#### Sample Arguments
`-H <host:port> -s <service> --auth <auth>`

Contribute page data by adding the flag `--page`

## EntitlementsVerificationSubscriptionExample
---
Subscribes to data and redistributes it to entitled users, all in an asychronous manner.

#### Useful for

- Using the SDK asynchronously (with an Event Handler)
- Creating a client-server setup
- Getting data once and fanning it out to other users

#### Sample Arguments
`-H <host:port> --auth <auth> -u <user> -u <user> --token=<token> -f BID -f ASK`

## EntitlementsVerificationRequestResponseExample
---
An asynchronous redistribution example where an app requests data and redistributes the response to entitled users.

#### Useful for

- Using the SDK asynchronously (with an Event Handler)
- Creating a client-server setup
- Getting data once and fanning it out to other users

#### Sample Arguments
`-H <host:port> --auth <auth> -S <security> -u <user> -S <security> -u <user> -u <user> -T <token>`

## GenerateTokenExample
---
Generates a token for a user. This token can be used for authorization. For example, once generated, the token can be used in the above Entitlements examples.

#### Useful for

- Generating a token that can be used to authorize a user on the server side


#### Sample Arguments
`--host <host:port> --auth <auth>`

## InteractivePublisherExample
---
Demonstrates a publisher that only publishes data when there are active subscriptions. By default, publishes market data. Pass the `--page` option to publish page data.


#### Sample Arguments
`-H <host:port> -s <service> --auth <auth> --register-ssc 0,5,1`

Publish page data with the `--page` flag

## MultipleRequestsOverrideExample
---
Demonstrates how to send requests with different overrides and correlate them to responses using `CorrelationId`.

#### Useful for

- Keeping track of multiple requests sent at the same time.

#### Sample Arguments
Note: Can be run with no arguments

`-H <host:port> --auth <auth>`

## RequestResponseExample
---
Demonstrates how to make a request and process a response. By default, the service used is `//blp/refdata`, but can be set to any variation of `//blp/refdata`, such as `//blp/staticmktdata`.


#### Sample Arguments
Note: Can be run without arguments

`-r <requestType>`

There are 4 request types: `ReferenceDataRequest`, `ReferenceDataRequestOverride`, `ReferenceDataRequestTableOverride`, and `HistoricalDataRequest`.

## RequestServiceConsumerExample
---
Demonstrates the client side of a request/response setup. Works in conjunction with `RequestServiceProviderExample`.


#### Sample Arguments
`-H <host:port> --auth <auth>`


## RequestServiceProviderExample
---
Demonstrates the server side of a request/response setup. A ProviderSession registers as a service and responds to client requests. This is in contrast with a pub-sub model. Works in conjunction with `RequestServiceConsumerExample`.


#### Sample Arguments
`-H <host:port> --auth <auth>`

## SecurityLookupExample
---
Demonstrates how to use the Bloomberg Instruments service to look up details about securities.


#### Sample Arguments
There are 3 request types: `instrumentListRequest`, `curveListRequest`, `govtListRequest`. For each request type, the user can specify filters i.e., search conditions.

Instrument List (Default):

`-S AAPL -F yellowKeyFilter=YK_FILTER_EQTY`

Curve List:

`-r curveListRequest -S GOOG -F countryCode=US`

Govt List:

`-r govtListRequest -S GOOG -F countryCode=US`


## SnapshotRequestTemplateExample
---
Demonstrates how to make snapshot requests. Snapshots are made by first creating a snapshot template, then sending requests using the template.
This example also batch processes the snapshot templates (batch size is set to 50) because requests are throttled in the infrastructure.

#### Useful for

- Getting a "snapshot" of subscription data without having to process real-time ticks

#### Sample Arguments
`-H <host:port> -s //blp/mktdata --auth <auth> -t "/ticker/SPY US Equity" -f ASK -f BID -f LAST_PRICE -t "/ticker/MSFT US Equity`

## SubscriptionExample
---
Demonstrates how to make subscriptions. Handles data asynchronously, using a session with an event handler. Also demonstrates various subscription-related messages, e.g., `SlowConsumerWarning`, `SlowConsumerWarningCleared`, and `DataLoss`.

Can be used to subscribe to data published by other examples, like `InteractivePublisherExample`.

#### Useful for
- Using BLPAPI asynchronously, processing events with an event handler (see `SubscriptionWithEventPollingExample` for synchronous usage)


#### Sample Arguments
Note: Can be run without arguments

`-H <host:port> -a <auth> -t "/ticker/IBM US Equity`

##  SubscriptionWithEventPollingExample
---
Demonstrates how to make subscriptions. Handles data synchronously.

Can be used to subscribe to data published by other examples, like `InteractivePublisherExample`.

#### Useful for
- Using the BLPAPI synchronously, processing events with `session.nextEvent()` (see `SubscriptionExample` for the recommended asynchronous usage)


#### Sample Arguments
Note: Can be run without arguments

`-H <host:port> -s //blp/mktdata -f LAST_PRICE -f BID -t "/ticker/SPY US Equity" -t "/ticker/IBM US Equity" --auth <auth> --max-events 2`

## UserModeExample
---
An asynchronous identity pass-through example where an app requests data on behalf of users.

#### Useful for

- Creating a client-server setup
- Relying on Bloomberg's backend to check entitlements, rather than using an application to check entitlements

#### Sample Arguments
`-H <host:port> --auth <auth> -u <user> -T<token> -u <user> -u <user> -S "IBM US Equity"`

## Examples Subdirectories
The above examples have some shared code refactored into the subdirectories `Snippets` and `Util`. These subdirectories contain code with the following functionality:

#### Snippets
- Creating and sending requests
- Processing responses

#### Util
- Creating `SessionOptions`
- Creating `SubscriptionList`s
- Creating subscription strings for snapshot request templates
- Handling command-line arguments
