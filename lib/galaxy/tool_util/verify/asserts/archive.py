import io
import os
import re
import tarfile
import tempfile
import zipfile


def _extract_from_tar(temp, path):
    with tarfile.open(fileobj=temp, mode='r') as tar_temp:
        for fn in tar_temp.getnames():
            if not re.match(path, fn):
                continue
            # if called on a dir zip.open returns a handle to an empty string
            # in contrast tar.extractfile returns None, the following
            # if makes the _extract... functions behave equally in this case
            if not tar_temp.getmember(fn).isfile():
                yield io.StringIO("")
            yield tar_temp.extractfile(fn)


def _extract_from_zip(temp, path):
    with zipfile.ZipFile(temp, mode='r') as zip_temp:
        for fn in zip_temp.namelist():
            if not re.match(path, fn):
                continue
            yield zip_temp.open(fn)


def assert_has_archive_member(output_bytes, path, verify_assertions_function, children, all=False):
    """ Recursively checks the specified children assertions against the text of
    the first element matching the specified path found within the archive.
    Currently supported formats: .zip, .tar, .tar.gz."""

    # from python 3.9 is_tarfile supports file like objects then we do not need
    # the tempfile detour but can use io.BytesIO(output_bytes)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmpname = tmp.name
        tmp.write(output_bytes)
    zipfoo = None
    if zipfile.is_zipfile(tmp.name):
        zipfoo = _extract_from_zip
    if tarfile.is_tarfile(tmp.name):
        zipfoo = _extract_from_tar
    os.remove(tmpname)
    assert zipfoo is not None, f"Expected path '{path}' to be an archive"

    with io.BytesIO(output_bytes) as output_temp:
        haspath = False
        for contents in zipfoo(output_temp, path):
            haspath = True
            verify_assertions_function(contents.read(), children)
            contents.close()
            if not all:
                break
        assert haspath, f"Expected path '{path}' in archive"