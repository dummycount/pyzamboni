#include "prs.hpp"

#include <algorithm>
#include <cstddef>
#include <cxxopts.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>

namespace {
void RoundTripTest(const std::filesystem::path& path) {
  auto stream = std::basic_ifstream<std::byte>{path, std::ios::binary};
  auto data =
      std::vector<std::byte>{std::istreambuf_iterator<std::byte>{stream}, std::istreambuf_iterator<std::byte>{}};

  auto compressed = Zamboni::Prs::Compress(data);
  auto decompressed = Zamboni::Prs::Decompress(compressed, data.size());

  std::cout << "Original size:   " << data.size() << "\n"
            << "Compressed size: " << compressed.size() << "\n";

  if (std::equal(data.begin(), data.end(), decompressed.begin(), decompressed.end())) {
    std::cout << "Decompressed OK\n";
  } else {
    std::cout << "Decompressed mismatch\n";
  }
}
}  // namespace

int main(int argc, char* argv[]) {
  cxxopts::Options options{"prs", "PRS compression test"};

  auto add = options.add_options();
  add("file", "file to test", cxxopts::value<std::string>());
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

    if (!std::filesystem::is_regular_file(file)) {
      std::cout << file << " is not a file\n";
      return -1;
    }

    RoundTripTest(file);

  } catch (const cxxopts::exceptions::exception& ex) {
    std::cout << ex.what() << "\n";
    return -1;
  }

  return 0;
}