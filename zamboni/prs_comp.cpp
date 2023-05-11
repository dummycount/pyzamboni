#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <iterator>
#include <span>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include <vector>

#include "prs.hpp"

namespace {

constexpr auto MaxShortRefSize = 5;
constexpr auto MaxLongRefSize = 255 + 10;
constexpr std::ptrdiff_t ShortRefOffsetLimit = 1 << 8;
constexpr std::ptrdiff_t LongRefOffsetLimit = 1 << (16 - 3);

using OffsetList = std::pair<std::vector<std::ptrdiff_t>, std::ptrdiff_t>;
using OffsetDictionary = std::unordered_map<std::byte, OffsetList>;

OffsetDictionary BuildOffsetDictionary(std::span<const std::byte> input) {
  OffsetDictionary dictionary{};

  for (std::ptrdiff_t i = 0; i < std::ssize(input); i++) {
    const auto key = input[i];
    dictionary[key].first.push_back(i);
  }

  return dictionary;
}

OffsetList& GetOffsetList(OffsetDictionary& dictionary, std::byte value, std::ptrdiff_t offset) {
  auto& item = dictionary[value];

  if (item.second < offset - 0x1FF0) {
    auto index = item.second;
    while (index < std::ssize(item.first) && item.first[index] < offset - 0x1FF0) {
      index++;
    }

    item.second = index;
  }

  return item;
}

class CompressState {
 public:
  explicit CompressState(std::vector<std::byte>& output) : mBuffer{output}, mOut{std::back_inserter(output)} {}

  void WriteStart(std::byte in0, std::byte in1) {
    mOut = std::byte{3};
    mOut = in0;
    mOut = in1;
  }

  void WriteEnd() {
    AddControlBit(0);
    AddControlBit(1);
    mOut = std::byte{0};
    mOut = std::byte{0};
  }

  void WriteByte(std::byte value) {
    AddControlBit(1);
    mOut = value;
  }

  void WriteShortReference(int size, std::ptrdiff_t offset) {
    if (size > MaxShortRefSize) {
      throw std::out_of_range{"Short reference size must be <= 5"};
    }
    if (offset >= ShortRefOffsetLimit) {
      throw std::out_of_range{"Short reference offset must be < 256"};
    }

    AddControlBit(0);
    AddControlBit(0);
    AddControlBit((size - 2) >> 1);
    AddControlBit((size - 2) & 0x1);
    mOut = static_cast<std::byte>(offset);
  }

  void WriteLongReference(int size, std::ptrdiff_t offset) {
    if (size >= MaxLongRefSize) {
      throw std::out_of_range{"Long reference size must be <= 6"};
    }
    if (offset >= ShortRefOffsetLimit) {
      throw std::out_of_range{"Long reference offset must be < 8192"};
    }

    AddControlBit(0);
    AddControlBit(1);

    auto value = offset << 3;
    if (size <= 9) {
      value |= size - 2;
    }

    // TODO: is this little or big endian?
    mOut = static_cast<std::byte>(value >> 8);
    mOut = static_cast<std::byte>(value & 0xFF);

    if (size > 9) {
      mOut = static_cast<std::byte>(size - 10);
    }
  }

 private:
  void AddControlBit(std::uint8_t bit) {
    if (mControlBitCounter == 8) {
      mControlBitCounter = 0;
      mControlByteOffset = std::ssize(mBuffer);
      mOut = std::byte{bit};
    } else {
      mBuffer.at(mControlByteOffset) |= static_cast<std::byte>(bit << mControlBitCounter);
      mControlBitCounter++;
    }
  }

  std::vector<std::byte>& mBuffer;
  std::back_insert_iterator<std::vector<std::byte>> mOut;
  int mControlBitCounter = 2;
  std::ptrdiff_t mControlByteOffset = 0;
};

}  // namespace

std::vector<std::byte> Compress(std::span<const std::byte> inputBuffer) {
  if (inputBuffer.size() < 2) {
    throw std::out_of_range{"Input must be at least 2 bytes"};
  }

  std::vector<std::byte> outputBuffer{};
  outputBuffer.reserve(inputBuffer.size());
  CompressState output{outputBuffer};

  auto dictionary = BuildOffsetDictionary(inputBuffer);

  auto input = inputBuffer.begin();
  const auto end = inputBuffer.end();
  const auto length = std::ssize(inputBuffer);

  output.WriteStart(*input++, *input++);

  while (input != end) {
    const auto currentOffset = input - inputBuffer.begin();
    const auto offsetList = GetOffsetList(dictionary, *input, currentOffset);

    auto refSize = 2;
    std::ptrdiff_t refOffset = -1;
    std::ptrdiff_t minOffset = currentOffset - ShortRefOffsetLimit;

    for (auto i = offsetList.second; i < std::ssize(offsetList.first) && offsetList.first[i] < currentOffset; i++) {
      auto testOffset = offsetList.first[i];
      auto testSize = 0;
      const auto maxSize = std::min(length - currentOffset, ShortRefOffsetLimit);

      while (testSize < maxSize && input[testOffset + testSize] == input[currentOffset + testSize]) {
        testSize++;
      }

      if ((testSize > 2 || testOffset > minOffset) &&
          (testSize > refSize || (testSize == refSize && testOffset > refOffset))) {
        refSize = testSize;
        refOffset = testOffset;
      }
    }

    if (refOffset < 0 || (currentOffset - refOffset > ShortRefOffsetLimit && refSize < 3)) {
      output.WriteByte(*input++);
    } else {
      if (refSize <= MaxShortRefSize && currentOffset - refOffset < ShortRefOffsetLimit) {
        output.WriteShortReference(refSize, refOffset - (currentOffset - ShortRefOffsetLimit));
      } else {
        output.WriteLongReference(refSize, refOffset - (currentOffset - LongRefOffsetLimit));
      }

      input += refSize;
    }
  }

  output.WriteEnd();
  return outputBuffer;
}
