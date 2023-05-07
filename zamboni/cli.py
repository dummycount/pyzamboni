import argparse
from pathlib import Path
from typing import Iterable

from .datafile import DataFile
from .icefile import IceFile
from .unpack import unpack
from .util import naturalsize


def main():
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

    unpack_parser = subparsers.add_parser(
        "unpack", help="extract files from an ICE archive"
    )
    unpack_parser.add_argument("icefile", type=Path, help="file to extract")
    unpack_parser.add_argument("--out", "-o", type=Path, help="output directory")
    unpack_parser.add_argument(
        "--groups", "-g", action="store_true", help="use group subdirectories"
    )

    args = parser.parse_args()

    match args.command:
        case "info":
            print_info(ice_path=args.icefile, humanize=args.human_readable)

        case "list":
            print_file_list(ice_path=args.icefile, use_groups=args.groups)

        case "pack":
            pass

        case "unpack":
            for path in unpack(ice=args.icefile, out_dir=args.out, use_groups=args.groups):
                print(path)


def print_info(ice_path: Path, humanize=False):
    def formatsize(num):
        return naturalsize(num) if humanize else num

    ice = IceFile.read(ice_path)

    print(f"Version: {ice.header.version}")
    print(f"Flags:   0x{ice.header.flags:04x}")
    print(f"Size:    {formatsize(ice.header.file_size)}")

    if ice.group1_files:
        print_group_info("Group 1:", ice.group1_files, humanize)

    if ice.group2_files:
        print_group_info("Group 2:", ice.group2_files, humanize)


def print_group_info(header: str, files: Iterable[DataFile], humanize=False):
    def formatsize(num):
        return naturalsize(num) if humanize else num

    column_width = max(len(f.name) for f in files)

    print()
    print(header)
    for file in files:
        print(f"  {file.name.ljust(column_width)}  {formatsize(len(file.raw_data))}")


def print_file_list(ice_path: Path, use_groups=False):
    group1_prefix = "group1/" if use_groups else ""
    group2_prefix = "group2/" if use_groups else ""

    ice = IceFile.read(ice_path)

    for file in ice.group1_files:
        print(group1_prefix + file.name)

    for file in ice.group2_files:
        print(group2_prefix + file.name)
