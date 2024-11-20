import os
import zlib
from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Set,
)
from urllib.parse import quote

import zipstream

from galaxy.util import to_content_disposition
from .path import safe_walk

CRC32_MIN = 1444
CRC32_MAX = 1459


class ZipstreamWrapper:
    def __init__(
        self, archive_name: Optional[str] = None, upstream_mod_zip: bool = False, upstream_gzip: bool = False
    ) -> None:
        self.upstream_mod_zip = upstream_mod_zip
        self.archive_name = archive_name
        if not self.upstream_mod_zip:
            self.archive = zipstream.ZipFile(
                allowZip64=True, compression=zipstream.ZIP_STORED if upstream_gzip else zipstream.ZIP_DEFLATED
            )
        self.files: List[str] = []
        self.directories: Set[str] = set()
        self.size = 0

    def response(self) -> Iterator[bytes]:
        if self.upstream_mod_zip:
            dir_lines = [f"0 0 @directory {directory}" for directory in self.directories]
            yield "\n".join(dir_lines + self.files).encode()
        else:
            yield from iter(self.archive)

    def get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.archive_name:
            headers["Content-Disposition"] = to_content_disposition(f"{self.archive_name}.zip")
        if self.upstream_mod_zip:
            headers["X-Archive-Files"] = "zip"
        else:
            headers["Content-Type"] = "application/x-zip-compressed"
        return headers

    def add_path(self, path: str, archive_name: str) -> None:
        size = int(os.stat(path).st_size)
        if self.upstream_mod_zip:
            # calculating crc32 would defeat the point of using mod-zip, but if we ever calculate hashsums we should consider this
            crc32 = "-"
            # We do have to calculate the crc32 for files that are between 1444 and 1459 bytes in size, xref: https://github.com/evanmiller/mod_zip/issues/44#issuecomment-656660686
            # Oddly that seems to be only true for usegalaxy.org (nginx version 1.12.2), and works fine locally (nginx 1.19.10).
            # May have been fixed in nginx 1.17.0
            if CRC32_MIN <= os.path.getsize(path) <= CRC32_MAX:
                with open(path, "rb") as contents:
                    crc32 = hex(zlib.crc32(contents.read()))[2:]
            line = f"{crc32} {size} {quote(path)} {archive_name}"
            head, tail = os.path.split(archive_name)
            if head:
                self.directories.add(head)
            self.files.append(line)
        else:
            self.size += size
            self.archive.write(path, archive_name)

    def write(self, path: str, archive_name: Optional[str] = None) -> None:
        if os.path.isdir(path):
            pardir = os.path.join(path, os.pardir)
            for root, directories, files in safe_walk(path):
                for directory in directories:
                    dir_path = os.path.join(root, directory)
                    self.add_path(dir_path, os.path.relpath(dir_path, pardir))
                for file in files:
                    file_path = os.path.join(root, file)
                    self.add_path(file_path, os.path.relpath(file_path, pardir))
        else:
            self.add_path(path, archive_name or os.path.basename(path))
