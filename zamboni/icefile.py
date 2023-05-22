from dataclasses import dataclass, field
from enum import IntFlag
from io import BytesIO
from pathlib import Path
import struct
from typing import BinaryIO, ClassVar

from .compression import CompressOptions
from .crc import crc32
from .datafile import DataFile
from .group import (
    GroupHeader,
    combine_group,
    compress_group,
    extract_group,
    get_group_header,
    split_group,
)
from .util import read_struct, set_flag
from .encrpytion import blowfish_decrypt, get_blowfish_keys


class IceFlags(IntFlag):
    NONE = 0
    ENCRYPTED = 0x01
    KRAKEN_COMPRESSED = 0x08


# TODO: v3 doesn't use this header format
@dataclass
class IceArchiveHeader:
    SIGNATURE: ClassVar[bytes] = b"ICE\0"
    FORMAT: ClassVar[str] = "<4s4xIIIIII"

    signature: bytes = SIGNATURE  # 4 bytes
    # 4 byte padding
    version: int = 4
    magic_80: int = 0x80
    magic_ff: int = 0xFF
    crc32: int = 0
    flags: IceFlags = IceFlags.NONE
    file_size: int = 0

    @staticmethod
    def read(stream: BinaryIO) -> "IceArchiveHeader":
        header = IceArchiveHeader(*read_struct(IceArchiveHeader.FORMAT, stream))

        if header.signature != IceArchiveHeader.SIGNATURE:
            raise ValueError("Not an ICE archive.")

        return header

    def write(self, stream: BinaryIO):
        stream.write(
            struct.pack(
                IceArchiveHeader.FORMAT,
                self.signature,
                self.version,
                self.magic_80,
                self.magic_ff,
                self.crc32,
                self.flags,
                self.file_size,
            )
        )

    @property
    def encrypted(self):
        return self.flags & IceFlags.ENCRYPTED != 0

    @encrypted.setter
    def encrypted(self, value: bool):
        self.flags = set_flag(self.flags, IceFlags.ENCRYPTED, value)

    @property
    def kraken_compressed(self):
        return self.flags & IceFlags.KRAKEN_COMPRESSED != 0

    @kraken_compressed.setter
    def kraken_compressed(self, value: bool):
        self.flags = set_flag(self.flags, IceFlags.KRAKEN_COMPRESSED, value)


@dataclass
class IceFile:
    header: IceArchiveHeader = field(default_factory=IceArchiveHeader)
    group1_header: GroupHeader = None
    group2_header: GroupHeader = None
    group1_files: list[DataFile] = field(default_factory=list)
    group2_files: list[DataFile] = field(default_factory=list)

    @staticmethod
    def read(stream: BinaryIO | Path | str) -> "IceFile":
        if isinstance(stream, (Path, str)):
            with open(stream, "rb") as file:
                return IceFile.read(file)

        header = IceArchiveHeader.read(stream)

        match header.version:
            case 3:
                return IceFileV3.read_after_header(header, stream)
            case 4:
                return IceFileV4.read_after_header(header, stream)
            case 5:
                return IceFileV5.read_after_header(header, stream)

        raise ValueError(f"Invalid version {header.version}")

    def write(
        self,
        stream: BinaryIO | Path | str,
        compression=CompressOptions(),
        encrypt=False,
    ):
        if isinstance(stream, (Path, str)):
            with open(stream, "wb") as file:
                self.write(file, compression=compression, encrypt=encrypt)

        self._write(stream, compression=compression, encrypt=encrypt)

    def _write(self, stream: BinaryIO, compression: CompressOptions, encrypt: bool):
        raise NotImplementedError()


class IceFileV3(IceFile):
    @staticmethod
    def read_after_header(header: IceArchiveHeader, stream: BinaryIO) -> "IceFileV3":
        assert header.version == 3

        return IceFileV3(header=header)

    def _write(self, stream: BinaryIO, compression: CompressOptions, encrypt: bool):
        pass


class IceFileV4(IceFile):
    # 0x20 archive header, 0x100 encryption keys, 0x30 group headers
    HEADER_SIZE: ClassVar[int] = 0x150
    SECOND_PASS_THRESHOLD: ClassVar[int] = 0x19000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header.version = 4

    @staticmethod
    def read_after_header(header: IceArchiveHeader, stream: BinaryIO) -> "IceFileV4":
        assert header.version == 4

        keys = get_blowfish_keys(stream.read(0x100), header.file_size)

        group_header_data = stream.read(0x30)

        if header.encrypted:
            group_header_data = blowfish_decrypt(
                group_header_data, keys.group_headers_key
            )

        group_header_stream = BytesIO(group_header_data)
        group1_header = GroupHeader.read(group_header_stream)
        group2_header = GroupHeader.read(group_header_stream)

        group1_data = extract_group(
            group1_header,
            stream,
            compression="kraken" if header.kraken_compressed else "prs",
            encrypted=header.encrypted,
            keys=keys.group1_keys,
            second_pass_threshold=IceFileV4.SECOND_PASS_THRESHOLD,
        )

        group2_data = extract_group(
            group2_header,
            stream,
            compression="kraken" if header.kraken_compressed else "prs",
            encrypted=header.encrypted,
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

    def _write(self, stream: BinaryIO, compression: CompressOptions, encrypt: bool):
        self.header.encrypted = encrypt
        self.header.kraken_compressed = compression.mode == "kraken"

        group1_data = combine_group(self.group1_files)
        group2_data = combine_group(self.group2_files)
        group1_original_size = len(group1_data)
        group2_original_size = len(group2_data)

        group1_data = compress_group(group1_data, options=compression)
        group2_data = compress_group(group2_data, options=compression)

        self.group1_header = get_group_header(
            data=group1_data,
            file_count=len(self.group1_files),
            original_size=group1_original_size,
        )
        self.group2_header = get_group_header(
            data=group2_data,
            file_count=len(self.group2_files),
            original_size=group2_original_size,
        )

        self.header.file_size = (
            IceFileV4.HEADER_SIZE + len(group1_data) + len(group2_data)
        )
        self.header.crc32 = crc32(group1_data, group2_data)
        self.header.write(stream)

        if self.header.encrypted:
            # TODO: write encryption keys
            raise NotImplementedError()
        else:
            stream.write(b"\0" * 0x100)

        self.group1_header.write(stream)
        self.group2_header.write(stream)

        # TODO: in an actual file, this is either 0 or almost but not quite the
        # original size. What are these values?
        stream.write(struct.pack("<II8x", group1_original_size, group2_original_size))
        stream.write(group1_data)
        stream.write(group2_data)


class IceFileV5(IceFile):
    @staticmethod
    def read_after_header(header: IceArchiveHeader, stream: BinaryIO) -> "IceFileV5":
        assert 5 <= header.version <= 9

        return IceFileV5(header=header)

    def _write(self, stream: BinaryIO, compression: CompressOptions, encrypt: bool):
        pass
