#include <cstddef>
#include <span>
#include <stdexcept>
#include <vector>

#include "prs.hpp"

namespace Zamboni {
namespace Prs {

namespace {

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

}  // namespace

std::vector<std::byte> Decompress(std::span<const std::byte> inputBuffer, std::ptrdiff_t outSize) {
  DecompressState input{inputBuffer};
  std::vector<std::byte> output(outSize);

  std::ptrdiff_t outIndex = 0;
  while (outIndex < outSize) {
    while (input.GetControlBit()) {
      output.at(outIndex++) = input.ReadByte();
    }

    int offset = 0;
    int loadSize = 0;

    if (input.GetControlBit()) {
      const auto loadInfo = input.ReadU16();
      if (!loadInfo) {
        break;
      }

      const auto size = loadInfo & 0x7;

      offset = static_cast<int>(loadInfo >> 3) - 0x2000;
      loadSize = size ? size + 2 : input.ReadU8() + 10;
    } else {
      loadSize = 2;
      if (input.GetControlBit()) {
        loadSize += 2;
      }
      if (input.GetControlBit()) {
        loadSize += 1;
      }

      offset = static_cast<int>(input.ReadU8()) - 0x100;
    }

    auto loadIndex = outIndex + offset;

    for (int i = 0; i < loadSize; i++) {
      output.at(outIndex++) = output.at(loadIndex++);
    }
  }

  return output;
}

}  // namespace Prs
}  // namespace Zamboni