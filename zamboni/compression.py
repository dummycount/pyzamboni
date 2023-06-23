"""
Compression options
"""
from dataclasses import dataclass
from typing import Literal, Optional


DEFAULT_COMPRESS_LEVEL = 3


@dataclass
class CompressOptions:
    """Selects the type of compression to use"""

    mode: Literal["none", "kraken", "prs"] = "none"
    level: int = DEFAULT_COMPRESS_LEVEL

    @staticmethod
    def parse(value: Optional[str]):
        """Parse a string as compression options"""
        if not value:
            return CompressOptions()

        match value:
            case "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9":
                return CompressOptions("kraken", int(value))

            case "kraken":
                return CompressOptions("kraken")

            case "prs":
                return CompressOptions("prs")

            case _:
                raise TypeError(
                    'Compression mode must be 0-9, "kraken", "prs", or None'
                )

    def __bool__(self):
        return self.mode != "none"
