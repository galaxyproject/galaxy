from __future__ import absolute_import

import gzip
import io
import logging
import os
import tarfile
import zipfile

from galaxy.util.path import safe_relpath
from .checkers import (
    bz2,
    is_bz2,
    is_gzip
)

log = logging.getLogger(__name__)


def get_fileobj(filename, mode="r", compressed_formats=None):
    """
    Returns a fileobj. If the file is compressed, return an appropriate file
    reader. In text mode, always use 'utf-8' encoding.

    :param filename: path to file that should be opened
    :param mode: mode to pass to opener
    :param compressed_formats: list of allowed compressed file formats among
      'bz2', 'gzip' and 'zip'. If left to None, all 3 formats are allowed
    """
    return get_fileobj_raw(filename, mode, compressed_formats)[1]


def get_fileobj_raw(filename, mode="r", compressed_formats=None):
    if compressed_formats is None:
        compressed_formats = ['bz2', 'gzip', 'zip']
    # Remove 't' from mode, which may cause an error for compressed files
    mode = mode.replace('t', '')
    # 'U' mode is deprecated, we open in 'r'.
    if mode == 'U':
        mode = 'r'
    compressed_format = None
    if 'gzip' in compressed_formats and is_gzip(filename):
        fh = gzip.GzipFile(filename, mode)
        compressed_format = 'gzip'
    elif 'bz2' in compressed_formats and is_bz2(filename):
        fh = bz2.BZ2File(filename, mode)
        compressed_format = 'bz2'
    elif 'zip' in compressed_formats and zipfile.is_zipfile(filename):
        # Return fileobj for the first file in a zip file.
        with zipfile.ZipFile(filename, mode) as zh:
            fh = zh.open(zh.namelist()[0], mode)
        compressed_format = 'zip'
    elif 'b' in mode:
        return compressed_format, open(filename, mode)
    else:
        return compressed_format, io.open(filename, mode, encoding='utf-8')
    if 'b' not in mode:
        return compressed_format, io.TextIOWrapper(fh, encoding='utf-8')
    else:
        return compressed_format, fh


class CompressedFile(object):

    @staticmethod
    def can_decompress(file_path):
        return tarfile.is_tarfile(file_path) or zipfile.is_zipfile(file_path)

    def __init__(self, file_path, mode='r'):
        if tarfile.is_tarfile(file_path):
            self.file_type = 'tar'
        elif zipfile.is_zipfile(file_path) and not file_path.endswith('.jar'):
            self.file_type = 'zip'
        self.file_name = os.path.splitext(os.path.basename(file_path))[0]
        if self.file_name.endswith('.tar'):
            self.file_name = os.path.splitext(self.file_name)[0]
        self.type = self.file_type
        method = 'open_%s' % self.file_type
        if hasattr(self, method):
            self.archive = getattr(self, method)(file_path, mode)
        else:
            raise NameError('File type %s specified, no open method found.' % self.file_type)

    def extract(self, path):
        '''Determine the path to which the archive should be extracted.'''
        contents = self.getmembers()
        extraction_path = path
        common_prefix = ''
        if len(contents) == 1:
            # The archive contains a single file, return the extraction path.
            if self.isfile(contents[0]):
                extraction_path = os.path.join(path, self.file_name)
                if not os.path.exists(extraction_path):
                    os.makedirs(extraction_path)
                self.archive.extractall(extraction_path, members=self.safemembers())
        else:
            # Get the common prefix for all the files in the archive. If the common prefix ends with a slash,
            # or self.isdir() returns True, the archive contains a single directory with the desired contents.
            # Otherwise, it contains multiple files and/or directories at the root of the archive.
            common_prefix = os.path.commonprefix([self.getname(item) for item in contents])
            if len(common_prefix) >= 1 and not common_prefix.endswith(os.sep) and self.isdir(self.getmember(common_prefix)):
                common_prefix += os.sep
            if not common_prefix.endswith(os.sep):
                common_prefix = ''
                extraction_path = os.path.join(path, self.file_name)
                if not os.path.exists(extraction_path):
                    os.makedirs(extraction_path)
            self.archive.extractall(extraction_path, members=self.safemembers())
        # Since .zip files store unix permissions separately, we need to iterate through the zip file
        # and set permissions on extracted members.
        if self.file_type == 'zip':
            for zipped_file in contents:
                filename = self.getname(zipped_file)
                absolute_filepath = os.path.join(extraction_path, filename)
                external_attributes = self.archive.getinfo(filename).external_attr
                # The 2 least significant bytes are irrelevant, the next two contain unix permissions.
                unix_permissions = external_attributes >> 16
                if unix_permissions != 0:
                    if os.path.exists(absolute_filepath):
                        os.chmod(absolute_filepath, unix_permissions)
                    else:
                        log.warning("Unable to change permission on extracted file '%s' as it does not exist" % absolute_filepath)
        return os.path.abspath(os.path.join(extraction_path, common_prefix))

    def safemembers(self):
        members = self.archive
        if self.file_type == "tar":
            for finfo in members:
                if not safe_relpath(finfo.name):
                    raise Exception(finfo.name + " is blocked (illegal path).")
                elif (finfo.issym() or finfo.islnk()) and not safe_relpath(finfo.linkname):
                    raise Exception(finfo.name + " is blocked.")
                else:
                    yield finfo
        elif self.file_type == "zip":
            for name in members.namelist():
                if not safe_relpath(name):
                    raise Exception(name + " is blocked (illegal path).")
                else:
                    yield name

    def getmembers_tar(self):
        return self.archive.getmembers()

    def getmembers_zip(self):
        return self.archive.infolist()

    def getname_tar(self, item):
        return item.name

    def getname_zip(self, item):
        return item.filename

    def getmember(self, name):
        for member in self.getmembers():
            if self.getname(member) == name:
                return member

    def getmembers(self):
        return getattr(self, 'getmembers_%s' % self.type)()

    def getname(self, member):
        return getattr(self, 'getname_%s' % self.type)(member)

    def isdir(self, member):
        return getattr(self, 'isdir_%s' % self.type)(member)

    def isdir_tar(self, member):
        return member.isdir()

    def isdir_zip(self, member):
        if member.filename.endswith(os.sep):
            return True
        return False

    def isfile(self, member):
        if not self.isdir(member):
            return True
        return False

    def open_tar(self, filepath, mode):
        return tarfile.open(filepath, mode, errorlevel=0)

    def open_zip(self, filepath, mode):
        return zipfile.ZipFile(filepath, mode)

    def zipfile_ok(self, path_to_archive):
        """
        This function is a bit pedantic and not functionally necessary.  It checks whether there is
        no file pointing outside of the extraction, because ZipFile.extractall() has some potential
        security holes.  See python zipfile documentation for more details.
        """
        basename = os.path.realpath(os.path.dirname(path_to_archive))
        zip_archive = zipfile.ZipFile(path_to_archive)
        for member in zip_archive.namelist():
            member_path = os.path.realpath(os.path.join(basename, member))
            if not member_path.startswith(basename):
                return False
        return True
