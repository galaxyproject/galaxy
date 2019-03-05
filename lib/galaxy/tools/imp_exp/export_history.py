#!/usr/bin/env python
"""
Export a history to an archive file using attribute files.

usage: %prog history_attrs dataset_attrs job_attrs out_file
    -G, --gzip: gzip archive file
"""
from __future__ import print_function

import optparse
import os
import shutil
import sys

from galaxy.model.store import tar_export_directory


def create_archive(export_directory, out_file, gzip=False):
    """Create archive from the given attribute/metadata files and save it to out_file."""
    try:
        tar_export_directory(export_directory, out_file, gzip)
        # Status.
        print('Created history archive.')
        return 0
    except Exception as e:
        print('Error creating history archive: %s' % str(e), file=sys.stderr)
        return 1


def main(argv=None):
    # Parse command line.
    parser = optparse.OptionParser()
    parser.add_option('-G', '--gzip', dest='gzip', action="store_true", help='Compress archive using gzip.')
    parser.add_option('--galaxy-version', dest='galaxy_version', help='Galaxy version that initiated the command.', default=None)
    (options, args) = parser.parse_args(argv)
    galaxy_version = options.galaxy_version
    if galaxy_version is None:
        galaxy_version = "19.01" if len(args) == 4 else "19.05"

    gzip = bool(options.gzip)
    if galaxy_version == "19.01":
        # This job was created pre 18.0X with old argument style.
        out_file = args[3]
        temp_directory = os.path.dirname(args[0])
    else:
        assert len(args) >= 2
        # We have a 19.0X directory argument instead of individual arguments.
        temp_directory = args[0]
        out_file = args[1]

    if galaxy_version == "19.01":
        history_attrs = os.path.join(temp_directory, 'history_attrs.txt')
        dataset_attrs = os.path.join(temp_directory, 'datasets_attrs.txt')
        job_attrs = os.path.join(temp_directory, 'jobs_attrs.txt')

        shutil.move(args[0], history_attrs)
        shutil.move(args[1], dataset_attrs)
        provenance_path = args[1] + ".provenance"
        if os.path.exists(provenance_path):
            shutil.move(provenance_path, dataset_attrs + ".provenance")
        shutil.move(args[2], job_attrs)

    # Create archive.
    return create_archive(temp_directory, out_file, gzip=gzip)


if __name__ == "__main__":
    main()
