import bz2
import gzip
import zipfile

from .checkers import (
    is_bz2,
    is_gzip
)


def get_fileobj(filename, mode="r", gzip_only=False, bz2_only=False, zip_only=False):
    """
    Returns a fileobj. If the file is compressed, return appropriate file reader.

    :param filename: path to file that should be opened
    :param mode: mode to pass to opener
    :param gzip_only: only open file if file is gzip compressed or not compressed
    :param bz2_only: only open file if file is bz2 compressed or not compressed
    :param zip_only: only open file if file is zip compressed or not compressed
    """
    # the various compression readers don't support 'U' mode,
    # so we open in 'r'.
    if mode == 'U':
        cmode = 'r'
    else:
        cmode = mode
    if not bz2_only and not zip_only and is_gzip(filename):
        return gzip.GzipFile(filename, cmode)
    if not gzip_only and not zip_only and is_bz2(filename):
        return bz2.BZ2File(filename, cmode)
    if not bz2_only and not gzip_only and zipfile.is_zipfile(filename):
        # Return fileobj for the first file in a zip file.
        with zipfile.ZipFile(filename, cmode) as zh:
            return zh.open(zh.namelist()[0], cmode)
    return open(filename, mode)
