from dataclasses import dataclass
import struct
from .util import is_headerless_file, is_nifl


@dataclass
class DataFile:
    data: bytes
    file_index: int

    _name: str = None

    @property
    def name(self):
        if self._name is not None:
            return self._name

        if not self.data:
            return ""

        if is_nifl(self.data):
            return f"unnamed_NIFL_{self.file_index}.bin"

        if is_headerless_file(self.data):
            return f"unnamed_{self.file_index}.bin"

        size = struct.unpack_from("I", self.data, 0x10)[0]
        name_bytes: bytes = struct.unpack_from(f"{size}s", self.data, 0x40)[0]

        self._name = name_bytes.decode(encoding="ascii").rstrip("\0")
        return self._name
