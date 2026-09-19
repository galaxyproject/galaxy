import glob
import os
import shutil

GXY_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))


def stage_static(f):
    src = os.path.join(GXY_ROOT, "config/plugins", f)
    dest = os.path.join(GXY_ROOT, "static/plugins", f)
    dest_parent = os.path.abspath(os.path.join(dest, os.pardir))
    if os.path.lexists(dest):
        # We have to clear out the old staged or linked static to relink.
        if os.path.islink(dest):
            os.remove(dest)
        else:
            shutil.rmtree(dest)
    elif not os.path.exists(dest_parent):
        os.makedirs(dest_parent)
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dest)
        else:
            shutil.copy(src, dest)
    except Exception:
        print(f"Error copying '{src}' to '{dest}'")
        raise


if __name__ == "__main__":
    # This is not awesome, but it's temporary, and it supports two-tier plugin static.
    for f in glob.glob(os.path.join(GXY_ROOT, "config/plugins/*/*/static")) + glob.glob(
        os.path.join(GXY_ROOT, "config/plugins/*/*/*/static")
    ):
        f = os.path.relpath(f, os.path.join(GXY_ROOT, "config/plugins"))
        stage_static(f)
