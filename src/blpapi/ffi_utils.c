#define Py_LIMITED_API 0x03080000
#include <Python.h>

#include "blpapi_element.h"
#include "blpapi_correlationid.h"

#if defined(WIN32) || defined(_WIN32) || defined(__WIN32) && !defined(__CYGWIN__)
#define PEXPRT __declspec(dllexport)
#else
#define PEXPRT
#endif

PEXPRT PyObject* blpapi_Element_toPy(blpapi_Element_t *element);

// this is only needed for windows as the linker will add an /EXPORT
void PyInit_ffiutils(void) {
}

PyObject* getScalarValue(const blpapi_Element_t* element, const int index) {
    const int datatype = blpapi_Element_datatype(element);

    switch (datatype) {
        case BLPAPI_DATATYPE_BOOL: {
            blpapi_Bool_t boolBuffer;
            if (0 != blpapi_Element_getValueAsBool(element,
                                                   &boolBuffer,
                                                   index)) {
                PyErr_SetString(
                        PyExc_Exception,
                        "Internal error getting bool");
                return NULL;
            }
            return PyBool_FromLong(boolBuffer);
        }
        case BLPAPI_DATATYPE_BYTE:
        case BLPAPI_DATATYPE_INT32:
        case BLPAPI_DATATYPE_INT64: {
            blpapi_Int64_t int64Buffer;
            if (0 != blpapi_Element_getValueAsInt64(element,
                                                    &int64Buffer,
                                                    index)) {
                PyErr_SetString(
                        PyExc_Exception,
                        "Internal error getting int");
                return NULL;
            }
            return PyLong_FromLongLong(int64Buffer);
        }
        case BLPAPI_DATATYPE_FLOAT32:
        case BLPAPI_DATATYPE_FLOAT64: {
            blpapi_Float64_t floatBuffer;
            if (0 != blpapi_Element_getValueAsFloat64(element,
                                                      &floatBuffer,
                                                      index)) {
                PyErr_SetString(
                        PyExc_Exception,
                        "Internal error getting float");
                return NULL;
            }
            return PyFloat_FromDouble(floatBuffer);
        }
        case BLPAPI_DATATYPE_CHAR:
        case BLPAPI_DATATYPE_STRING:
        case BLPAPI_DATATYPE_ENUMERATION: {
            const char* strValue;
            if (0 != blpapi_Element_getValueAsString(element,
                                                     &strValue,
                                                     index)) {
                PyErr_SetString(
                        PyExc_Exception,
                        "Internal error getting string");
                return NULL;
            }
            return PyUnicode_FromString(strValue);
        }
        case BLPAPI_DATATYPE_BYTEARRAY: {
            const char* bytesValue = 0;
            size_t bytesLength = 0;
            if (0 != blpapi_Element_getValueAsBytes(element,
                                                    &bytesValue,
                                                    &bytesLength,
                                                    index)) {
                PyErr_SetString(
                        PyExc_Exception,
                        "Internal error getting bytes");
                return NULL;
            }
            return PyBytes_FromStringAndSize(bytesValue, bytesLength);
        }
        case BLPAPI_DATATYPE_DATE:
        case BLPAPI_DATATYPE_TIME:
        case BLPAPI_DATATYPE_DATETIME: {
            static PyObject* blpapiDatetimeModule = NULL;
            static PyObject* datetimeUtil = NULL;
            static PyObject* convertToPyTime = NULL;
            blpapi_HighPrecisionDatetime_t highPrecisionDatetimeBuffer;

            /*
               Py_LIMITED_API blocks the use of macros from datetime.h
               we need to call conversion code from python...
            */
            // initialize static variables once
            if (convertToPyTime == NULL) {
                blpapiDatetimeModule =
                    PyImport_ImportModule("blpapi.datetime");
                if (blpapiDatetimeModule == NULL) {
                    PyErr_SetString(
                            PyExc_Exception,
                            "Internal error getting blpapi.datetime");
                    return NULL;
                }
                datetimeUtil =
                    PyObject_GetAttr(blpapiDatetimeModule,
                                     PyUnicode_FromString("_DatetimeUtil"));
                if (datetimeUtil == NULL) {
                    Py_DECREF(blpapiDatetimeModule);
                    PyErr_SetString(
                            PyExc_Exception,
                            "Internal error getting _DatetimeUtil");
                    return NULL;
                }
                convertToPyTime = PyObject_GetAttr(
                    datetimeUtil, PyUnicode_FromString("toPyTimeFromInts"));
                if (convertToPyTime == NULL) {
                    Py_DECREF(blpapiDatetimeModule);
                    Py_DECREF(datetimeUtil);
                    PyErr_SetString(
                            PyExc_Exception,
                            "Internal error getting 'toPyTimeFromInts'");
                    return NULL;
                }
            }

            if (blpapi_Element_getValueAsHighPrecisionDatetime(
                        element,
                        &highPrecisionDatetimeBuffer,
                        index) != 0) {
                PyErr_SetString(
                        PyExc_Exception,
                        "Internal error getting datetime");
                return NULL;
            }

            // Return `None` when the `datetime` has no parts because our
            if (!highPrecisionDatetimeBuffer.datetime.parts) {
                Py_RETURN_NONE; // inc ref and return
            }

            return PyObject_CallFunction(
                convertToPyTime, "iiiiiiiii",
                    highPrecisionDatetimeBuffer.datetime.parts,
                    highPrecisionDatetimeBuffer.datetime.offset,
                    highPrecisionDatetimeBuffer.datetime.year,
                    highPrecisionDatetimeBuffer.datetime.month,
                    highPrecisionDatetimeBuffer.datetime.day,
                    highPrecisionDatetimeBuffer.datetime.hours,
                    highPrecisionDatetimeBuffer.datetime.minutes,
                    highPrecisionDatetimeBuffer.datetime.seconds,
                    (highPrecisionDatetimeBuffer.datetime.milliSeconds * 1000)
                    + (highPrecisionDatetimeBuffer.picoseconds / 1000000)
                    );
        }
        case BLPAPI_DATATYPE_SEQUENCE:
        case BLPAPI_DATATYPE_CHOICE:
        default: {
            PyErr_SetString(PyExc_Exception, "Internal datatype error");
            return NULL;
        }
    }
}

