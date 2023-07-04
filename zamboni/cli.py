"""
Command line interface
"""
import argparse
import itertools
from pathlib import Path
import re
from typing import Iterable, Optional

from .compression import CompressOptions
from .datafile import DataFile
from .icefile import IceFile
from .pack import pack
from .unpack import unpack
from .util import naturalsize


def _flatten_args(args: Optional[list[list[str]]]) -> list[str]:
    if args:
        return list(
            itertools.chain.from_iterable(re.split("[,;]", arg) for arg in args)
        )

    return []


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info command
    info_parser = subparsers.add_parser("info", help="print ICE archive info")
    info_parser.add_argument("icefile", type=Path, help="file to inspect")
    info_parser.add_argument(
        "--human-readable",
        "-H",
        action="store_true",
        help="print sizes in human-readable format",
    )

    # list command
    list_parser = subparsers.add_parser(
        "list", help="list files contained in an ICE archive"
    )
    list_parser.add_argument("icefile", type=Path, help="file to inspect")
    list_parser.add_argument(
        "--groups", "-g", action="store_true", help="use group subdirectories"
    )

    # unpack command
    unpack_parser = subparsers.add_parser(
        "unpack", help="extract files from an ICE archive"
    )
    unpack_parser.add_argument("icefile", type=Path, help="file to extract")
    unpack_parser.add_argument("--out", "-o", type=Path, help="output directory")
    unpack_parser.add_argument(
        "--groups", "-g", action="store_true", help="use group subdirectories"
    )
    unpack_parser.add_argument(
        "--raw", "-r", action="store_true", help="Do not strip ICE file headers"
    )

    # pack command
    pack_parser = subparsers.add_parser("pack", help="pack files into an ICE archive")
    pack_parser.add_argument(
        "--out", "-o", type=Path, help="output file", required=True
    )
    pack_parser.add_argument(
        "files", type=Path, nargs="+", help="files or directories to pack"
    )
    pack_parser.add_argument(
        "--compress",
        "-c",
        type=CompressOptions.parse,
        default="kraken",
        nargs="?",
        help="compression level ('none', 0-9, or 'prs', default: 3)",
    )
    pack_parser.add_argument(
        "--encrypt", "-e", action="store_true", help="encrypt the archive"
    )
    pack_parser.add_argument(
        "--version",
        "-v",
        type=int,
        default=4,
        help="format version (3 or 4, default: 4)",
    )
    pack_parser.add_argument(
        "--group1",
        "-1",
        nargs="*",
        help='file extensions and/or file names to include in group 1, e.g. ".acb,.snd"',
    )
    pack_parser.add_argument(
        "--ignore",
        "-i",
        nargs="*",
        help='file extensions and/or file names to ignore, e.g. ".mp4,.png"',
    )

    # repack command
    repack_parser = subparsers.add_parser("repack", help="")
    repack_parser.add_argument("icefile", type=Path, help="file to extract")

    repack_parser.add_argument(
        "--out", "-o", type=Path, help="output file", required=True
    )
    repack_parser.add_argument(
        "--compress",
        "-c",
        type=CompressOptions.parse,
        default="kraken",
        nargs="?",
        help="compression level ('none', 0-9, or 'prs', default: 3)",
    )
    repack_parser.add_argument(
        "--encrypt", "-e", action="store_true", help="encrypt the archive"
    )
    repack_parser.add_argument(
        "--version",
        "-v",
        type=int,
        default=4,
        help="format version (3 or 4, default: 4)",
    )

    args = parser.parse_args()

    match args.command:
        case "info":
            print_info(ice_path=args.icefile, humanize=args.human_readable)

        case "list":
            print_file_list(ice_path=args.icefile, use_groups=args.groups)

        case "unpack":
            unpack_file(
                ice_path=args.icefile,
                out_dir=args.out,
                use_groups=args.groups,
                dump_raw_data=args.raw,
            )

        case "pack":
            pack_file(
                files=args.files,
                out_path=args.out,
                version=args.version,
                group1_files=_flatten_args(args.group1),
                exclude_files=_flatten_args(args.ignore),
                compression=args.compress,
                encrypt=args.encrypt,
            )

        case "repack":
            repack_file(
                ice_path=args.icefile,
                out_path=args.out,
                version=args.version,
                compression=args.compress,
                encrypt=args.encrypt,
            )


def unpack_file(ice_path: Path, out_dir: Path, use_groups: bool, dump_raw_data: bool):
    """Extract an ICE archive and print the files extracted"""
    for path in unpack(
        ice_path, out_dir=out_dir, use_groups=use_groups, dump_raw_data=dump_raw_data
    ):
        print(path)


def pack_file(
    files: list[Path],
    out_path: Path,
    version: int,
    group1_files: list[str],
    exclude_files: list[str],
    compression: CompressOptions,
    encrypt: bool,
):
    """Pack files into an ICE archive"""
    with out_path.open("wb") as f:
        pack(
            f,
            files,
            file_type=version,
            group1_files=group1_files,
            exclude_files=exclude_files,
            compression=compression,
            encrypt=encrypt,
        )


def repack_file(
    ice_path: Path,
    out_path: Path,
    version: int,
    compression: CompressOptions,
    encrypt: bool,
):
    """Extract an ICE archive and pack it back into an archive with different options"""
    ice = IceFile.read(ice_path)

    file_type = IceFile.get_file_type(version)
    if file_type != type(ice):
        new_ice = file_type()
        new_ice.group1_files = ice.group1_files
        new_ice.group2_files = ice.group2_files
        ice = new_ice

    with out_path.open("wb") as f:
        ice.write(f, compression=compression, encrypt=encrypt)


def print_info(ice_path: Path, humanize=False):
    """Print ICE file metadata and file list"""

    def formatsize(num):
        return naturalsize(num) if humanize else num

    ice = IceFile.read(ice_path)

    print(f"Version: {ice.header.version}")
    print(f"Flags:   0x{ice.meta.flags:04x}")
    print(f"Size:    {formatsize(ice.meta.file_size)}")

    if ice.group1_files:
        print_group_info("Group 1:", ice.group1_files, humanize)

    if ice.group2_files:
        print_group_info("Group 2:", ice.group2_files, humanize)


def print_group_info(header: str, files: Iterable[DataFile], humanize=False):
    """Print files in a file group"""

    def formatsize(num):
        return naturalsize(num) if humanize else num

    column_width = max(len(f.name) for f in files)

    print()
    print(header)
    for file in files:
        print(f"  {file.name.ljust(column_width)}  {formatsize(len(file.data))}")


def print_file_list(ice_path: Path, use_groups=False):
    """Print files contained in an ICE archive"""

    group1_prefix = "group1/" if use_groups else ""
    group2_prefix = "group2/" if use_groups else ""

    ice = IceFile.read(ice_path)

    for file in ice.group1_files:
        print(group1_prefix + file.name)

    for file in ice.group2_files:
        print(group2_prefix + file.name)
