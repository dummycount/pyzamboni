#pragma once

#include <cstddef>
#include <span>
#include <vector>

namespace Zamboni {
namespace Prs {

std::vector<std::byte> Compress(std::span<const std::byte> inputBuffer);
std::vector<std::byte> Decompress(std::span<const std::byte> inputBuffer, std::ptrdiff_t outSize);

}  // namespace Prs
}  // namespace Zamboni
