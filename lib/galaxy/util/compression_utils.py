import bz2
import gzip
import io
import logging
import os
import tarfile
import zipfile
from typing import (
    Any,
    cast,
    Generator,
    IO,
    Iterable,
    List,
    Optional,
    overload,
    Tuple,
    Union,
)

from typing_extensions import Literal

from galaxy.util.path import safe_relpath
from .checkers import (
    is_bz2,
    is_gzip,
)

log = logging.getLogger(__name__)

FileObjTypeStr = Union[IO[str], io.TextIOWrapper]
FileObjTypeBytes = Union[gzip.GzipFile, bz2.BZ2File, IO[bytes]]
FileObjType = Union[FileObjTypeStr, FileObjTypeBytes]


@overload
def get_fileobj(filename: str, mode: Literal["r"], compressed_formats: Optional[List[str]] = None) -> FileObjTypeStr:
    ...


@overload
def get_fileobj(filename: str, mode: Literal["rb"], compressed_formats: Optional[List[str]] = None) -> FileObjTypeBytes:
    ...


@overload
def get_fileobj(filename: str) -> FileObjTypeStr:
    ...


@overload
def get_fileobj(filename: str, mode: str = "r", compressed_formats: Optional[List[str]] = None) -> FileObjType:
    ...


def get_fileobj(filename: str, mode: str = "r", compressed_formats: Optional[List[str]] = None) -> FileObjType:
    """
    Returns a fileobj. If the file is compressed, return an appropriate file
    reader. In text mode, always use 'utf-8' encoding.

    :param filename: path to file that should be opened
    :param mode: mode to pass to opener
    :param compressed_formats: list of allowed compressed file formats among
      'bz2', 'gzip' and 'zip'. If left to None, all 3 formats are allowed
    """
    return get_fileobj_raw(filename, mode, compressed_formats)[1]


@overload
def get_fileobj_raw(
    filename: str, mode: Literal["r"], compressed_formats: Optional[List[str]] = None
) -> Tuple[Optional[str], FileObjTypeStr]:
    ...


@overload
def get_fileobj_raw(
    filename: str, mode: Literal["rb"], compressed_formats: Optional[List[str]] = None
) -> Tuple[Optional[str], FileObjTypeBytes]:
    ...


@overload
def get_fileobj_raw(filename: str) -> Tuple[Optional[str], FileObjTypeStr]:
    ...


@overload
def get_fileobj_raw(
    filename: str, mode: str = "r", compressed_formats: Optional[List[str]] = None
) -> Tuple[Optional[str], FileObjType]:
    ...


def get_fileobj_raw(
    filename: str, mode: str = "r", compressed_formats: Optional[List[str]] = None
) -> Tuple[Optional[str], FileObjType]:
    if compressed_formats is None:
        compressed_formats = ["bz2", "gzip", "zip"]
    # Remove 't' from mode, which may cause an error for compressed files
    mode = mode.replace("t", "")
    # 'U' mode is deprecated, we open in 'r'.
    if mode == "U":
        mode = "r"
    compressed_format = None
    if "gzip" in compressed_formats and is_gzip(filename):
        fh: Union[gzip.GzipFile, bz2.BZ2File, IO[bytes]] = gzip.GzipFile(filename, mode)
        compressed_format = "gzip"
    elif "bz2" in compressed_formats and is_bz2(filename):
        mode = cast(Literal["a", "ab", "r", "rb", "w", "wb", "x", "xb"], mode)
        fh = bz2.BZ2File(filename, mode)
        compressed_format = "bz2"
    elif "zip" in compressed_formats and zipfile.is_zipfile(filename):
        # Return fileobj for the first file in a zip file.
        # 'b' is not allowed in the ZipFile mode argument
        # since it always opens files in binary mode.
        # For emulating text mode, we will be returning the binary fh in a
        # TextIOWrapper.
        zf_mode = cast(Literal["r", "w"], mode.replace("b", ""))
        with zipfile.ZipFile(filename, zf_mode) as zh:
            fh = zh.open(zh.namelist()[0], zf_mode)
        compressed_format = "zip"
    elif "b" in mode:
        return compressed_format, open(filename, mode)
    else:
        return compressed_format, open(filename, mode, encoding="utf-8")
    if "b" not in mode:
        return compressed_format, io.TextIOWrapper(cast(IO[bytes], fh), encoding="utf-8")
    else:
        return compressed_format, fh


def file_iter(fname: str, sep: Optional[Any] = None) -> Generator[Union[List[bytes], Any, List[str]], None, None]:
    """
    This generator iterates over a file and yields its lines
    splitted via the C{sep} parameter. Skips empty lines and lines starting with
    the C{#} character.

    >>> lines = [ line for line in file_iter(__file__) ]
    >>> len(lines) !=  0
    True
    """
    with get_fileobj(fname) as fh:
        for line in fh:
            if line and line[0] != "#":
                yield line.split(sep)


ArchiveMemberType = Union[tarfile.TarInfo, zipfile.ZipInfo]


