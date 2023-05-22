#define PY_SSIZE_T_CLEAN

#include "prs.hpp"

#include <Python.h>

#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace {

PyObject* PrsCompress(PyObject* self, PyObject* args) {
  const std::byte* data;
  Py_ssize_t dataSize;

  if (!PyArg_ParseTuple(args, "y#", &data, &dataSize)) {
    return nullptr;
  }

  try {
    const auto result = Zamboni::Prs::Compress({data, static_cast<std::size_t>(dataSize)});

    return Py_BuildValue("y#", result.data(), result.size());
  } catch (const std::out_of_range& ex) {
    PyErr_SetString(PyExc_ValueError, ex.what());
    return nullptr;
  }
}

PyObject* PrsDecompress(PyObject* self, PyObject* args) {
  const std::byte* data;
  Py_ssize_t dataSize;
  Py_ssize_t outSize;

  if (!PyArg_ParseTuple(args, "y#n", &data, &dataSize, &outSize)) {
    return nullptr;
  }

  try {
    const auto result = Zamboni::Prs::Decompress({data, static_cast<std::size_t>(dataSize)}, outSize);

    return Py_BuildValue("y#", result.data(), result.size());
  } catch (const std::out_of_range& ex) {
    PyErr_SetString(PyExc_ValueError, ex.what());
    return nullptr;
  }
}

PyMethodDef Methods[] = {
    {"compress", PrsCompress, METH_VARARGS, nullptr},
    {"decompress", PrsDecompress, METH_VARARGS, nullptr},
    {},  // Sentinel
};

PyModuleDef Module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "prs",
    .m_size = -1,
    .m_methods = Methods,
};

}  // namespace

PyMODINIT_FUNC PyInit_prs() { return PyModule_Create(&Module); }