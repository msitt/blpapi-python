from snippets.apiflds import ApiFieldsRequestUtils


def createRequest(apifldsService):
    request = apifldsService.createRequest("FieldListRequest")
    request["fieldType"] = "Static"
    request["returnFieldDocumentation"] = False

    return request


def processResponse(event):
    # NOTE: this function uses the method-based interface to read a
    # `Message`. See `FieldInfoRequests.processResponse` for the
    # dictionary-like interface.
    for msg in event:
        ApiFieldsRequestUtils.printHeader()

        fields = msg.getElement("fieldData")
        for i in range(fields.numValues()):
            ApiFieldsRequestUtils.printField(fields.getValueAsElement(i))

        print()


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
