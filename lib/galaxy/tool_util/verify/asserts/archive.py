import io
import re
import tarfile
import tempfile
import zipfile
from typing import Optional

from galaxy.util import asbool
from ._util import _assert_presence_number


def _extract_from_tar(bytes, fn):
    with io.BytesIO(bytes) as temp:
        with tarfile.open(fileobj=temp, mode="r") as tar_temp:
            ti = tar_temp.getmember(fn)
            # zip treats directories like empty files.
            # so make this consistent for tar
            if ti.isdir():
                return ""
            tar_file = tar_temp.extractfile(fn)
            assert tar_file is not None
            with tar_file as member_fh:
                return member_fh.read()


def _list_from_tar(bytes, path):
    lst = list()
    with io.BytesIO(bytes) as temp:
        with tarfile.open(fileobj=temp, mode="r") as tar_temp:
            for fn in tar_temp.getnames():
                if not re.match(path, fn):
                    continue
                lst.append(fn)
    return sorted(lst)


def _extract_from_zip(bytes, fn):
    with io.BytesIO(bytes) as temp:
        with zipfile.ZipFile(temp, mode="r") as zip_temp:
            with zip_temp.open(fn) as member_fh:
                return member_fh.read()


def _list_from_zip(bytes, path):
    lst = list()
    with io.BytesIO(bytes) as temp:
        with zipfile.ZipFile(temp, mode="r") as zip_temp:
            for fn in zip_temp.namelist():
                if not re.match(path, fn):
                    continue
                lst.append(fn)
    return sorted(lst)


def assert_has_archive_member(
    output_bytes,
    path,
    verify_assertions_function,
    children,
    all="false",
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """Recursively checks the specified children assertions against the text of
    the first element matching the specified path found within the archive.
    Currently supported formats: .zip, .tar, .tar.gz."""
    all = asbool(all)
    extract_foo = None
    # from python 3.9 is_tarfile supports file like objects then we do not need
    # the tempfile detour but can use io.BytesIO(output_bytes)
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(output_bytes)
        tmp.flush()
        if zipfile.is_zipfile(tmp.name):
            extract_foo = _extract_from_zip
            list_foo = _list_from_zip
        elif tarfile.is_tarfile(tmp.name):
            extract_foo = _extract_from_tar
            list_foo = _list_from_tar
    assert extract_foo is not None, f"Expected path '{path}' to be an archive"

    # get list of matching file names in archive and check against n, delta,
    # min, max (slightly abusing the output and text as well as the function
    # parameters)
    fns = list_foo(output_bytes, path)
    _assert_presence_number(
        None,
        path,
        n,
        delta,
        min,
        max,
        negate,
        lambda o, t: len(fns) > 0,
        lambda o, t: len(fns),
        "{expected} path '{text}' in archive",
        "{expected} {n}+-{delta} matches for path '{text}' in archive",
        "{expected} that the number of matches for path '{text}' in archive is in [{min}:{max}]",
    )

    # check sub-assertions on members matching path
    for fn in fns:
        contents = extract_foo(output_bytes, fn)
        try:
            verify_assertions_function(contents, children)
        except AssertionError as e:
            raise AssertionError(f"Archive member '{path}': {str(e)}")
        if not all:
            break
