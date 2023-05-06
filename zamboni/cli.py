import argparse
from pathlib import Path
from .icefile import IceFile


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    unpack_parser = subparsers.add_parser("unpack")
    unpack_parser.add_argument("icefile", type=Path)
    unpack_parser.add_argument("--out", "-o", type=Path)

    args = parser.parse_args()

    match args.command:
        case "unpack":
            unpack(args.icefile, args.out)


def unpack(ice_file: Path, out_dir: Path = None):
    if out_dir is None:
        out_dir = ice_file.with_suffix(".extracted")

    out_dir.mkdir(parents=True, exist_ok=True)

    with ice_file.open(mode="rb") as in_file:
        ice = IceFile.read(in_file)

        for data_file in ice.group2_files:
            print(data_file.name)
            path = out_dir / data_file.name
            with path.open(mode="wb") as out_file:
                out_file.write(data_file.data)
