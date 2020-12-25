#!/usr/bin/env python
"""
Export a history to an archive file using attribute files.

usage: %prog history_attrs dataset_attrs job_attrs out_file
    -G, --gzip: gzip archive file
"""

import optparse
import shutil
import sys

from galaxy.model.store import tar_export_directory
from galaxy.util import unicodify


def create_archive(export_directory, out_file, gzip=False):
    """Create archive from the given attribute/metadata files and save it to out_file."""
    try:
        tar_export_directory(export_directory, out_file, gzip)
        # Status.
        print('Created history archive.')
        return 0
    except Exception as e:
        print('Error creating history archive: %s' % unicodify(e), file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(export_directory, ignore_errors=True)


def main(argv=None):
    # Parse command line.
    parser = optparse.OptionParser()
    parser.add_option('-G', '--gzip', dest='gzip', action="store_true", help='Compress archive using gzip.')
    parser.add_option('--galaxy-version', dest='galaxy_version', help='Galaxy version that initiated the command.', default=None)
    (options, args) = parser.parse_args(argv)
    galaxy_version = options.galaxy_version
    if galaxy_version is None:
        galaxy_version = "19.05"

    gzip = bool(options.gzip)
    assert len(args) >= 2
    temp_directory = args[0]
    out_file = args[1]

    # Create archive.
    return create_archive(temp_directory, out_file, gzip=gzip)


if __name__ == "__main__":
    main()