PyObject* complexElementToPy(blpapi_Element_t *element) {
        PyObject* pyDict = PyDict_New();
        PyObject* subElementPy = NULL;
        unsigned int i;
        if (pyDict == NULL) {
            goto ERROR;
        }

        for (i = 0; i < blpapi_Element_numElements(element); ++i) {
            blpapi_Element_t* subElement;
            const char* name;
            if (0 != blpapi_Element_getElementAt(element, &subElement, i)) {
                PyErr_SetString(PyExc_Exception,
                                "Internal error in `Element.toPy`");
                goto ERROR;
            }
            name = blpapi_Element_nameString(subElement);
            subElementPy = blpapi_Element_toPy(subElement);
            if (subElementPy == NULL) {
                goto ERROR;
            }
            // does not steal ref to value
            if (PyDict_SetItemString(pyDict, name, subElementPy)) {
                goto ERROR;
            }
            Py_DECREF(subElementPy);
        }
        return pyDict;
ERROR:
    Py_XDECREF(pyDict);
    Py_XDECREF(subElementPy);
    // Ensure that we set an error before returning NULL
    if (PyErr_Occurred() == NULL) {
        PyErr_SetString(
                PyExc_Exception,
                "Internal error converting a complex Element");
    }
    return NULL;
}

PyObject* arrayElementToPy(blpapi_Element_t *element) {
    const unsigned int numValues = blpapi_Element_numValues(element);
    PyObject* pyList = PyList_New(numValues);
    PyObject* pyValue = NULL;

    const blpapi_SchemaElementDefinition_t* definition
            = blpapi_Element_definition(element);
    const blpapi_SchemaTypeDefinition_t* typeDefinition
            = blpapi_SchemaElementDefinition_type(definition);

    unsigned int i;
    if (pyList == NULL) {
        goto ERROR;
    }

    // complex values
    if (blpapi_SchemaTypeDefinition_isComplexType(typeDefinition)) {
        for (i = 0; i < numValues; ++i) {
            blpapi_Element_t* result;
            if (0 != blpapi_Element_getValueAsElement(element, &result, i)) {
                PyErr_SetString(
                    PyExc_Exception,
                    "Internal error in blpapi_Element_getValueAsElement");
                goto ERROR;
            }
            pyValue = blpapi_Element_toPy(result);
            if (pyValue == NULL) {
                goto ERROR;
            }
            // see https://docs.python.org/3/c-api/list.html#c.PyList_SetItem
            PyList_SetItem(pyList, i, pyValue);
        }
    }
    else {
        // non complex values
        for (i = 0; i < numValues; ++i) {
            pyValue = getScalarValue(element, i);
            if (pyValue == NULL) {
                goto ERROR;
            }
            PyList_SetItem(pyList, i, pyValue);
        }
    }
    return pyList;

ERROR:
    Py_XDECREF(pyList);
    Py_XDECREF(pyValue);
    // Ensure that we set an error before returning NULL
    if (PyErr_Occurred() == NULL) {
        PyErr_SetString(
                PyExc_Exception,
                "Internal error converting an array Element");
    }
    return NULL;
}

