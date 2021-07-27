# requesttemplate.py

"""
This component provides a class, RequestTemplate, that can be used to obtain
snapshots from subscription data without having to handle the ticks on an
actual subscription.

Request templates are obtained from a Session and should be always used with
the session that creates the template. When a session is terminated, any
request templates associated with that session become invalid. Results of
sending or canceling of invalid request templates is undefined.

In order to send a request represented by a template,
'blpapi.Session.sendRequestTemplate' method should be called.

Check 'blpapi.Session.createSnapshotRequestTemplate' for details about creation
and management of snapshot request templates.
"""

from . import internals
from .chandle import CHandle

class RequestTemplate(CHandle):
    """Request templates cache the necessary information to make a request and
    eliminate the need to create new requests for snapshot services.
    """

    def __init__(self, handle):
        super(RequestTemplate, self).__init__(
            handle, internals.blpapi_RequestTemplate_release)

__copyright__ = """
Copyright 2018. Bloomberg Finance L.P.

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
