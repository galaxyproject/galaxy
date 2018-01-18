import gzip
import re
import sys
import zipfile

from six import StringIO

from galaxy import util
from galaxy.util.image_util import image_type

if sys.version_info < (3, 3):
    gzip.GzipFile.read1 = gzip.GzipFile.read  # workaround for https://bugs.python.org/issue12591
    try:
        import bz2file as bz2
    except ImportError:
        # If bz2file is unavailable, just fallback to not having pbzip2 support.
        import bz2
else:
    import bz2

HTML_CHECK_LINES = 100


def check_html(file_path, chunk=None):
    if chunk is None:
        temp = open(file_path, "U")
    elif hasattr(chunk, "splitlines"):
        temp = chunk.splitlines()
    else:
        temp = chunk
    regexp1 = re.compile("<A\s+[^>]*HREF[^>]+>", re.I)
    regexp2 = re.compile("<IFRAME[^>]*>", re.I)
    regexp3 = re.compile("<FRAMESET[^>]*>", re.I)
    regexp4 = re.compile("<META[\W][^>]*>", re.I)
    regexp5 = re.compile("<SCRIPT[^>]*>", re.I)
    lineno = 0
    # TODO: Potentially reading huge lines into string here, this should be
    # reworked.
    for line in temp:
        lineno += 1
        matches = regexp1.search(line) or regexp2.search(line) or regexp3.search(line) or regexp4.search(line) or regexp5.search(line)
        if matches:
            if chunk is None:
                temp.close()
            return True
        if HTML_CHECK_LINES and (lineno > HTML_CHECK_LINES):
            break
    if chunk is None:
        temp.close()
    return False


def check_binary(name, file_path=True):
    # Handles files if file_path is True or text if file_path is False
    is_binary = False
    if file_path:
        temp = open(name, "U")
    else:
        temp = StringIO(name)
    try:
        for char in temp.read(100):
            if util.is_binary(char):
                is_binary = True
                break
    finally:
        temp.close()
    return is_binary


def check_gzip(file_path, check_content=True):
    # This method returns a tuple of booleans representing ( is_gzipped, is_valid )
    # Make sure we have a gzipped file
    try:
        temp = open(file_path, "U")
        magic_check = temp.read(2)
        temp.close()
        if magic_check != util.gzip_magic:
            return (False, False)
    except Exception:
        return (False, False)
    # We support some binary data types, so check if the compressed binary file is valid
    # If the file is Bam, it should already have been detected as such, so we'll just check
    # for sff format.
    try:
        header = gzip.open(file_path).read(4)
        if header == b'.sff':
            return (True, True)
    except Exception:
        return(False, False)

    if not check_content:
        return (True, True)

    CHUNK_SIZE = 2 ** 15  # 32Kb
    gzipped_file = gzip.GzipFile(file_path, mode='rb')
    chunk = gzipped_file.read(CHUNK_SIZE)
    gzipped_file.close()
    # See if we have a compressed HTML file
    if check_html(file_path, chunk=chunk):
        return (True, False)
    return (True, True)


def check_bz2(file_path, check_content=True):
    try:
        temp = open(file_path, "U")
        magic_check = temp.read(3)
        temp.close()
        if magic_check != util.bz2_magic:
            return (False, False)
    except Exception:
        return(False, False)

    if not check_content:
        return (True, True)

    CHUNK_SIZE = 2 ** 15  # reKb
    bzipped_file = bz2.BZ2File(file_path, mode='rb')
    chunk = bzipped_file.read(CHUNK_SIZE)
    bzipped_file.close()
    # See if we have a compressed HTML file
    if check_html(file_path, chunk=chunk):
        return (True, False)
    return (True, True)


def check_zip(file_path):
    if zipfile.is_zipfile(file_path):
        return True
    return False


def is_bz2(file_path):
    is_bz2, is_valid = check_bz2(file_path, check_content=False)
    return is_bz2


def is_gzip(file_path):
    is_gzipped, is_valid = check_gzip(file_path, check_content=False)
    return is_gzipped


def check_image(file_path):
    """ Simple wrapper around image_type to yield a True/False verdict """
    if image_type(file_path):
        return True
    return False


__all__ = (
    'check_binary',
    'check_bz2',
    'check_gzip',
    'check_html',
    'check_image',
    'check_zip',
    'is_gzip',
    'is_bz2',
)
