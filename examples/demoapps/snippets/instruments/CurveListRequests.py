from blpapi import Name

NAME_DESCRIPTION = Name("description")
NAME_QUERY = Name("query")
NAME_RESULTS = Name("results")
NAME_MAX_RESULTS = Name("maxResults")
NAME_CURVE = Name("curve")
ERROR_RESPONSE = Name("ErrorResponse")

CURVE_RESPONSE_ELEMENTS = [
    Name("country"),
    Name("currency"),
    Name("curveid"),
    Name("type"),
    Name("subtype"),
    Name("publisher"),
    Name("bbgid")]


def createRequest(instrumentsService, query, maxResults, filters):
    request = instrumentsService.createRequest("curveListRequest")
    request[NAME_QUERY] = query
    request[NAME_MAX_RESULTS] = maxResults

    for f in filters:
        request[f.name] = f.value

    return request


def processResponse(event):
    for msg in event:
        if msg.messageType() == ERROR_RESPONSE:
            print(f"Received error: {msg}")
            continue

        results = msg[NAME_RESULTS]
        print(f"Processing {len(results)} results:")

        for i, result in enumerate(results):
            elements_values = [f"{n}={result[n]}"
                               for n in CURVE_RESPONSE_ELEMENTS]

            curve = result[NAME_CURVE]
            description = result[NAME_DESCRIPTION]
            print(
                f"    {i + 1}  {curve}  - {description}, {' '.join(elements_values)}")


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
