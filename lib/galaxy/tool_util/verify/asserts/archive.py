import io
import re
import tarfile
import tempfile
import zipfile

from galaxy.util import asbool
from ._types import (
    Annotated,
    AssertionParameter,
    ChildAssertions,
    Delta,
    Max,
    Min,
    N,
    Negate,
    NEGATE_DEFAULT,
    OutputBytes,
    VerifyAssertionsFunction,
    XmlBool,
)
from ._util import _assert_presence_number


def _extract_from_tar(output_bytes, fn):
    with io.BytesIO(output_bytes) as temp:
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


def _list_from_tar(output_bytes, path):
    lst = []
    with io.BytesIO(output_bytes) as temp:
        with tarfile.open(fileobj=temp, mode="r") as tar_temp:
            for fn in tar_temp.getnames():
                if not re.match(path, fn):
                    continue
                lst.append(fn)
    return sorted(lst)


def _extract_from_zip(output_bytes, fn):
    with io.BytesIO(output_bytes) as temp:
        with zipfile.ZipFile(temp, mode="r") as zip_temp:
            with zip_temp.open(fn) as member_fh:
                return member_fh.read()


def _list_from_zip(output_bytes, path):
    lst = []
    with io.BytesIO(output_bytes) as temp:
        with zipfile.ZipFile(temp, mode="r") as zip_temp:
            for fn in zip_temp.namelist():
                if not re.match(path, fn):
                    continue
                lst.append(fn)
    return sorted(lst)


Path = Annotated[str, AssertionParameter("The regular expression specifying the archive member.")]
All = Annotated[
    XmlBool,
    AssertionParameter(
        "Check the sub-assertions for all paths matching the path. Default: false, i.e. only the first",
        xml_type="PermissiveBoolean",
    ),
]


def assert_has_archive_member(
    output_bytes: OutputBytes,
    path: Path,
    verify_assertions_function: VerifyAssertionsFunction,
    children: ChildAssertions = None,
    all: All = False,
    n: N = None,
    delta: Delta = 0,
    min: Min = None,
    max: Max = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """This tag allows to check if ``path`` is contained in a compressed file.

    The path is a regular expression that is matched against the full paths of the objects in
    the compressed file (remember that "matching" means it is checked if a prefix of
    the full path of an archive member is described by the regular expression).
    Valid archive formats include ``.zip``, ``.tar``, and ``.tar.gz``. Note that
    depending on the archive creation method:

    - full paths of the members may be prefixed with ``./``
    - directories may be treated as empty files

    ```xml
    <has_archive_member path="./path/to/my-file.txt"/>
    ```

    With ``n`` and ``delta`` (or ``min`` and ``max``) assertions on the number of
    archive members matching ``path`` can be expressed. The following could be used,
    e.g., to assert an archive containing n&plusmn;1 elements out of which at least
    4 need to have a ``txt`` extension.

    ```xml
    <has_archive_member path=".*" n="10" delta="1"/>
    <has_archive_member path=".*\\.txt" min="4"/>
    ```

    In addition the tag can contain additional assertions as child elements about
    the first member in the archive matching the regular expression ``path``. For
    instance

    ```xml
    <has_archive_member path=".*/my-file.txt">
      <not_has_text text="EDK72998.1"/>
    </has_archive_member>
    ```

    If the ``all`` attribute is set to ``true`` then all archive members are subject
    to the assertions. Note that, archive members matching the ``path`` are sorted
    alphabetically.

    The ``negate`` attribute of the ``has_archive_member`` assertion only affects
    the asserts on the presence and number of matching archive members, but not any
    sub-assertions (which can offer the ``negate`` attribute on their own).  The
    check if the file is an archive at all, which is also done by the function, is
    not affected."""
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
