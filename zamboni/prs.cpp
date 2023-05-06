#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <cstddef>
#include <span>
#include <stdexcept>
#include <vector>

namespace {

PyObject* PrsCompress(PyObject* self, PyObject* args) { return nullptr; }

class DecompressState {
 public:
  explicit DecompressState(std::span<const std::byte> input) : mCur{std::begin(input)}, mEnd{std::end(input)} {}

  std::byte ReadByte() {
    if (mCur == mEnd) {
      throw std::out_of_range{"Read past end of input"};
    }

    return *mCur++;
  }

  std::uint16_t ReadU8() { return std::to_integer<std::uint8_t>(ReadByte()); }

  std::uint16_t ReadU16() {
    const auto byte0 = std::to_integer<std::uint16_t>(ReadByte());
    const auto byte1 = std::to_integer<std::uint16_t>(ReadByte());

    return (byte1 << 8) + byte0;
  }

  bool GetControlBit() {
    static constexpr auto LSB = std::byte{0x1};

    mControlByteCounter--;
    if (mControlByteCounter == 0) {
      mControlByte = ReadByte();
      mControlByteCounter = 8;
    }

    const auto result = static_cast<bool>(mControlByte & LSB);
    mControlByte >>= 1;
    return result;
  }

 private:
  std::span<const std::byte>::iterator mCur;
  std::span<const std::byte>::iterator mEnd;
  std::byte mControlByte{};
  int mControlByteCounter = 1;
};

std::vector<std::byte> Decompress(std::span<const std::byte> input, std::ptrdiff_t outSize) {
  DecompressState state{input};
  std::vector<std::byte> output(outSize);

  std::ptrdiff_t outIndex = 0;
  while (outIndex < outSize) {
    while (state.GetControlBit()) {
      output.at(outIndex++) = state.ReadByte();
    }

    int offset = 0;
    int loadSize = 0;

    if (state.GetControlBit()) {
      const auto loadInfo = state.ReadU16();
      if (!loadInfo) {
        break;
      }

      const auto size = loadInfo & 0x7;

      offset = static_cast<int>(loadInfo >> 3) - 0x2000;
      loadSize = size ? size + 2 : state.ReadU8() + 10;
    } else {
      loadSize = 2;
      if (state.GetControlBit()) {
        loadSize += 2;
      }
      if (state.GetControlBit()) {
        loadSize += 1;
      }

      offset = static_cast<int>(state.ReadU8()) - 0x100;
    }

    auto loadIndex = outIndex + offset;

    for (int i = 0; i < loadSize; i++) {
      output.at(outIndex++) = output.at(loadIndex++);
    }
  }

  return output;
}

PyObject* PrsDecompress(PyObject* self, PyObject* args) {
  const std::byte* data;
  Py_ssize_t dataSize;
  Py_ssize_t outSize;

  if (!PyArg_ParseTuple(args, "y#n", &data, &dataSize, &outSize)) {
    return nullptr;
  }

  try {
    const auto result = Decompress({data, static_cast<std::size_t>(dataSize)}, outSize);

    return Py_BuildValue("y#", result.data(), result.size());
  } catch (const std::out_of_range& ex) {
    PyErr_SetString(PyExc_IndexError, ex.what());
  }

  return nullptr;
}

PyMethodDef PrsMethods[] = {
    {"compress", PrsCompress, METH_VARARGS, nullptr},
    {"decompress", PrsDecompress, METH_VARARGS, nullptr},
    {},  // Sentinel
};

PyModuleDef FloatageModule = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "prs",
    .m_size = -1,
    .m_methods = PrsMethods,
};

}  // namespace

PyMODINIT_FUNC PyInit_prs() { return PyModule_Create(&FloatageModule); }