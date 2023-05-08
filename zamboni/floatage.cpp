#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <algorithm>
#include <cstddef>
#include <ranges>
#include <span>
#include <vector>

namespace {

std::vector<std::byte> Decrypt(std::span<const std::byte> input, std::uint32_t key) {
  static constexpr auto Zero = std::byte{0};
  static constexpr auto Shift = 16;

  const auto xorByte = std::byte{((key >> Shift) ^ key) & 0xFF};

  std::vector<std::byte> result{};
  result.reserve(input.size());

  std::ranges::transform(input, std::back_inserter(result),
                         [&](const std::byte b) { return b == Zero || b == xorByte ? b : b ^ xorByte; });

  return result;
}

PyObject* FloatageDecrypt(PyObject* self, PyObject* args) {
  const std::byte* data;
  Py_ssize_t dataSize;
  std::uint32_t key;

  if (!PyArg_ParseTuple(args, "y#I", &data, &dataSize, &key)) {
    return nullptr;
  }

  const auto result = Decrypt({data, static_cast<std::size_t>(dataSize)}, key);

  return Py_BuildValue("y#", result.data(), result.size());
}

PyMethodDef Methods[] = {
    {"decrypt", FloatageDecrypt, METH_VARARGS, nullptr}, {},  // Sentinel
};

PyModuleDef Module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "floatage",
    .m_size = -1,
    .m_methods = Methods,
};

}  // namespace

PyMODINIT_FUNC PyInit_floatage() { return PyModule_Create(&Module); }