PyObject* blpapi_Element_toPy(blpapi_Element_t *element) {
    if (blpapi_Element_isComplexType(element)) {
        return complexElementToPy(element);
    }
    else if (blpapi_Element_isArray(element)) {
        return arrayElementToPy(element);
    }
    else if (blpapi_Element_isNull(element)) {
        Py_RETURN_NONE; // inc ref and return
    }
    else {
        return getScalarValue(element, 0);
    }
}

/* increfs allow python code to increment ref. count of objects,
   even if they are not yet pointed to by blpapi_ManagedPtr_t struct.
*/
PEXPRT void incref(PyObject *obj);
void incref(PyObject *obj)
{
    PyGILState_STATE s = PyGILState_Ensure();
    Py_XINCREF(obj);
    PyGILState_Release(s);
}

/* This function implements the interface for managing objects from C.
   We are ensuring GIL in this implementation, but those calls
   can be nested and will not cause a deadlock if a call to managerFunc
   is interrupted by GC that needs to decref.
   Note: INCREF/DECREF are not atomic in the C-sense, but will not be
   interrupted by Python interpreted thread.
 */
PEXPRT int managerFunc(void * mptr, void * sptr, int operation)
{
    PyGILState_STATE s = PyGILState_Ensure();

    blpapi_ManagedPtr_t * managedPtr = (blpapi_ManagedPtr_t *) mptr;
    blpapi_ManagedPtr_t * srcPtr = (blpapi_ManagedPtr_t *) sptr;

    if (operation == BLPAPI_MANAGEDPTR_COPY) {
        managedPtr->pointer = srcPtr->pointer;
        managedPtr->manager = srcPtr->manager;
        Py_XINCREF((PyObject *) (managedPtr->pointer));
    }
    else if (operation == BLPAPI_MANAGEDPTR_DESTROY) {
        Py_XDECREF((PyObject *) (managedPtr->pointer));
    }

    PyGILState_Release(s);
    return 0;
}

/* Used to set the function pointer to our manager inside cid structure */
PEXPRT void setmptr(void *s);
void setmptr(void *s) {
    blpapi_ManagedPtr_t *p = (blpapi_ManagedPtr_t *) s;
    p->manager = (blpapi_ManagedPtr_ManagerFunction_t ) &managerFunc;
}

/* Used to check if the manager used by a cid is the one we set.
If it is not the same, it must be a C++ cb set for recaps.
This function will be removed when recap cids are fixed.
*/
PEXPRT int is_known_obj(void *s);
int is_known_obj(void *s) {
    blpapi_ManagedPtr_t *p = (blpapi_ManagedPtr_t *) s;
    return p->manager == (blpapi_ManagedPtr_ManagerFunction_t ) &managerFunc;
}
