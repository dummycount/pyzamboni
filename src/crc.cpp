// Based on https://gist.github.com/timepp/1f678e200d9e0f2a043a9ec6b3690635

#include "util.hpp"

#define PY_SSIZE_T_CLEAN

#include <Python.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace {

constexpr std::array<std::uint32_t, 256> GenerateTable() {
  constexpr std::uint32_t Polynomial = 0xEDB88320;

  std::array<std::uint32_t, 256> table{};
  for (auto i = 0; i < table.size(); i++) {
    std::uint32_t c = i;
    for (auto j = 0; j < 8; j++) {
      if (c & 1) {
        c = Polynomial ^ (c >> 1);
      } else {
        c >>= 1;
      }
    }
    table[i] = c;
  }
  return table;
}

constexpr auto Table = GenerateTable();

std::uint32_t Update(std::span<const std::byte> data, std::uint32_t initial = 0) {
  auto c = initial ^ 0xFFFFFFFF;

  for (const auto byte : data) {
    c = Table[(c ^ static_cast<std::uint8_t>(byte)) & 0xFF] ^ (c >> 8);
  }

  return c ^ 0xFFFFFFFF;
}

PyObject* Crc32(PyObject* self, PyObject* args) {
  std::uint32_t checksum = 0;

  auto iter = PythonRef(PyObject_GetIter(args));
  if (!iter) {
    return nullptr;
  }

  while (auto item = PythonRef(PyIter_Next(*iter))) {
    Py_buffer buffer;

    if (PyObject_GetBuffer(*item, &buffer, PyBUF_CONTIG_RO) != 0) {
      PyErr_SetString(PyExc_ValueError, "Expected a buffer");
      return nullptr;
    }

    checksum = Update(AsSpan(buffer), checksum);
    PyBuffer_Release(&buffer);
  }

  return Py_BuildValue("I", checksum);
}

PyObject* Crc32Update(PyObject* self, PyObject* args) {
  const std::byte* data;
  Py_ssize_t dataSize;
  std::uint32_t initial;

  if (!PyArg_ParseTuple(args, "y#I", &data, &dataSize, &initial)) {
    return nullptr;
  }

  auto checksum = Update({data, static_cast<std::size_t>(dataSize)}, initial);

  return Py_BuildValue("I", checksum);
}

PyMethodDef Methods[] = {
    {"crc32", Crc32, METH_VARARGS, nullptr}, {},  // Sentinel
};

PyModuleDef Module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "crc",
    .m_size = -1,
    .m_methods = Methods,
};

}  // namespace

PyMODINIT_FUNC PyInit_crc() { return PyModule_Create(&Module); }