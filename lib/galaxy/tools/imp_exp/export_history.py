#!/usr/bin/env python
"""
Export a history to an archive file using attribute files.

usage: %prog history_attrs dataset_attrs job_attrs out_file
    -G, --gzip: gzip archive file
"""

import json
import optparse
import os
import shutil
import sys

from galaxy.files import ConfiguredFileSources
from galaxy.model.store import tar_export_directory
from galaxy.util import unicodify


def create_archive(export_directory, out_file, gzip=False):
    """Create archive from the given attribute/metadata files and save it to out_file."""
    try:
        tar_export_directory(export_directory, out_file, gzip)
        # Status.
        print("Created history archive.")
        return 0
    except Exception as e:
        print(f"Error creating history archive: {unicodify(e)}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(export_directory, ignore_errors=True)


def main(argv=None):
    # Parse command line.
    parser = optparse.OptionParser()
    parser.add_option("-G", "--gzip", dest="gzip", action="store_true", help="Compress archive using gzip.")
    parser.add_option(
        "--galaxy-version", dest="galaxy_version", help="Galaxy version that initiated the command.", default=None
    )
    parser.add_option("--file-sources", type=str, help="file sources json")
    (options, args) = parser.parse_args(argv)

    gzip = bool(options.gzip)
    assert len(args) >= 2
    temp_directory = args[0]
    out_arg = args[1]

    destination_uri = None
    if "://" in out_arg:
        # writing to a file source instead of a dataset path.
        destination_uri = out_arg
        out_file = "./temp_out_archive"
    else:
        out_file = out_arg
    # Create archive.
    exit = create_archive(temp_directory, out_file, gzip=gzip)
    if destination_uri is not None and exit == 0:
        actual_uri = _write_to_destination(options.file_sources, os.path.abspath(out_file), destination_uri)
        if destination_uri != actual_uri:
            print(f"Saved history archive to {actual_uri}.")
    return exit


def _write_to_destination(file_sources_path: str, out_file: str, destination_uri: str) -> str:
    file_sources = get_file_sources(file_sources_path)
    file_source_path = file_sources.get_file_source_path(destination_uri)
    file_source = file_source_path.file_source
    assert os.path.exists(out_file)
    return f"{file_source.get_scheme()}://{file_source.get_prefix()}" + file_source.write_from(
        file_source_path.path, out_file
    )


def get_file_sources(file_sources_path: str) -> ConfiguredFileSources:
    assert os.path.exists(file_sources_path), f"file sources path [{file_sources_path}] does not exist"
    with open(file_sources_path) as f:
        file_sources_as_dict = json.load(f)
    file_sources = ConfiguredFileSources.from_dict(file_sources_as_dict)
    return file_sources


if __name__ == "__main__":
    main()
