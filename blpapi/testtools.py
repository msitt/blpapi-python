# This tool tries to register every blpapi_*** function call in a database.
# Resulting information can be used later to generate test coverage report.
# This module doesn't ment to be used directly.

import sqlite3
import blpapi.internals as internals
from collections import defaultdict
from threading import Lock
import inspect

#import blpapi-py modules
import blpapi

__MODULES = [
        blpapi,
        blpapi.abstractsession,
        blpapi.constant,
        blpapi.datatype,
        blpapi.datetime,
        blpapi.element,
        blpapi.event,
        blpapi.eventdispatcher,
        blpapi.eventformatter,
        #blpapi.exception,
        blpapi.identity,
        blpapi.message,
        blpapi.name,
        blpapi.providersession,
        blpapi.request,
        blpapi.resolutionlist,
        blpapi.schema,
        blpapi.service,
        blpapi.session,
        blpapi.sessionoptions,
        blpapi.subscriptionlist,
        blpapi.topic,
        blpapi.topiclist,
        blpapi.utils,
]


__DBNAME = 'coverage.db'
__connection = None
__cursor = None
__cursorLock = Lock()

__EXCEPTIONS = set([
    "blpapi_Datetime_tag",
])

def __writeCallToDB(method_name, test_name, class_name=None):
    global __cursor, __cursorLock
    with __cursorLock:
        query = """
            INSERT OR IGNORE INTO {table_name} (test_name, method_name)
            VALUES ('{test_name}', '{method_name}');
            """
        table_name = None
        if class_name is None:
            full_method_name = method_name
            table_name = 'api_calls_by_test'
        else:
            full_method_name = "{0}.{1}".format(class_name, method_name)
            table_name = 'method_calls_by_test'

        if __cursor is not None:
            __cursor.execute(query.format(test_name=test_name,
                                          method_name=full_method_name,
                                          table_name=table_name,))
        else:
            print("No database connection, calling {method} from {test}".format(
                                          method=full_method_name, test=test_name))

def logCallsToDB(method_name, test_name, obj, clsname=None):
    """Basic logging decorator"""
    def newcall(*args, **kwargs):
        __writeCallToDB(method_name, test_name, clsname)
        return obj(*args, **kwargs)
    return newcall

def getAllAPIFunctionNames():
    """Get list of all blpapi function names"""
    global __EXCEPTIONS
    results = []
    for name, obj in internals.__dict__.items():
        # Hack function that starts with 'blpapi_' signature
        # this is an API methods.
        signature = 'blpapi_'
        if name.startswith(signature) and name not in __EXCEPTIONS:
            if hasattr(obj, '__call__'):
                # API function was found
                results.append(name)
    return results

def alterClass(cls, clsName, testName, wrapper):
    """Wrap each class method with decorator"""
    for mname, value in cls.__dict__.items():
        if hasattr(value, '__call__'):
            setattr(cls, mname, wrapper(mname, testName, value, clsName))

def hackInternalsModule(testname, wrap=logCallsToDB):
    """Wraps all API calls with a decorator provided by user"""
    for name in getAllAPIFunctionNames():
        obj = internals.__dict__[name]
        # modify API function
        internals.__dict__[name] = wrap(name, testname, obj)
    # Wrap all blpapi class methods
    global __MODULES
    hackModules(__MODULES, testname, wrap)

def getAllClasses(modules):
    """List all classes in a modules list"""
    result = {}
    for module in modules:
        for name, value in inspect.getmembers(module):
            if inspect.isclass(value):
                result[name] = value
    return result

def getAllClassMethods(modulesList):
    """List all class methods in listed modules"""
    result = []
    for module in modulesList:
        for cname, cls in inspect.getmembers(module):
            if inspect.isclass(cls):
                for mname, mvalue in cls.__dict__.items():
                    if hasattr(mvalue, '__call__'):
                        result.append('{0}.{1}'.format(cname, mname))
    return result

def hackModules(modulesList, testname, wrap=logCallsToDB):
    clsList = getAllClasses(modulesList)
    for clsName, cls in clsList.items():
        alterClass(cls, clsName, testname, wrap)

def init():
    """Initialize module state (sqlite database)"""
    global __cursor, __connection, __DBNAME, __MODULES
    conn = sqlite3.connect(__DBNAME, check_same_thread=False)
    cursor = conn.cursor()
    __connection = conn
    __cursor = cursor
    # There should be two tables, one with all API functions
    # supported, other with all called functions by test.
    query = """
    CREATE TABLE IF NOT EXISTS all_api_exists (
        method_name TEXT,
        UNIQUE(method_name)
    )
    """
    cursor.execute(query)

    query = """
    CREATE TABLE IF NOT EXISTS api_calls_by_test (
        test_name TEXT,
        method_name TEXT,
        UNIQUE(test_name, method_name)
    )
    """
    cursor.execute(query)

    query = """
    CREATE TABLE IF NOT EXISTS all_class_methods (
        method_name TEXT,
        UNIQUE(method_name)
    )
    """
    cursor.execute(query)

    query = """
    CREATE TABLE IF NOT EXISTS method_calls_by_test (
        test_name TEXT,
        method_name TEXT,
        UNIQUE(test_name, method_name)
    )
    """
    cursor.execute(query)

    # Initialize API table
    for name in getAllAPIFunctionNames():
        query = """
            INSERT OR IGNORE INTO all_api_exists (method_name)
            VALUES ('{method_name}');
            """
        if cursor is not None:
            cursor.execute(query.format(method_name=name))

    for name in getAllClassMethods(__MODULES):
        query = """
            INSERT OR IGNORE INTO all_class_methods (method_name)
            VALUES ('{method_name}');
            """
        if cursor is not None:
            cursor.execute(query.format(method_name=name))
    conn.commit()

def commit():
    global __connection, __cursor
    __connection.commit()

class Coverage:
    def __init__(self, cur, api_table_name='all_api_exists', calls_table_name='api_calls_by_test'):
        self.__api_table_name = api_table_name
        self.__calls_table_name = calls_table_name
        self.__tests = defaultdict(list)
        self.__allfn = []
        self.__cursor = cur
        self.readDB()

    def readDB(self):
        query = """SELECT * from {0};""".format(self.__api_table_name)
        for name, in self.__cursor.execute(query):
            self.__allfn.append(name)

        query = """SELECT test_name, method_name FROM {0};""".format(self.__calls_table_name)
        for test, method in self.__cursor.execute(query):
            self.__tests[test].append(method)

    def getTotalCoverage(self):
        from itertools import chain
        allexists = set(self.__allfn)
        alltested = set(chain(*self.__tests.values()))
        uncovered = allexists - alltested
        return {
            "numtested": len(alltested),
            "numexists": len(allexists),
            "needcheck": len(uncovered),
            "uncovered": uncovered,
        }

def getCodeCoverage():
    global __cursor
    blpapi_coverage = Coverage(__cursor)
    blpapipy_coverage = Coverage(__cursor, api_table_name="all_class_methods",
                                 calls_table_name='method_calls_by_test')
    return {
        "blpapi": blpapi_coverage.getTotalCoverage(),
        "blpapipy": blpapipy_coverage.getTotalCoverage(),
    }

# Init everything on module load
print("Initializing testtools, database name %s" % __DBNAME)
init()

