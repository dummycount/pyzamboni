"""
ICE archive files
"""
from dataclasses import dataclass, field
from enum import IntFlag
from io import BytesIO
import os
from pathlib import Path
import struct
from typing import BinaryIO, ClassVar, Optional, Tuple

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
    """Bitfield of metadata flags"""

    NONE = 0
    ENCRYPTED = 0x01
    KRAKEN_COMPRESSED = 0x08


@dataclass
class IceFileHeader:
    """Header at the start of every ICE file"""

    SIGNATURE: ClassVar[bytes] = b"ICE\0"
    FORMAT: ClassVar[str] = "<4s4xII"

    signature: bytes = SIGNATURE  # 4 bytes
    # 4 byte padding
    version: int = 4
    magic_80: int = 0x80

    @staticmethod
    def read(stream: BinaryIO) -> "IceFileHeader":
        """Read a header from a stream"""
        sig = IceFileHeader(*read_struct(IceFileHeader.FORMAT, stream))

        if sig.signature != IceFileHeader.SIGNATURE:
            raise ValueError("Not an ICE archive")

        return sig

    def write(self, stream: BinaryIO):
        """Write the header to a stream"""
        stream.write(
            struct.pack(
                IceFileHeader.FORMAT,
                self.signature,
                self.version,
                self.magic_80,
            )
        )


@dataclass
class IceFileMetadata:
    """Metadata about an ICE file"""

    FORMAT: ClassVar[str] = "<IIII"

    magic_ff: int = 0xFF
    crc32: int = 0
    flags: IceFlags = IceFlags.NONE
    file_size: int = 0

    @staticmethod
    def read(stream: BinaryIO) -> "IceFileMetadata":
        """Read metadata from a stream"""
        return IceFileMetadata(*read_struct(IceFileMetadata.FORMAT, stream))

    def write(self, stream: BinaryIO):
        """Write metadata to a stream"""
        stream.write(
            struct.pack(
                IceFileMetadata.FORMAT,
                self.magic_ff,
                self.crc32,
                self.flags,
                self.file_size,
            )
        )

    @property
    def encrypted(self):
        """Is the file encrypted?"""
        return self.flags & IceFlags.ENCRYPTED != 0

    @encrypted.setter
    def encrypted(self, value: bool):
        self.flags = set_flag(self.flags, IceFlags.ENCRYPTED, value)

    @property
    def kraken_compressed(self):
        """Does the file use Kraken compression?"""
        return self.flags & IceFlags.KRAKEN_COMPRESSED != 0

    @kraken_compressed.setter
    def kraken_compressed(self, value: bool):
        self.flags = set_flag(self.flags, IceFlags.KRAKEN_COMPRESSED, value)


@dataclass
class IceFile:
    """ICE archive file"""

    header: IceFileHeader = field(default_factory=IceFileHeader)
    meta: IceFileMetadata = field(default_factory=IceFileMetadata)
    group1_header: GroupHeader = None
    group2_header: GroupHeader = None
    group1_files: list[DataFile] = field(default_factory=list)
    group2_files: list[DataFile] = field(default_factory=list)

    @staticmethod
    def read(stream: BinaryIO | Path | str) -> "IceFile":
        """Read an ICE archive from a stream or file"""
        if isinstance(stream, (Path, str)):
            with open(stream, "rb") as file:
                return IceFile.read(file)

        signature = IceFileHeader.read(stream)

        match signature.version:
            case 3:
                return IceFileV3.read_after_header(signature, stream)
            case 4:
                return IceFileV4.read_after_header(signature, stream)

        raise ValueError(f"Invalid version {signature.version}")

    def write(
        self,
        stream: BinaryIO | Path | str,
        compression=CompressOptions(),
        encrypt=False,
    ):
        """Write an ICE archive to a stream or file"""
        if isinstance(stream, (Path, str)):
            with open(stream, "wb") as file:
                self.write(file, compression=compression, encrypt=encrypt)

        self.header.write(stream)
        self._write(stream, compression=compression, encrypt=encrypt)

    def _write(self, stream: BinaryIO, compression: CompressOptions, encrypt: bool):
        raise NotImplementedError()


