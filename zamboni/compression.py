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
    def parse(value: Optional[str | int]):
        """Parse a string as compression options"""

        match value:
            case CompressOptions():
                return value

            case "no" | "none" | None:
                return CompressOptions()

            case "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | int():
                return CompressOptions("kraken", int(value))

            case "kraken" | "yes":
                return CompressOptions("kraken")

            case "prs":
                return CompressOptions("prs")

            case _:
                raise TypeError(
                    f'Compression mode must be 0-9, "kraken", "prs", or "none". Got "{value}"'
                )

    def __bool__(self):
        return self.mode != "none"
