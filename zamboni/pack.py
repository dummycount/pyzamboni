"""
Pack files into an ICE archive
"""
from pathlib import Path
import re
from typing import BinaryIO, Iterable, Optional, Type, TypeVar

from .compression import CompressOptions
from .datafile import DataFile
from .icefile import IceFile, IceFileV4


_T = TypeVar("_T", bound=Type[IceFile])


def parse_file_list(value: Iterable[str]):
    def _to_regex(pattern: str):
        escaped = re.escape(pattern)
        if pattern.startswith("."):
            escaped = rf".*{escaped}"

        return re.compile(rf"^{escaped}$", re.IGNORECASE)

    return [_to_regex(part) for part in value]


def pack(
    file: str | Path | BinaryIO,
    paths: Path | Iterable[Path],
    group1_files: Optional[Iterable[str]] = None,
    exclude_files: Optional[Iterable[str]] = None,
    file_type: _T | int = IceFileV4,
    compression=CompressOptions(),
    encrypt=False,
):
    """
    Pack files into an ICE archive

    :param file: Output stream or file path
    :param paths: Paths to files/directories to pack
    :param group1_files: List of file names and/or file extensions to place in group 1.
        (Files in a directory named "group1" are automatically included.)
    :param exclude_files: List of file names and/or file extensions to ignore.
    :param file_type: IceFile subclass or version number of the format to use
    :param compression: Compression options
    :param encrypt: Encrypt the archive?
    """
    if isinstance(file, (str, Path)):
        with open(file, mode="wb") as f:
            return pack(
                f,
                paths=paths,
                group1_files=group1_files,
                exclude_files=exclude_files,
                file_type=file_type,
                compression=compression,
                encrypt=encrypt,
            )

    group1_files = parse_file_list(group1_files or [])
    exclude_files = parse_file_list(exclude_files or [])

    group1, group2 = group_files(
        paths, group1_files=group1_files, exclude_files=exclude_files
    )

    if not group1 and not group2:
        raise ValueError("No files to pack")

    if isinstance(file_type, int):
        file_type = IceFile.get_file_type(file_type)

    ice: IceFile = file_type()
    ice.group1_files = [DataFile(name=f.name, data=f.read_bytes()) for f in group1]
    ice.group2_files = [DataFile(name=f.name, data=f.read_bytes()) for f in group2]

    ice.write(file, compression=compression, encrypt=encrypt)

    return group1, group2


def group_files(
    paths: Path | Iterable[Path],
    group1_files: list[re.Pattern],
    exclude_files: list[re.Pattern],
    base_path: Optional[Path] = None,
):
    """Sort files into (group1, group2)"""
    if isinstance(paths, Path):
        paths = [paths]

    group1: list[Path] = []
    group2: list[Path] = []

    for path in paths:
        if is_excluded(path, exclude_files):
            continue

        if path.is_dir():
            sub1, sub2 = group_files(
                (f for f in path.rglob("*") if f.is_file()),
                base_path=path,
                group1_files=group1_files,
                exclude_files=exclude_files,
            )
            group1.extend(sub1)
            group2.extend(sub2)

        elif path.is_file():
            if is_group1(path, base_path, group1_files):
                group1.append(path)
            else:
                group2.append(path)

    return group1, group2


def is_excluded(path: Path, exclude_files: Iterable[re.Pattern]):
    """Get whether a file should not be packed"""
    return any(pattern.match(path.name) for pattern in exclude_files)


def is_group1(
    path: Path, base_path: Optional[Path], group1_files: Iterable[re.Pattern]
):
    """Get whether a file should be in group 1"""
    if base_path:
        if "group1" in path.relative_to(base_path).parts:
            return True

    return any(pattern.match(path.name) for pattern in group1_files)
