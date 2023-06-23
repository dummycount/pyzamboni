"""
General utilities
"""

import ctypes
from pathlib import Path
import struct
from typing import BinaryIO, TypeVar

_T = TypeVar("_T")


def read_struct(fmt: str, stream: BinaryIO):
    """Read data from a stream and struct.unpack() it"""
    return struct.unpack(fmt, stream.read(struct.calcsize(fmt)))


def is_nifl(data: bytes):
    """Get whether the given data starts with a NIFL header"""
    return data.startswith(b"NIFL")


def is_headerless_file(data: bytes):
    """Get whether the given data does not have a data file header"""

    # ICE files do not seem to allow uppercase characters, so assume that
    # anything starting with a non-lowercase ASCII character is missing a header.
    char = data[0]
    return (char < 32 or char > 64) and (char < 91 or char > 126)


def int32_to_uint32(value: int):
    """Cast a signed integer to an unsigned integer"""
    return ctypes.c_uint32(value).value


def pad_to_multiple(value: int, multiple: int):
    """If "value" is not a multiple of "multiple", increase it to the next multiple."""
    remainder = value % multiple
    return value if remainder == 0 else value + multiple - remainder


def set_flag(bitmask: _T, flag: _T, value: bool):
    """Set a bit in a bitmask to the given value"""
    return (bitmask & ~flag) | (flag if value else 0)


def write_file(path: Path, data: bytes):
    """Write data to a file"""
    with open(path, mode="wb") as f:
        f.write(data)


def naturalsize(num: int, suffix="B"):
    """Get a size in bytes in a human-readable format"""
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"
