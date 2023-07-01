#include <algorithm>
#include <cstddef>
#include <cxxopts.hpp>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <string>

#include "../ooz/ooz.h"
#include "prs.hpp"

namespace {
using CompressFunc = std::function<std::vector<std::byte>(std::span<const std::byte>)>;
using DecompressFunc = std::function<std::vector<std::byte>(std::span<const std::byte>, ptrdiff_t)>;

void RoundTripTest(const std::filesystem::path& path, const CompressFunc& compress, const DecompressFunc& decompress) {
  auto stream = std::basic_ifstream<std::byte>{path, std::ios::binary};
  auto data =
      std::vector<std::byte>{std::istreambuf_iterator<std::byte>{stream}, std::istreambuf_iterator<std::byte>{}};

  auto compressed = compress(data);
  auto decompressed = decompress(compressed, data.size());

  std::cout << "Original size:   " << data.size() << "\n"
            << "Compressed size: " << compressed.size() << "\n";

  if (std::equal(data.begin(), data.end(), decompressed.begin(), decompressed.end())) {
    std::cout << "Decompressed OK\n";
  } else {
    std::cout << "Decompressed mismatch\n";
  }
}

auto KrakenCompress(std::span<const std::byte> buffer, int level) {
  std::vector<std::byte> input{buffer.begin(), buffer.end()};
  std::vector<std::byte> output(buffer.size() + 0x10000);

  const auto size = Kraken_Compress(reinterpret_cast<uint8_t*>(input.data()), static_cast<size_t>(input.size()),
                                    reinterpret_cast<uint8_t*>(output.data()), level);

  output.resize(size);
  return output;
}

auto KrakenDecompress(std::span<const std::byte> buffer, ptrdiff_t outSize) {
  std::vector<std::byte> output(outSize + SAFE_SPACE);
  const auto size =
      Kraken_Decompress(reinterpret_cast<const uint8_t*>(buffer.data()), static_cast<size_t>(buffer.size()),
                        reinterpret_cast<uint8_t*>(output.data()), static_cast<size_t>(outSize));

  output.resize(size);
  return output;
}

}  // namespace

int main(int argc, char* argv[]) {
  cxxopts::Options options{"test", "Compression test"};

  auto add = options.add_options();
  add("file", "file to compress", cxxopts::value<std::string>());
  add("p,prs", "test PRS format");
  add("k,kraken", "test Kraken format");
  add("l,level", "compression level", cxxopts::value<int>());
  add("h,help", "print usage");

  options.positional_help("FILE");
  options.parse_positional({"file"});

  try {
    auto result = options.parse(argc, argv);

    if (result.count("help")) {
      std::cout << options.help() << "\n";
      return 0;
    }

    auto file = result["file"].as<std::string>();
    auto level = result.count("level") ? result["level"].as<int>() : 3;

    if (!std::filesystem::is_regular_file(file)) {
      std::cout << file << " is not a file\n";
      return -1;
    }

    if (result.count("prs")) {
      std::cout << "Testing PRS\n";
      RoundTripTest(file, Zamboni::Prs::Compress, Zamboni::Prs::Decompress);
    }

    if (result.count("kraken")) {
      std::cout << "Testing Kraken\n";
      RoundTripTest(
          file, [level](auto buffer) { return KrakenCompress(buffer, level); }, KrakenDecompress);
    }

  } catch (const cxxopts::exceptions::exception& ex) {
    std::cout << ex.what() << "\n";
    return -1;
  }

  return 0;
}