class CompressedFile:

    archive: Union[tarfile.TarFile, zipfile.ZipFile]

    @staticmethod
    def can_decompress(file_path: str) -> bool:
        return tarfile.is_tarfile(file_path) or zipfile.is_zipfile(file_path)

    def __init__(self, file_path: str, mode: str = "r") -> None:
        if tarfile.is_tarfile(file_path):
            self.file_type = "tar"
        elif zipfile.is_zipfile(file_path) and not file_path.endswith(".jar"):
            self.file_type = "zip"
        self.file_name = os.path.splitext(os.path.basename(file_path))[0]
        if self.file_name.endswith(".tar"):
            self.file_name = os.path.splitext(self.file_name)[0]
        self.type = self.file_type
        method = f"open_{self.file_type}"
        if hasattr(self, method):
            self.archive = getattr(self, method)(file_path, mode)
        else:
            raise NameError(f"File type {self.file_type} specified, no open method found.")

    @property
    def common_prefix_dir(self) -> str:
        """
        Get the common prefix directory for all the files in the archive, if any.

        Returns '' if the archive contains multiple files and/or directories at
        the root of the archive.
        """
        contents = self.getmembers()
        common_prefix = ""
        if len(contents) > 1:
            common_prefix = os.path.commonprefix([self.getname(item) for item in contents])
            # If the common_prefix does not end with a slash, check that is a
            # directory and all other files are contained in it
            common_prefix_member = self.getmember(common_prefix)
            if (
                len(common_prefix) >= 1
                and not common_prefix.endswith(os.sep)
                and common_prefix_member
                and self.isdir(common_prefix_member)
                and all(self.getname(item).startswith(common_prefix + os.sep) for item in contents if self.isfile(item))
            ):
                common_prefix += os.sep
            if not common_prefix.endswith(os.sep):
                common_prefix = ""
        return common_prefix

    def extract(self, path: str) -> str:
        """Determine the path to which the archive should be extracted."""
        contents = self.getmembers()
        extraction_path = path
        common_prefix_dir = self.common_prefix_dir
        if len(contents) == 1:
            # The archive contains a single file, return the extraction path.
            if self.isfile(contents[0]):
                extraction_path = os.path.join(path, self.file_name)
                if not os.path.exists(extraction_path):
                    os.makedirs(extraction_path)
                if isinstance(self.archive, tarfile.TarFile):
                    members_t = cast(Iterable[tarfile.TarInfo], self.safemembers())
                    self.archive.extractall(extraction_path, members=members_t)
                else:
                    members_z = cast(Iterable[str], self.safemembers())
                    self.archive.extractall(extraction_path, members=members_z)
        else:
            if not common_prefix_dir:
                extraction_path = os.path.join(path, self.file_name)
                if not os.path.exists(extraction_path):
                    os.makedirs(extraction_path)
            if isinstance(self.archive, tarfile.TarFile):
                members_t = cast(Iterable[tarfile.TarInfo], self.safemembers())
                self.archive.extractall(extraction_path, members=members_t)
            else:
                members_z = cast(Iterable[str], self.safemembers())
                self.archive.extractall(extraction_path, members=members_z)
        # Since .zip files store unix permissions separately, we need to iterate through the zip file
        # and set permissions on extracted members.
        if self.file_type == "zip":
            assert isinstance(self.archive, zipfile.ZipFile)
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
                        log.warning(
                            f"Unable to change permission on extracted file '{absolute_filepath}' as it does not exist"
                        )
        return os.path.abspath(os.path.join(extraction_path, common_prefix_dir))

    def safemembers(self) -> Union[Iterable[tarfile.TarInfo], Iterable[str]]:
        members = self.archive
        common_prefix_dir = self.common_prefix_dir
        if self.file_type == "tar":
            assert isinstance(members, tarfile.TarFile)
            for finfo in members:
                if not safe_relpath(finfo.name):
                    raise Exception(f"Path '{finfo.name}' is blocked (illegal path).")
                if finfo.issym() or finfo.islnk():
                    link_target = os.path.join(os.path.dirname(finfo.name), finfo.linkname)
                    if not safe_relpath(link_target) or not os.path.normpath(link_target).startswith(common_prefix_dir):
                        raise Exception(f"Link '{finfo.name}' to '{finfo.linkname}' is blocked.")
                yield finfo
        elif self.file_type == "zip":
            assert isinstance(members, zipfile.ZipFile)
            for name in members.namelist():
                if not safe_relpath(name):
                    raise Exception(f"{name} is blocked (illegal path).")
                yield name

    def getmembers_tar(self) -> List[tarfile.TarInfo]:
        assert isinstance(self.archive, tarfile.TarFile)
        return self.archive.getmembers()

    def getmembers_zip(self) -> List[zipfile.ZipInfo]:
        assert isinstance(self.archive, zipfile.ZipFile)
        return self.archive.infolist()

    def getname_tar(self, item: tarfile.TarInfo) -> str:
        return item.name

    def getname_zip(self, item: zipfile.ZipInfo) -> str:
        return item.filename

    def getmember(self, name: str) -> Optional[ArchiveMemberType]:
        for member in self.getmembers():
            if self.getname(member) == name:
                return member
        return None

    def getmembers(self) -> List[ArchiveMemberType]:
        return cast(List[ArchiveMemberType], getattr(self, f"getmembers_{self.type}")())

    def getname(self, member: ArchiveMemberType) -> str:
        return cast(str, getattr(self, f"getname_{self.type}")(member))

    def isdir(self, member: ArchiveMemberType) -> bool:
        return cast(bool, getattr(self, f"isdir_{self.type}")(member))

    def isdir_tar(self, member: tarfile.TarInfo) -> bool:
        return member.isdir()

    def isdir_zip(self, member: zipfile.ZipInfo) -> bool:
        if member.filename.endswith(os.sep):
            return True
        return False

    def isfile(self, member: ArchiveMemberType) -> bool:
        if not self.isdir(member):
            return True
        return False

    def open_tar(self, filepath: str, mode: str) -> tarfile.TarFile:
        return tarfile.open(filepath, mode, errorlevel=0)

    def open_zip(self, filepath: str, mode: str) -> zipfile.ZipFile:
        mode = cast(Literal["a", "r", "w", "x"], mode)
        return zipfile.ZipFile(filepath, mode)

    def zipfile_ok(self, path_to_archive: str) -> bool:
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
