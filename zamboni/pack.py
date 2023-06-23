"""
Pack files into an ICE archive
"""
from pathlib import Path
import re
from typing import BinaryIO, Iterable, Optional, Type, TypeVar

from .compression import CompressOptions
from .datafile import DataFile
from .icefile import IceFile, IceFileV3, IceFileV4


_T = TypeVar("_T", bound=Type[IceFile])


def pack(
    stream: BinaryIO,
    paths: Path | Iterable[Path],
    group1_files: Optional[Iterable[str]] = None,
    file_type: _T | int = IceFileV4,
    compression=CompressOptions(),
    encrypt=False,
):
    """
    Pack files into an ICE archive

    :param stream: Output stream
    :param paths: Paths to files/directories to pack
    :param group1_files: List or regexes matching files to place in group 1.
        (Files in a directory named "group1" are automatically included.)
    :param file_type: IceFile subclass or version number of the format to use
    :param compression: Compression options
    :param encrypt: Encrypt the archive?
    """
    group1, group2 = group_files(paths, group1_files=group1_files)

    if not group1 and not group2:
        raise ValueError("No files to pack")

    if isinstance(file_type, int):
        match file_type:
            case 3:
                file_type = IceFileV3
            case 4:
                file_type = IceFileV4
            case _:
                raise ValueError(f"Unknown format version {file_type}")

    ice = file_type()
    ice.group1_files = [DataFile(name=f.name, data=f.read_bytes()) for f in group1]
    ice.group2_files = [DataFile(name=f.name, data=f.read_bytes()) for f in group2]

    ice.write(stream, compression=compression, encrypt=encrypt)

    return group1, group2


def group_files(
    paths: Path | Iterable[Path],
    base_path: Optional[Path] = None,
    group1_files: Optional[Iterable[str]] = None,
):
    """Sort files into (group1, group2)"""
    if isinstance(paths, Path):
        paths = [paths]

    group1: list[Path] = []
    group2: list[Path] = []

    for path in paths:
        if path.is_dir():
            sub1, sub2 = group_files(
                (f for f in path.rglob("*") if f.is_file()),
                base_path=path,
                group1_files=group1_files,
            )
            group1.extend(sub1)
            group2.extend(sub2)

        elif path.is_file():
            if is_group1(path, base_path, group1_files):
                group1.append(path)
            else:
                group2.append(path)

    return group1, group2


def is_group1(path: Path, base_path: Optional[Path], group1_files: Iterable[str]):
    """Get whether a file should be in group 1"""
    if base_path:
        if "group1" in path.relative_to(base_path).parts:
            return True

    if group1_files:
        return any(
            re.match(pattern, path.name, re.IGNORECASE) for pattern in group1_files
        )

    return False
