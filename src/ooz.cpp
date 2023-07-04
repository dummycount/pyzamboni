#define PY_SSIZE_T_CLEAN

#include <Python.h>
#include <ooz.h>
#include <stdint.h>

#include <vector>

namespace {

PyObject* KrakenCompress(PyObject* self, PyObject* args, PyObject* kwargs) {
  static char DataArg[] = "data";
  static char LevelArg[] = "level";
  static char* kwlist[] = {DataArg, LevelArg, nullptr};

  Py_buffer data;
  int level = 4;

  if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*|i", kwlist, &data, &level)) {
    return nullptr;
  }

  std::vector<uint8_t> output(data.len + 0x10000);
  const auto size =
      Kraken_Compress(static_cast<uint8_t*>(data.buf), static_cast<size_t>(data.len), output.data(), level);

  if (size < 0) {
    PyErr_SetString(PyExc_ValueError, "Failed to decompress");
    return nullptr;
  }

  return Py_BuildValue("y#", output.data(), size);
}

PyObject* KrakenDecompress(PyObject* self, PyObject* args) {
  const uint8_t* data;
  Py_ssize_t dataSize;
  Py_ssize_t outSize;

  if (!PyArg_ParseTuple(args, "y#n", &data, &dataSize, &outSize)) {
    return nullptr;
  }

  std::vector<uint8_t> output(outSize + SAFE_SPACE);
  const auto size = Kraken_Decompress(data, static_cast<size_t>(dataSize), output.data(), static_cast<size_t>(outSize));

  if (size < 0) {
    PyErr_SetString(PyExc_ValueError, "Failed to decompress");
    return nullptr;
  }

  return Py_BuildValue("y#", output.data(), size);
}

PyMethodDef Methods[] = {
    {"kraken_compress", (PyCFunction)KrakenCompress, METH_VARARGS | METH_KEYWORDS, nullptr},
    {"kraken_decompress", KrakenDecompress, METH_VARARGS, nullptr},
    {},  // Sentinel
};

PyModuleDef Module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "ooz",
    .m_size = -1,
    .m_methods = Methods,
};

}  // namespace

PyMODINIT_FUNC PyInit_ooz() { return PyModule_Create(&Module); }