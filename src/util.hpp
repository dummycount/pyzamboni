#pragma once

#define PY_SSIZE_T_CLEAN

#include <Python.h>

#include <cstddef>
#include <span>

class PythonRef {
 public:
  explicit PythonRef(PyObject* obj) : mObj{obj} {}

  PythonRef(const PythonRef&) = delete;
  PythonRef& operator=(const PythonRef&) = delete;
  PythonRef(PythonRef&&) = delete;
  PythonRef& operator=(PythonRef&&) = delete;

  ~PythonRef() {
    if (mObj) {
      Py_DECREF(mObj);
    }
  }

  operator bool() { return mObj; }
  PyObject* operator*() { return mObj; }
  PyObject& operator&() { return *mObj; }

 private:
  PyObject* mObj;
};

template <class T = std::byte>
std::span<T> AsSpan(Py_buffer& buffer) {
  return std::span{reinterpret_cast<T*>(buffer.buf), static_cast<std::size_t>(buffer.len / sizeof(T))};
}