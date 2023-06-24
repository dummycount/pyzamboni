# Zamboni

Python library for working with PSO2 ICE files, based on [https://github.com/Shadowth117/ZamboniLib](ZamboniLib).

## Installation

This project uses C++ extensions, so a [C++ compiler](https://wiki.python.org/moin/WindowsCompilers) is required.

```sh
git submodule update --init --recursive
pip install .
```

To install in editable mode, so changes you make to the library apply immediately, use this command to install instead:

```sh
pip install . -e
```

## Usage (CLI)

```sh
zamboni --help
```

List files in archive:

```sh
zamboni list <file>
```

Unpack ICE archive:

```sh
# Extract to directory <file>.extracted
zamboni unpack <file>
# Group in "group1" and "group2" directories
zamboni unpack <file> -g
# Extract to specified directory
zamboni unpack <file> -o <directory>
```

Repack ICE archive:

```sh
# Pack directory to file
zamboni pack <directory> -o <file>
# Change compression level
zamboni pack <directory> -o <file> -c 6
```

(Files are assumed to belong to group 2 unless contained in a directory named "group1".)
