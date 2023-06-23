"""
Command line interface
"""
import argparse
from pathlib import Path
from typing import Iterable

from .compression import CompressOptions
from .datafile import DataFile
from .icefile import IceFile
from .pack import pack
from .unpack import unpack
from .util import naturalsize


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    info_parser = subparsers.add_parser("info", help="print ICE archive info")
    info_parser.add_argument("icefile", type=Path, help="file to inspect")
    info_parser.add_argument(
        "--human-readable",
        "-H",
        action="store_true",
        help="print sizes in human-readable format",
    )

    list_parser = subparsers.add_parser(
        "list", help="list files contained in an ICE archive"
    )
    list_parser.add_argument("icefile", type=Path, help="file to inspect")
    list_parser.add_argument(
        "--groups", "-g", action="store_true", help="use group subdirectories"
    )

    pack_parser = subparsers.add_parser("pack", help="pack files into an ICE archive")
    pack_parser.add_argument(
        "files", type=Path, nargs="+", help="files or directories to pack"
    )
    pack_parser.add_argument(
        "--out", "-o", type=Path, help="output file", required=True
    )
    pack_parser.add_argument(
        "--compress",
        "-c",
        type=CompressOptions.parse,
        nargs="?",
        help="compression level (0-9 or 'prs')",
    )
    pack_parser.add_argument(
        "--encrypt", "-e", action="store_true", help="encrypt the archive"
    )
    pack_parser.add_argument(
        "--version", "-v", type=int, default=4, help="format version (3 or 4)"
    )
    pack_parser.add_argument(
        "--group1", "-1", nargs="*", help="regular expression(s) matching group 1 files"
    )

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

    args = parser.parse_args()

    match args.command:
        case "info":
            print_info(ice_path=args.icefile, humanize=args.human_readable)

        case "list":
            print_file_list(ice_path=args.icefile, use_groups=args.groups)

        case "pack":
            pack_file(
                files=args.files,
                out_path=args.out,
                file_type=args.version,
                group1_files=args.group1,
                compression=CompressOptions.parse(args.compress),
                encrypt=args.encrypt,
            )

        case "unpack":
            unpack_file(
                ice_path=args.icefile,
                out_dir=args.out,
                use_groups=args.groups,
                dump_raw_data=args.raw,
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
    file_type: int,
    group1_files: list[str],
    compression: CompressOptions,
    encrypt: bool,
):
    """Pack files into an ICE archive"""
    with out_path.open("wb") as f:
        pack(
            f,
            files,
            file_type=file_type,
            group1_files=group1_files,
            compression=compression,
            encrypt=encrypt,
        )


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
