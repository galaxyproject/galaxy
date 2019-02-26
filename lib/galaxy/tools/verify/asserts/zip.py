import io
import re
import zipfile


def assert_has_archive_member(output_bytes, path, verify_assertions_function, children):
    """ Recursively checks the specified assertions against the text of
    the first element matching the specified path found within the zip archive."""
    output_temp = io.BytesIO(output_bytes)
    with zipfile.ZipFile(output_temp, 'r') as zip_temp:
        for fn in zip_temp.namelist():
            if re.match(path, fn):
                path = fn
                break  # Will only match on first hit, probably fine for now

        with zip_temp.open(path) as file_temp:
            verify_assertions_function(file_temp.read(), children)
