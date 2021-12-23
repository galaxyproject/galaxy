import io
import re
import tarfile
import zipfile


def _extract_from_tar(tar_temp, path):
    for fn in tar_temp.getnames():
        if not re.match(path, fn):
            continue
        # Will only match on first hit, probably fine for now
        # if called on a dir zip.open returns a handle to an empty string
        # in contrast tar.extractfile returns None, the following
        # if makes the _extract... functions behave equally in this case
        if not tar_temp.getmember(fn).isfile():
            return io.StringIO("")
        return tar_temp.extractfile(fn)


def _extract_from_zip(zip_temp, path):
    for fn in zip_temp.namelist():
        if not re.match(path, fn):
            continue
        return zip_temp.open(fn)


def assert_has_archive_member(output_bytes, path, verify_assertions_function, children):
    """ Recursively checks the specified children assertions against the text of
    the first element matching the specified path found within the archive.
    Currently supported formats: .zip, .tar, .tar.gz."""

    with io.BytesIO(output_bytes) as output_temp:
        try:  # tar / tar.gz
            temp = tarfile.open(fileobj=output_temp, mode='r')
            contents = _extract_from_tar(temp, path)
        except tarfile.TarError:  # zip
            try:
                temp = zipfile.ZipFile(output_temp, mode='r')
                contents = _extract_from_zip(temp, path)
            except zipfile.BadZipFile:
                raise AssertionError(f"Expected path '{path}' to be an archive")
        assert contents is not None, f"Expected path '{path}' in archive"
        verify_assertions_function(contents.read(), children)
        contents.close()
        temp.close()
