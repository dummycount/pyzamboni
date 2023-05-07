from pathlib import Path
from typing import Any, Generator, Iterable, Optional, overload

from .datafile import DataFile
from .icefile import IceFile


@overload
def unpack(ice: IceFile, out_dir: Path, use_groups=False) -> Generator[Path, Any, None]:
    """
    Unpack an ICE archive

    :param ice: ICE file to unpack
    :param out_dir: Output directory
    :param use_groups: If True, write files to "group1" and "group2" subdirectories.
    """


@overload
def unpack(
    ice: Path | str, out_dir: Optional[Path] = None, use_groups=False
) -> Generator[Path, Any, None]:
    """
    Unpack an ICE archive

    :param ice: Path to ICE file to unpack
    :param out_dir: Output directory. Defaults to "<path>.extracted"
    :param use_groups: If True, write files to "group1" and "group2" subdirectories.
    """


def unpack(ice: IceFile | Path | str, out_dir: Optional[Path] = None, use_groups=False):
    if isinstance(ice, (Path, str)):
        ice_path = ice
        ice = IceFile.read(ice_path)

        if out_dir is None:
            out_dir = ice_path.with_suffix(".extracted")
    else:
        if out_dir is None:
            raise ValueError("out_dir must be specified")

    if use_groups:
        group1_dir = out_dir / "group1"
        group2_dir = out_dir / "group2"
    else:
        group1_dir = out_dir
        group2_dir = out_dir

    unpacked: list[Path] = []

    if ice.group1_files:
        unpacked += unpack_group(ice.group1_files, group1_dir)

    if ice.group2_files:
        unpacked += unpack_group(ice.group2_files, group2_dir)

    return unpacked


def unpack_group(files: Iterable[DataFile], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    unpacked: list[Path] = []

    for data_file in files:
        path = out_dir / data_file.name
        with path.open(mode="wb") as out_file:
            out_file.write(data_file.data())

        unpacked.append(path)

    return unpacked
