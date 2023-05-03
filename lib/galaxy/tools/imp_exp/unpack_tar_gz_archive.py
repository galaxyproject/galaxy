#!/usr/bin/env python
"""
Unpack a tar, tar.gz or zip archive into a directory.

usage: %prog archive_source dest_dir
    --[url|file] source type, either a URL or a file.
"""

import json
import math
import optparse
import os
import tarfile
import zipfile
from base64 import b64decode

from galaxy.files import ConfiguredFileSources
from galaxy.files.uris import stream_url_to_file

# Set max size of archive/file that will be handled to be 100 GB. This is
# arbitrary and should be adjusted as needed.
MAX_SIZE = 100 * math.pow(2, 30)


def get_file_sources(file_sources_path) -> ConfiguredFileSources:
    assert os.path.exists(file_sources_path), f"file sources path [{file_sources_path}] does not exist"

    with open(file_sources_path) as f:
        file_sources_as_dict = json.load(f)
    file_sources = ConfiguredFileSources.from_dict(file_sources_as_dict)
    return file_sources


def check_archive(archive_file, dest_dir):
    """
    Ensure that a tar archive has no absolute paths or relative paths outside
    the archive.
    """
    if zipfile.is_zipfile(archive_file):
        with zipfile.ZipFile(archive_file, "r") as archive_fp:
            for arc_path in archive_fp.namelist():
                assert not os.path.isabs(arc_path), f"Archive member has absolute path: {arc_path}"
                assert not os.path.relpath(arc_path).startswith(
                    ".."
                ), f"Archive member would extract outside target directory: {arc_path}"
    else:
        with tarfile.open(archive_file, mode="r") as archive_fp:
            for arc_path in archive_fp.getnames():
                assert os.path.normpath(os.path.join(dest_dir, arc_path)).startswith(
                    dest_dir.rstrip(os.sep) + os.sep
                ), f"Archive member would extract outside target directory: {arc_path}"
    return True


def unpack_archive(archive_file, dest_dir):
    """
    Unpack a tar and/or gzipped archive into a destination directory.
    """
    if zipfile.is_zipfile(archive_file):
        with zipfile.ZipFile(archive_file, "r") as zip_archive:
            zip_archive.extractall(path=dest_dir)
    else:
        with tarfile.open(archive_file, mode="r") as archive_fp:
            archive_fp.extraction_filter = getattr(tarfile, "data_filter", (lambda member, path: member))
            archive_fp.extractall(path=dest_dir)


def main(options, args):
    is_url = bool(options.is_url)
    is_file = bool(options.is_file)
    archive_source, dest_dir = args

    if options.is_b64encoded:
        archive_source = b64decode(archive_source).decode("utf-8")
        dest_dir = b64decode(dest_dir).decode("utf-8")

    # Get archive from URL.
    if is_url:
        archive_file = stream_url_to_file(
            archive_source, file_sources=get_file_sources(options.file_sources), prefix="gx_history_archive"
        )
    elif is_file:
        archive_file = archive_source

    # Unpack archive.
    check_archive(archive_file, dest_dir)
    unpack_archive(archive_file, dest_dir)


if __name__ == "__main__":
    # Parse command line.
    parser = optparse.OptionParser()
    parser.add_option("-U", "--url", dest="is_url", action="store_true", help="Source is a URL.")
    parser.add_option("-F", "--file", dest="is_file", action="store_true", help="Source is a file.")
    parser.add_option(
        "-e",
        "--encoded",
        dest="is_b64encoded",
        action="store_true",
        default=False,
        help="Source and destination dir values are base64 encoded.",
    )
    parser.add_option("--file-sources", type=str, help="file sources json")
    (options, args) = parser.parse_args()
    main(options, args)
