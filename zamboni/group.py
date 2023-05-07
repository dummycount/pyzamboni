from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, ClassVar, Optional, Tuple
import os

import numpy as np
import ooz
from . import prs
from .datafile import DataFile
from .encrpytion import blowfish_decrypt, floatage_decrypt
from .util import is_headerless_file, is_nifl, read_struct


@dataclass
class GroupHeader:
    FORMAT: ClassVar[str] = "<IIII"

    original_size: int = 0
    compressed_size: int = 0
    file_count: int = 0
    crc32: int = 0

    @staticmethod
    def read(stream: BinaryIO) -> "GroupHeader":
        return GroupHeader(*read_struct(GroupHeader.FORMAT, stream))

    @property
    def stored_size(self):
        return self.compressed_size if self.compressed_size else self.original_size


def extract_group(
    header: GroupHeader,
    stream: BinaryIO,
    kraken_compressed=False,
    encrypted=False,
    keys: Optional[Tuple[bytes, bytes]] = None,
    second_pass_threshold=0,
    v3_decrypt=False,
) -> bytes:
    if header.stored_size == 0:
        return bytes()

    data = stream.read(header.stored_size)
    if encrypted:
        assert keys is not None
        data = decrypt_group(
            data,
            keys=keys,
            second_pass_threshold=second_pass_threshold,
            v3_decrypt=v3_decrypt,
        )

    if header.compressed_size:
        data = decompress_group(data, header.original_size, kraken_compressed)

    return data


def decrypt_group(
    data: bytes, keys: Tuple[bytes, bytes], second_pass_threshold=0, v3_decrypt=False
) -> bytes:
    key1, key2 = keys

    if not v3_decrypt:
        data = floatage_decrypt(data, key1)

    # The last 12 bytes of the file don't match the C# Zamboni implementation.
    # Is that a bug here or a bug there?
    data = blowfish_decrypt(data, key1)

    if not v3_decrypt and len(data) < second_pass_threshold:
        data = blowfish_decrypt(data, key2)

    return data


def decompress_group(data: bytes, out_size: int, kraken_compressed: bool) -> bytes:
    if kraken_compressed:
        return ooz.decompress(data, out_size)

    data = np.frombuffer(data, dtype=np.uint8) ^ 0x95
    return prs.decompress(data, out_size)


def split_group(header: GroupHeader, data: bytes) -> list[bytes]:
    if not data:
        return []

    if is_nifl(data):
        return _split_headerless_nifl(header, data)

    if is_headerless_file(data):
        return _split_headerless_file(header, data)

    return _split_normal_group(header, data)


def _split_headerless_nifl(header: GroupHeader, data: bytes):
    files: list[DataFile] = []
    stream = BytesIO(data)

    for i in range(header.file_count):
        start = stream.tell()

        if stream.read(4) != b"NIFL":
            # Nameless file for remaining file data
            stream.seek(start, os.SEEK_SET)
            files.append(DataFile(raw_data=stream.read(), file_index=i))
            break

        size = read_struct("16xi", stream)[0]

        stream.seek(size - 0x10, os.SEEK_CUR)
        nof0_size = read_struct("i", stream)[0] + 8

        # Add padding bytes
        nof0_size += 0x10 - (nof0_size % 0x10)

        # Add NOF0 size and NEND bytes
        size += nof0_size + 0x10

        stream.seek(start, os.SEEK_SET)
        files.append(DataFile(raw_data=stream.read(size), file_index=i))

    return files


def _split_headerless_file(header: GroupHeader, data: bytes):
    if header.file_count != 1:
        raise ValueError(
            f"Expected a single nameless file but header lists {header.file_count} files."
        )
    return [data]


def _split_normal_group(header: GroupHeader, data: bytes):
    files: list[bytes] = []
    stream = BytesIO(data)

    for i in range(header.file_count):
        start = stream.tell()
        size = read_struct("4xi", stream)[0]

        stream.seek(start, os.SEEK_SET)
        files.append(DataFile(raw_data=stream.read(size), file_index=i))

    return files
