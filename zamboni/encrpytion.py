from dataclasses import dataclass
from struct import unpack_from, pack
import struct
from typing import Tuple

from Crypto.Cipher import Blowfish

from .crc import crc32
from .util import int32_to_uint32


@dataclass
class BlowfishKeys:
    group_headers_key: bytes
    group1_keys: Tuple[bytes, bytes]
    group2_keys: Tuple[bytes, bytes]


# TODO: does python-blowfish have a function for this?
def floatage_decrypt_block(data: bytes, key: bytes, shift=16):
    key_uint = unpack_from("<I", key)[0]
    xor_byte = ((key_uint >> shift) ^ key_uint) & 0xFF

    return bytes(b ^ xor_byte if b and b != xor_byte else b for b in data)


def _endian_swap(data: bytes):
    return b"".join(struct.pack(">I", x[0]) for x in struct.iter_unpack("<I", data))


def blowfish_decrypt(data: bytes, key: bytes):
    dlen = len(data)
    split = dlen - (dlen % Blowfish.block_size)
    blocks, remainder = data[0:split], data[split:]

    cipher = Blowfish.new(key, Blowfish.MODE_ECB)

    # TODO: can we avoid needing to swap byte order back and forth here?
    # Can't find any way to set the cipher to little endian.
    decrypted = _endian_swap(cipher.decrypt(_endian_swap(blocks)))

    # TODO: is leaving the remainder unmodified correct or a bug in the C# code?
    return decrypted + remainder


def get_blowfish_keys(magic_numbers: bytes, file_size: int) -> BlowfishKeys:
    int_6c = unpack_from("i", magic_numbers, 0x6C)[0]
    crc = crc32(magic_numbers[0x7C:0xDC])

    temp_key = int32_to_uint32(crc ^ int_6c ^ file_size ^ 0x4352F5C2)

    key = _get_key(magic_numbers, temp_key)

    def swap(uint32: int, right_shift: int):
        left_shift = 32 - right_shift
        return (uint32 >> right_shift) | ((uint32 << left_shift) & 0xFFFFFFFF)

    group1_blowfish0 = _calc_blowfish_keys(magic_numbers, key)
    group1_blowfish1 = _get_key(magic_numbers, group1_blowfish0)
    group2_blowfish0 = swap(group1_blowfish0, 15)
    group2_blowfish1 = swap(group1_blowfish1, 15)
    headers_key = swap(group1_blowfish0, 19)

    return BlowfishKeys(
        group_headers_key=pack("<I", headers_key),
        group1_keys=(pack("<I", group1_blowfish0), pack("<I", group1_blowfish1)),
        group2_keys=(pack("<I", group2_blowfish0), pack("<I", group2_blowfish1)),
    )


def _get_key(keys: bytes, temp_key: int):
    num1 = ((temp_key & 0xFF) + 93) & 0xFF
    num2 = ((temp_key >> 8) + 63) & 0xFF
    num3 = ((temp_key >> 16) + 69) & 0xFF
    num4 = ((temp_key >> 24) - 58) & 0xFF

    def get_byte(idx: int, shift1: int, shift2: int, shift3: int):
        return (((keys[idx] << shift1) | (keys[idx] >> shift2)) & 0xFF) << shift3

    b1 = get_byte(num2, 7, 1, 24)
    b2 = get_byte(num4, 6, 2, 16)
    b3 = get_byte(num1, 5, 3, 8)
    b4 = get_byte(num3, 5, 3, 0)

    return b1 | b2 | b3 | b4


def _calc_blowfish_keys(keys: bytes, temp_key: int):
    temp_key1 = 0x8E02C25C ^ temp_key
    num1 = 0x24924925 * temp_key1 >> 32
    num2 = ((temp_key1 - num1 >> 1) + num1 >> 2) * 7

    for _ in range(temp_key1 - num2 + 2):
        temp_key1 = _get_key(keys, temp_key1)

    return int32_to_uint32(temp_key1 ^ 0x4352F5C2 ^ -0x32AFC862)
