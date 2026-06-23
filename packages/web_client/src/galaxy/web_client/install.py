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

TARGETS = {
    "dist": os.path.join(os.path.dirname(__file__), "dist"),
}

try:
    import galaxy.webapps.base

    STATIC = os.path.join(os.path.dirname(galaxy.webapps.base.__file__), "static")
    TARGETS.update({
        "style": os.path.join(STATIC, "style"),
        "favicon.ico": os.path.join(STATIC, "favicon.ico"),
        "favicon.svg": os.path.join(STATIC, "favicon.svg"),
        "robots.txt": os.path.join(STATIC, "robots.txt"),
        "welcome.sample.html": os.path.join(STATIC, "welcome.sample.html"),
    })
except ImportError:
    # Consider this a soft fail, this package depends on nothing but is probably installed with galaxy-web-apps
    pass


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)

    assert os.path.exists(TARGETS["dist"]), f"ERROR: Cannot find web client at expected path: {TARGETS['dist']}"

    _try(functools.partial(os.makedirs, args.dest), args.dest, args.force_overwrite, dir_ok=True)
    for dest, target in TARGETS.items():
        dest = os.path.join(args.dest, dest)
        if args.mode in ("absolute", "relative"):
            _symlink(dest, target, args.mode == "absolute", args.force_overwrite)
        elif args.mode == "copy":
            _copy(dest, target, args.force_overwrite)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["relative", "absolute", "copy"], default="relative", help="Install mode")
    parser.add_argument(
        "--force-overwrite", action="store_true", default=False, help="Force overwrite DEST if it exists"
    )
    parser.add_argument("dest", metavar="DEST", nargs="?", default="client", help="Destination path")

    return parser


def _symlink(dest, target, absolute, force):
    if absolute:
        target = os.path.abspath(target)
    else:
        target = os.path.relpath(target, start=os.path.dirname(dest))
    if _try(functools.partial(os.symlink, target, dest), dest, force, target=target):
        print(f"link: {dest} -> {target}")


def _copy(dest, target, force):
    if os.path.isdir(target):
        f = functools.partial(shutil.copytree, target, dest, dirs_exist_ok=False)
    else:
        f = functools.partial(_copy2, target, dest)
    if _try(f, dest, force):
        print(f"copy: {target} -> {dest}")


def _copy2(target, dest):
    if os.path.exists(dest):
        raise FileExistsError(dest)
    shutil.copy2(target, dest)


def _try(f, dest, force, target=None, dir_ok=False):
    try:
        f()
    except (FileExistsError, shutil.SameFileError):
        if dir_ok and os.path.isdir(dest) and not os.path.islink(dest):
            return True
        if target and os.path.islink(dest) and os.readlink(dest) == target:
            return True
        if not force:
            print(f"ERROR: File exists, use --force-overwrite to overwrite: {dest}")
            return False
        if os.path.isdir(dest) and not os.path.islink(dest):
            shutil.rmtree(dest)
        else:
            os.unlink(dest)
        f()
    return True


if __name__ == "__main__":
    main()
