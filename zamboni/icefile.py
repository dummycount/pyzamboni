"""
"""
from dataclasses import dataclass, field
from enum import IntFlag
from io import BytesIO
import os
import struct
from typing import BinaryIO, ClassVar, Optional, Tuple

import blowfish
from .compression import decompress_kraken, decompress_prs
from .encrpytion import floatage_decrypt_block, get_blowfish_keys


def _read_struct(fmt: str, stream: BinaryIO):
    return struct.unpack(fmt, stream.read(struct.calcsize(fmt)))


def _is_nifl(data: bytes):
    return data.startswith(b"NIFL")


def _is_headerless_file(data: bytes):
    # ICE files do not seem to allow uppercase characters, so assume that
    # anything starting with a non-lowercase ASCII character is missing a header.
    c = data[0]
    return (c < 32 or c > 64) and (c < 91 or c > 126)


@dataclass
class GroupHeader:
    FORMAT: ClassVar[str] = "<IIII"

    original_size: int = 0
    compressed_size: int = 0
    file_count: int = 0
    crc32: int = 0

    @staticmethod
    def read(stream: BinaryIO) -> "GroupHeader":
        return GroupHeader(*_read_struct(GroupHeader.FORMAT, stream))

    @property
    def stored_size(self):
        return self.compressed_size if self.compressed_size else self.original_size


class IceFlags(IntFlag):
    ENCRYPTED = 0x01
    KRAKEN = 0x08


@dataclass
class IceArchiveHeader:
    FORMAT: ClassVar[str] = "<I4xIIIIII"

    signature: int = 0x00454349  # "ICE\0"
    # 4 byte padding
    version: int = 4
    magic_80: int = 0x80
    magic_ff: int = 0xFF
    crc32: int = 0
    flags: IceFlags = IceFlags.ENCRYPTED
    file_size: int = 0

    @staticmethod
    def read(stream: BinaryIO) -> "GroupHeader":
        return IceArchiveHeader(*_read_struct(IceArchiveHeader.FORMAT, stream))


@dataclass
class DataFile:
    data: bytes
    index: int

    @property
    def name(self):
        if not self.data:
            return ""

        if _is_nifl(self.data):
            return f"namelessNIFLFile_{self.index}.bin"

        if _is_headerless_file(self.data):
            return f"namelessFile_{self.index}.bin"

        size = struct.unpack_from("I", self.data, 0x10)[0]
        name: bytes = struct.unpack_from(f"{size}s", self.data, 0x40)[0]
        return name.rstrip(b"\0").decode()


@dataclass
class IceFile:
    header: IceArchiveHeader
    group1_header: GroupHeader = None
    group2_header: GroupHeader = None
    group1_files: list[DataFile] = field(default_factory=list)
    group2_files: list[DataFile] = field(default_factory=list)

    @staticmethod
    def read(stream: BinaryIO) -> "IceFile":
        header = IceArchiveHeader.read(stream)

        match header.version:
            case 3:
                return IceFileV3.read_after_header(header, stream)
            case 4:
                return IceFileV4.read_after_header(header, stream)
            case 5 | 6 | 7 | 8 | 9:
                return IceFileV5.read_after_header(header, stream)

        raise ValueError(f"Invalid version {header.version}")


class IceFileV3(IceFile):
    @staticmethod
    def read_after_header(header: IceArchiveHeader, stream: BinaryIO) -> "IceFileV3":
        assert header.version == 3

        return IceFileV3(header=header)


class IceFileV4(IceFile):
    SECOND_PASS_THRESHOLD: ClassVar[int] = 0x19000

    @staticmethod
    def read_after_header(header: IceArchiveHeader, stream: BinaryIO) -> "IceFileV4":
        assert header.version == 4

        encrypted = bool(header.flags & IceFlags.ENCRYPTED)
        kraken = bool(header.flags & IceFlags.KRAKEN)
        keys = get_blowfish_keys(stream.read(0x100), header.file_size)

        if header.flags & IceFlags.ENCRYPTED:
            # stream.seek(0, os.SEEK_SET)
            # header_bytes = stream.read(0x120)
            # block_bytes = stream.read(0x30)
            cipher = blowfish.Cipher(keys.group_headers_key)
            group_header_bytes = cipher.decrypt_block(stream.read(0x30))
            # TODO?
        else:
            group_header_bytes = stream.read(0x30)

        group_header_stream = BytesIO(group_header_bytes)
        group1_header = GroupHeader.read(group_header_stream)
        group2_header = GroupHeader.read(group_header_stream)

        group1_data = bytes()
        group2_data = bytes()

        if group1_header.stored_size:
            group1_data = extract_group(
                group1_header,
                stream,
                kraken_compressed=kraken,
                encrypted=encrypted,
                keys=keys.group1_keys,
                second_pass_threshold=IceFileV4.SECOND_PASS_THRESHOLD,
            )

        if group2_header.stored_size:
            group2_data = extract_group(
                group2_header,
                stream,
                kraken_compressed=kraken,
                encrypted=encrypted,
                keys=keys.group2_keys,
                second_pass_threshold=IceFileV4.SECOND_PASS_THRESHOLD,
            )

        group1_files = split_group(group1_header, group1_data) if group1_data else []
        group2_files = split_group(group2_header, group2_data) if group2_data else []

        return IceFileV4(
            header=header,
            group1_header=group1_header,
            group2_header=group2_header,
            group1_files=group1_files,
            group2_files=group2_files,
        )


class IceFileV5(IceFile):
    @staticmethod
    def read_after_header(header: IceArchiveHeader, stream: BinaryIO) -> "IceFileV5":
        assert 5 <= header.version <= 9

        return IceFileV5(header=header)


def extract_group(
    header: GroupHeader,
    stream: BinaryIO,
    kraken_compressed=False,
    encrypted=False,
    keys: Optional[Tuple[bytes, bytes]] = None,
    second_pass_threshold=0,
    v3_decrypt=False,
) -> bytes:
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
    if not v3_decrypt:
        data = floatage_decrypt_block(data, keys[0])

    cipher1 = blowfish.Cipher(keys[0])
    data = cipher1.decrypt_block(data)

    if not v3_decrypt and len(data) < second_pass_threshold:
        cipher2 = blowfish.Cipher(keys[1])
        data = cipher2.decrypt_block(data)

    return data


def decompress_group(data: bytes, out_size: int, kraken_compressed: bool) -> bytes:
    if kraken_compressed:
        return decompress_kraken(data, out_size)

    data = [b ^ 0x95 for b in data]
    return decompress_prs(data, out_size)


def split_group(header: GroupHeader, data: bytes) -> list[bytes]:
    if _is_nifl(data):
        return _split_headerless_nifl(header, data)

    if _is_headerless_file(data):
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
            files.append(DataFile(data=stream.read(), index=i))
            break

        size = _read_struct("16xi", stream)[0]

        stream.seek(size - 0x10, os.SEEK_CUR)
        nof0_size = _read_struct("i", stream)[0] + 8

        # Add padding bytes
        nof0_size += 0x10 - (nof0_size % 0x10)

        # Add NOF0 size and NEND bytes
        size += nof0_size + 0x10

        stream.seek(start, os.SEEK_SET)
        files.append(DataFile(data=stream.read(size), index=i))

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
        size = _read_struct("4xi", stream)[0]

        stream.seek(start, os.SEEK_SET)
        files.append(DataFile(data=stream.read(size), index=i))

    return files