class IceFileV3(IceFile):
    """Version 3 ICE archive"""

    SECOND_PASS_THRESHOLD: ClassVar[int] = 0x19000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header.version = 3

    @dataclass
    class GroupInfo:
        """Header providing extra file group info"""

        FORMAT: ClassVar[str] = "<II4xI"

        group1_size: int
        group2_size: int
        key: int

        @staticmethod
        def read(stream: BinaryIO):
            """Read info from a stream"""
            return IceFileV3.GroupInfo(*read_struct(IceFileV3.GroupInfo.FORMAT, stream))

    @staticmethod
    def read_after_header(header: IceFileHeader, stream: BinaryIO) -> "IceFileV3":
        """Read the data following the IceFileHeader"""
        assert header.version == 3

        group1_header = GroupHeader.read(stream)
        group2_header = GroupHeader.read(stream)

        group_info = IceFileV3.GroupInfo.read(stream)
        meta = IceFileMetadata.read(stream)

        # Skip padding
        stream.seek(0x30, os.SEEK_CUR)

        keys = IceFileV3._get_keys(group1_header, group2_header, group_info, meta)
        compression = CompressOptions("kraken" if meta.kraken_compressed else "prs")

        group1_data = extract_group(
            group1_header,
            stream,
            compression=compression,
            encrypted=meta.encrypted,
            keys=keys,
            second_pass_threshold=IceFileV3.SECOND_PASS_THRESHOLD,
            v3_decrypt=True,
        )

        group2_data = extract_group(
            group2_header,
            stream,
            compression=compression,
            encrypted=meta.encrypted,
            keys=keys,
            second_pass_threshold=IceFileV3.SECOND_PASS_THRESHOLD,
            v3_decrypt=True,
        )

        group1_files = split_group(group1_header, group1_data)
        group2_files = split_group(group2_header, group2_data)

        return IceFileV3(
            header=header,
            meta=meta,
            group1_header=group1_header,
            group2_header=group2_header,
            group1_files=group1_files,
            group2_files=group2_files,
        )

    @staticmethod
    def _get_keys(
        group1_header: GroupHeader,
        group2_header: GroupHeader,
        groups: GroupInfo,
        meta: IceFileMetadata,
    ) -> Optional[Tuple[bytes, bytes]]:
        if groups.group1_size:
            return (struct.pack("<I", groups.group1_size), b"")

        if meta.encrypted:
            key = (
                group1_header.original_size
                ^ group2_header.original_size
                ^ groups.group2_size
                ^ groups.key
                ^ 0xC8D7469A
            )

            return (struct.pack("<I", key), b"")

        return None

    def _write(self, stream: BinaryIO, compression: CompressOptions, encrypt: bool):
        raise NotImplementedError()


class IceFileV4(IceFile):
    """Version 4 ICE archive"""

    # 0x20 archive header, 0x100 encryption keys, 0x30 group headers
    HEADER_SIZE: ClassVar[int] = 0x150
    SECOND_PASS_THRESHOLD: ClassVar[int] = 0x19000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header.version = 4

    @staticmethod
    def read_after_header(header: IceFileHeader, stream: BinaryIO) -> "IceFileV4":
        """Read the data following the IceFileHeader"""
        assert header.version == 4

        meta = IceFileMetadata.read(stream)
        keys = get_blowfish_keys(stream.read(0x100), meta.file_size)

        group_header_data = stream.read(0x30)

        if meta.encrypted:
            group_header_data = blowfish_decrypt(
                group_header_data, keys.group_headers_key
            )

        group_header_stream = BytesIO(group_header_data)
        group1_header = GroupHeader.read(group_header_stream)
        group2_header = GroupHeader.read(group_header_stream)

        compression = CompressOptions("kraken" if meta.kraken_compressed else "prs")

        group1_data = extract_group(
            group1_header,
            stream,
            compression=compression,
            encrypted=meta.encrypted,
            keys=keys.group1_keys,
            second_pass_threshold=IceFileV4.SECOND_PASS_THRESHOLD,
        )

        group2_data = extract_group(
            group2_header,
            stream,
            compression=compression,
            encrypted=meta.encrypted,
            keys=keys.group2_keys,
            second_pass_threshold=IceFileV4.SECOND_PASS_THRESHOLD,
        )

        group1_files = split_group(group1_header, group1_data)
        group2_files = split_group(group2_header, group2_data)

        return IceFileV4(
            header=header,
            meta=meta,
            group1_header=group1_header,
            group2_header=group2_header,
            group1_files=group1_files,
            group2_files=group2_files,
        )

    def _write(self, stream: BinaryIO, compression: CompressOptions, encrypt: bool):
        self.meta.encrypted = encrypt
        self.meta.kraken_compressed = compression.mode == "kraken"

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

        self.meta.file_size = (
            IceFileV4.HEADER_SIZE + len(group1_data) + len(group2_data)
        )
        self.meta.crc32 = crc32(group1_data, group2_data)
        self.meta.write(stream)

        if self.meta.encrypted:
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
