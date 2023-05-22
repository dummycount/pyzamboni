"""
Oodle compression
"""

# pylint: disable=unused-argument

def kraken_compress(data: bytes, level=3) -> bytes:
    """
    Compress data to Kraken format

    :param data: Data to compress
    :param level: Compression level. 0 = none, 9 = max
    :raises ValueError:
    """

def kraken_decompress(data: bytes, out_size: int) -> bytes:
    """
    Decompress data from Kraken format

    :param data: Data to decompress
    :param out_size: Expected size of the output data
    :raises ValueError:
    """
