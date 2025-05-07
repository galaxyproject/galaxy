import argparse
import functools
import os
import shutil
import sys


DESCRIPTION = """Install Galaxy web client from package path.

This utility installs the Galaxy web client from its Python package location to
another location, typically in order to be served by a proxy server in
production Galaxy installations.

The --mode option specifies how the web client is installed:

    relative (default):
        Create a symlink at DEST with a relative path target to the Galaxy web
        client's package directory

    absolute:
        Create a symlink at DEST with an absolute path target to the Galaxy web
        client's package directory

    copy:
        Copy the Galaxy web client to DEST
"""

CLIENT = os.path.join(os.path.dirname(__file__))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)

    dist = os.path.join(CLIENT, "dist")
    assert os.path.exists(dist), f"ERROR: Cannot find web client at expected path: {dist}"
    if args.mode in ("absolute", "relative"):
        _symlink(args.dest, args.mode == "absolute", args.force_overwrite)
    elif args.mode == "copy":
        _copy(args.dest, args.force_overwrite)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["relative", "absolute", "copy"], default="relative", help="Install mode")
    parser.add_argument(
        "--force-overwrite", action="store_true", default=False, help="Force overwrite DEST if it exists"
    )
    parser.add_argument("dest", metavar="DEST", nargs="?", default="client", help="Destination path")

    return parser


def _symlink(dest, absolute, force):
    if absolute:
        target = os.path.abspath(CLIENT)
    else:
        target = os.path.relpath(CLIENT, start=dest)
    _try(functools.partial(os.symlink, target, dest), dest, force)


def _copy(dest, force):
    _try(functools.partial(shutil.copytree, CLIENT, dest, dirs_exist_ok=False), dest, force)


def _try(f, dest, force):
    try:
        f()
    except FileExistsError:
        if not force:
            print(f"ERROR: File exists, use --force-overwrite to overwrite: {dest}")
            sys.exit(1)
        if os.path.isdir(dest) and not os.path.islink(dest):
            shutil.rmtree(dest)
        else:
            os.unlink(dest)
        f()


if __name__ == "__main__":
    main()
