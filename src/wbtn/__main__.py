import argparse
import sys
from pathlib import Path

from wbtn._base import JOURNAL_MODES

from . import Webtoon
from ._managers import ConnectionSettings

parser = argparse.ArgumentParser(
    prog="wbtn",
)
parser.set_defaults(subparser_name=None)

subparsers = parser.add_subparsers(title="Commands")

touch_subparser = subparsers.add_parser("touch", help="Create/initialize an empty wbtn file")
touch_subparser.add_argument("path", help="Path for the wbtn file to create")
touch_subparser.add_argument("-f", "--force", action="store_true", help="Overwrite existing file if exists")
touch_subparser.add_argument("--journal-mode", choices=JOURNAL_MODES, help="Set journal mode for the file")
touch_subparser.add_argument("--bypass-integrity-check", action="store_true", help="Bypass all of integrity check and overwrite values to current one")
touch_subparser.set_defaults(subparser_name="touch")

# info_subparser = subparsers.add_parser("info", help="Extract information from wbtn file; read only.")
# info_subparser.set_defaults(subparser_name="info")


def _touch_db(args: argparse.Namespace):
    path = Path(args.path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    settings = ConnectionSettings(
        clear_existing_db=args.force,
        journal_mode=args.journal_mode,
        bypass_integrity_check=args.bypass_integrity_check,
    )

    with Webtoon(path, connection_settings=settings):
        pass


def _main(argv: list[str] | None = None) -> None:
    args = parser.parse_args(argv)
    match args.subparser_name:
        case "touch":
            _touch_db(args)
        case None:
            parser.print_help()
        case other:
            raise ValueError(f"Unknown subparser: {other}")


def main(argv: list[str] | None = None) -> int:
    try:
        _main(argv)
    except Exception as exc:  # pragma: no cover
        reason = str(exc)
        print(f"{type(exc).__name__}{': ' if reason else ''}{reason}", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(0)
