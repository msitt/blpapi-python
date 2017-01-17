# utils.py

"""Internal utils."""


class Iterator(object):
    """Universal iterator for many of BLPAPI objects.

    It can be used to iterate any sub-items in an item which has
    the following methods:
        * method returning the number of sub-items
        * method returning the 'index'ed sub-item

    For example, it is currently used as an iterator for Service's event
    definition in the following way:

        class Service(object):
            ...
            # Returns an iterator over this Service's event definitions.
            def eventDefinitions(self):
                return utils.Iterator(
                    self,
                    Service.numEventDefinitions,
                    Service.getEventDefinitionAt)

            ...

    """

    def __init__(self, objToIterate, numFunc, getFunc):
        self.__obj = objToIterate
        self.__index = 0
        self.__num = numFunc(objToIterate)
        self.__getter = getFunc

    def __iter__(self):
        return self

    def next(self):
        if self.__index == self.__num:
            raise StopIteration()
        else:
            res = self.__getter(self.__obj, self.__index)
            self.__index += 1
            return res


class MetaClassForClassesWithEnums(type):
    """This meta class protects enums from changes.

    This meta class does not let change values of class members with names in
    uppercase (a typical naming convention for enums).

    """

    class EnumError(TypeError):
        """Raise this on attempt to change value of an enumeration constant.
        """
        pass

    def __setattr__(mcs, name, value):
        """Change the value of an attribute if it is not an enum.

        Raise EnumError exception otherwise.
        """
        if name.isupper() and name in mcs.__dict__:
            raise mcs.EnumError, "Can't change value of enum %s" % name
        else:
            type.__setattr__(mcs, name, value)

    def __delattr__(mcs, name):
        """Unbind the attribute if it is not an enum.

        Raise EnumError exception otherwise.
        """
        if name.isupper() and name in mcs.__dict__:
            raise mcs.EnumError, "Can't unbind enum %s" % name
        else:
            type.__delattr__(mcs, name)

__copyright__ = """
Copyright 2012. Bloomberg Finance L.P.

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
