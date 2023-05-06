from dataclasses import dataclass, field
from enum import IntFlag
from io import BytesIO
from typing import BinaryIO, ClassVar

from .datafile import DataFile
from .group import GroupHeader, extract_group, split_group
from .util import read_struct, write_file
from .encrpytion import blowfish_decrypt, get_blowfish_keys


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
        return IceArchiveHeader(*read_struct(IceArchiveHeader.FORMAT, stream))


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

        raise NotImplementedError()


class IceFileV4(IceFile):
    SECOND_PASS_THRESHOLD: ClassVar[int] = 0x19000

    @staticmethod
    def read_after_header(header: IceArchiveHeader, stream: BinaryIO) -> "IceFileV4":
        assert header.version == 4

        encrypted = bool(header.flags & IceFlags.ENCRYPTED)
        kraken = bool(header.flags & IceFlags.KRAKEN)
        keys = get_blowfish_keys(stream.read(0x100), header.file_size)

        group_header_data = stream.read(0x30)

        if header.flags & IceFlags.ENCRYPTED:
            group_header_data = blowfish_decrypt(
                group_header_data, keys.group_headers_key
            )

        write_file(".testdata/test_decrypt_header.bin", group_header_data)

        group_header_stream = BytesIO(group_header_data)
        group1_header = GroupHeader.read(group_header_stream)
        group2_header = GroupHeader.read(group_header_stream)

        group1_data = extract_group(
            group1_header,
            stream,
            kraken_compressed=kraken,
            encrypted=encrypted,
            keys=keys.group1_keys,
            second_pass_threshold=IceFileV4.SECOND_PASS_THRESHOLD,
        )

        group2_data = extract_group(
            group2_header,
            stream,
            kraken_compressed=kraken,
            encrypted=encrypted,
            keys=keys.group2_keys,
            second_pass_threshold=IceFileV4.SECOND_PASS_THRESHOLD,
        )

        group1_files = split_group(group1_header, group1_data)
        group2_files = split_group(group2_header, group2_data)

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
