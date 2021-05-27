import argparse
import json
import os
import sys

from galaxy.files import ConfiguredFileSources


def get_file_sources(file_sources_path):
    assert os.path.exists(file_sources_path), f"file sources path [{file_sources_path}] does not exist"
    with open(file_sources_path, "r") as f:
        file_sources_as_dict = json.load(f)
    file_sources = ConfiguredFileSources.from_dict(file_sources_as_dict)
    return file_sources


def check_for_duplicate_name(files_to_export):
    seen = set()
    duplicates = set()
    for entry in files_to_export:
        name = entry['name']
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    if duplicates:
        sys.exit(f"Duplicate export filenames given: {', '.join(duplicates)}, failing export")


def write_if_not_exists(file_sources, target_uri, real_data_path):
    file_source_path = file_sources.get_file_source_path(target_uri)
    if os.path.exists(file_source_path.path):
        print(f'Error: File "{file_source_path.path}" already exists. Skipping.')
        return 1
    file_source = file_source_path.file_source
    file_source.write_from(file_source_path.path, real_data_path)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = _parser().parse_args(argv)
    exit_code = 0
    file_sources = get_file_sources(args.file_sources)
    directory_uri = args.directory_uri
    export_metadata_files = args.export_metadata_files
    with open(args.files_to_export) as f:
        files_to_export = json.load(f)
    counter = 0
    check_for_duplicate_name(files_to_export)
    for entry in files_to_export:
        name = entry["name"]
        real_data_path = entry["real_data_path"]
        if directory_uri.endswith("/"):
            target_uri = directory_uri + name
        else:
            target_uri = directory_uri + "/" + name
        if write_if_not_exists(file_sources, target_uri, real_data_path):
            exit_code = 1
        if export_metadata_files:
            metadata_files = entry.get('metadata_files', [])
            for extension, path in metadata_files:
                metadata_file_uri = f"{target_uri}.{extension}"
                if write_if_not_exists(file_sources, metadata_file_uri, path):
                    exit_code = 1
        counter += 1
    print(f"{counter} out of {len(files_to_export)} files have been exported.\n")
    sys.exit(exit_code)


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory-uri", type=str, help="directory target URI")
    parser.add_argument("--file-sources", type=str, help="file sources json")
    parser.add_argument("--files-to-export", type=str, help="files to export")
    parser.add_argument("--export-metadata-files", type=bool, help="export metadata files", default=True)
    return parser


if __name__ == "__main__":
    main()
