import os
from urllib.parse import quote

import zipstream

from .path import safe_walk


class ZipstreamWrapper:

    def __init__(self, archive_name=None, upstream_mod_zip=False, upstream_gzip=False):
        self.upstream_mod_zip = upstream_mod_zip
        self.archive_name = archive_name
        if not self.upstream_mod_zip:
            self.archive = zipstream.ZipFile(allowZip64=True, compression=zipstream.ZIP_STORED if upstream_gzip else zipstream.ZIP_DEFLATED)
        self.files = []
        self.size = 0

    def response(self):
        if self.upstream_mod_zip:
            yield "\n".join(self.files).encode()
        else:
            yield iter(self.archive)

    def get_headers(self):
        headers = {}
        if self.archive_name:
            headers['Content-Disposition'] = f'attachment; filename="{self.archive_name}.zip"'
        if self.upstream_mod_zip:
            headers['X-Archive-Files'] = 'zip'
        else:
            headers['Content-Type'] = 'application/x-zip-compressed'
        return headers

    def add_path(self, path, archive_name):
        size = int(os.stat(path).st_size)
        if self.upstream_mod_zip:
            # calculating crc32 would defeat the point of using mod-zip, but if we ever calculate hashsums we should consider this
            crc32 = "-"
            line = f"{crc32} {size} {quote(path)} {archive_name}"
            self.files.append(line)
        else:
            self.size += size
            self.archive.write(path, archive_name)

    def write(self, path, archive_name=None):
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
