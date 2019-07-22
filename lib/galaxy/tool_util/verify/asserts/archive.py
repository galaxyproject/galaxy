import io
import re
import tarfile
import zipfile


def _extract_from_tar(tar_temp, path):
    for fn in tar_temp.getnames():
        if re.match(path, fn):
            # Will only match on first hit, probably fine for now
            return tar_temp.extractfile(fn)


def _extract_from_zip(zip_temp, path):
    for fn in zip_temp.namelist():
        if re.match(path, fn):
            # Will only match on first hit, probably fine for now
            return zip_temp.open(fn)


def assert_has_archive_member(output_bytes, path, verify_assertions_function, children):
    """ Recursively checks the specified children assertions against the text of
    the first element matching the specified path found within the archive.
    Currently supported formats: .zip, .tar, .tar.gz."""

    output_temp = io.BytesIO(output_bytes)
    try:  # tar / tar.gz
        temp = tarfile.open(fileobj=output_temp, mode='r')
        contents = _extract_from_tar(temp, path)
    except tarfile.TarError:  # zip
        temp = zipfile.ZipFile(output_temp, mode='r')
        contents = _extract_from_zip(temp, path)
    finally:
        verify_assertions_function(contents.read(), children)
        contents.close()
        temp.close()
    output_temp.close()
