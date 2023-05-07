from dataclasses import dataclass
import struct
from .util import is_headerless_file, is_nifl


@dataclass
class DataFile:
    raw_data: bytes
    file_index: int

    _name: str = None

    @property
    def name(self):
        if self._name is not None:
            return self._name

        if not self.raw_data:
            return ""

        if is_nifl(self.raw_data):
            return f"unnamed_NIFL_{self.file_index}.bin"

        if is_headerless_file(self.raw_data):
            return f"unnamed_{self.file_index}.bin"

        size = struct.unpack_from("I", self.raw_data, 0x10)[0]
        name_bytes: bytes = struct.unpack_from(f"{size}s", self.raw_data, 0x40)[0]

        self._name = name_bytes.decode(encoding="ascii").rstrip("\0")
        return self._name


    def data(self):
        if is_nifl(self.raw_data) or is_headerless_file(self.raw_data):
            return self.raw_data

        data_size, header_size = struct.unpack_from("II", self.raw_data, 0x8)
        return self.raw_data[header_size : header_size + data_size]


