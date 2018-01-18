import gzip
import io
import zipfile

from .checkers import (
    bz2,
    is_bz2,
    is_gzip
)


def get_fileobj(filename, mode="r", compressed_formats=None):
    """
    Returns a fileobj. If the file is compressed, return an appropriate file
    reader. In text mode, always use 'utf-8' encoding.

    :param filename: path to file that should be opened
    :param mode: mode to pass to opener
    :param compressed_formats: list of allowed compressed file formats among
      'bz2', 'gzip' and 'zip'. If left to None, all 3 formats are allowed
    """
    if compressed_formats is None:
        compressed_formats = ['bz2', 'gzip', 'zip']
    # Remove 't' from mode, which may cause an error for compressed files
    mode = mode.replace('t', '')
    # the various compression readers don't support 'U' mode,
    # so we open in 'r'.
    if mode == 'U':
        cmode = 'r'
    else:
        cmode = mode
    if 'gzip' in compressed_formats and is_gzip(filename):
        fh = gzip.GzipFile(filename, cmode)
    elif 'bz2' in compressed_formats and is_bz2(filename):
        fh = bz2.BZ2File(filename, cmode)
    elif 'zip' in compressed_formats and zipfile.is_zipfile(filename):
        # Return fileobj for the first file in a zip file.
        with zipfile.ZipFile(filename, cmode) as zh:
            fh = zh.open(zh.namelist()[0], cmode)
    elif 'b' in mode:
        return open(filename, mode)
    else:
        return io.open(filename, mode, encoding='utf-8')
    if 'b' not in mode:
        return io.TextIOWrapper(fh, encoding='utf-8')
    else:
        return fh
