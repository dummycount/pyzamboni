from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import struct
from typing import BinaryIO, ClassVar, Optional
from .util import is_headerless_file, pad_to_multiple, read_struct


@dataclass
class DataFileHeader:
    FORMAT: ClassVar[str] = "<4sIIIII40x"

    extension: bytes  # 4 bytes, no period
    file_size: int  # file size including header
    data_size: int  # file size without header
    header_size: int  # typically a multiple of 0x10
    filename_size: int
    field_0x14: int = 1  # unknown use. Always 0x1
    # unused 40 bytes
    filename_bytes: bytes = ""
    # pad out to header_size

    @staticmethod
    def read(stream: BinaryIO) -> "DataFileHeader":
        start = stream.tell()
        header = DataFileHeader(*read_struct(DataFileHeader.FORMAT, stream))

        header.filename_bytes = read_struct(f"{header.filename_size}s", stream)[0]

        stream.seek(start + header.header_size, os.SEEK_SET)

        return header

    @staticmethod
    def for_file(filename: str, size: int):
        extension = Path(filename).suffix.removeprefix(".").encode().ljust(4, b"\0")
        filename_bytes = filename.encode() + b"\0"

        header_size = struct.calcsize(DataFileHeader.FORMAT) + len(filename_bytes)
        header_size = pad_to_multiple(header_size, 0x10)
        file_size = pad_to_multiple(size + header_size, 0x10)

        return DataFileHeader(
            extension=extension,
            file_size=file_size,
            data_size=size,
            header_size=header_size,
            filename_size=len(filename_bytes),
            filename_bytes=filename_bytes,
        )

    @property
    def pad_size(self) -> int:
        """Number of padding bytes on the end of the file data"""
        return self.file_size - self.header_size - self.data_size

    def write(self, stream: BinaryIO):
        filename_space = self.header_size - struct.calcsize(DataFileHeader.FORMAT)

        assert len(self.filename_bytes) <= filename_space

        stream.write(
            struct.pack(
                DataFileHeader.FORMAT,
                self.extension,
                self.file_size,
                self.data_size,
                self.header_size,
                self.filename_size,
                self.field_0x14,
            )
        )
        stream.write(self.filename_bytes)

        padding = b"\0" * (filename_space - len(self.filename_bytes))
        stream.write(padding)


@dataclass
class DataFile:
    name: str
    data: bytes
    header: Optional[DataFileHeader] = None

    @staticmethod
    def from_stream(stream: BinaryIO, file_index=0):
        start = stream.tell()
        ext = stream.read(4)
        stream.seek(start, os.SEEK_SET)

        if is_headerless_file(ext):
            header = None
            data = stream.read()
            name = f"unnamed_{file_index}.bin"
        else:
            header = DataFileHeader.read(stream)
            data = stream.read(header.data_size)
            name = header.filename_bytes.decode().rstrip("\0")

            if pad_size := header.pad_size:
                stream.seek(pad_size, os.SEEK_CUR)

        return DataFile(name=name, header=header, data=data)

    @staticmethod
    def from_bytes(data: bytes, file_index=0):
        return DataFile.from_stream(BytesIO(data), file_index=file_index)

    def update_header(self):
        self.header = DataFileHeader.for_file(self.name, len(self.data))

    def write(self, stream: BinaryIO, include_header=False):
        if include_header:
            self.update_header()
            self.header.write(stream)

        stream.write(self.data)

        if include_header and self.header.pad_size:
            stream.write(b"\0" * self.header.pad_size)
