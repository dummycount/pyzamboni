import ctypes
from pathlib import Path
import struct
from typing import BinaryIO


def read_struct(fmt: str, stream: BinaryIO):
    return struct.unpack(fmt, stream.read(struct.calcsize(fmt)))


def is_nifl(data: bytes):
    return data.startswith(b"NIFL")


def is_headerless_file(data: bytes):
    # ICE files do not seem to allow uppercase characters, so assume that
    # anything starting with a non-lowercase ASCII character is missing a header.
    char = data[0]
    return (char < 32 or char > 64) and (char < 91 or char > 126)


def int32_to_uint32(value: int):
    return ctypes.c_uint32(value).value


def write_file(path: Path, data: bytes):
    with open(path, mode="wb") as f:
        f.write(data)


def naturalsize(num: int, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"
