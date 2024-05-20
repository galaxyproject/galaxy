import argparse
import logging
import os
import sys

import yaml

import galaxy.model
from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.model import store
from galaxy.model.store.discover import persist_target_to_export_store
from galaxy.objectstore import build_object_store_from_config
from galaxy.util.bunch import Bunch

DESCRIPTION = """Build import ready model objects from YAML description of files.

The positional argument to this script should be a a YAML file containing a
data fetch API-like YAML file describing files. This script will then import
this data into a defined object store and populate metadata corresponding to
these files as datasets into a "model store".

The YAML file should contain a dictionary of destination+elements objects or a
list of such dictionaries. Each such destination+elements dictionary should
contain at least two keys - 'destination' and 'items'.

Examples of destinations for creating libraries and just populating history
datasets are as follows:

```
destination:
  type: library
  name: Training Material
  description: Data for selected tutorials from https://training.galaxyproject.org.
```

```
destination:
  type: hdas
````

The 'items' definition should be a list of files or library folders. If library
folders need to be setup they should each be defined with a name and recursive
set of items (again files or folders). The following code fragment describes
both a library folder definition and a file entry:

```
items:
  - name: "Example Folder 1"
    description: "Description of what is in Example Folder 1"
    items:
      - url: https://raw.githubusercontent.com/eteriSokhoyan/test-data/master/cliques-high-representatives.fa
        filename: cliques-high-representatives.fa
        ext: fasta
        info: "A cool longer description."
        dbkey: "hg19"
        md5: e5d21b1ea57fc9a31f8ea0110531bf3d
```

Currently for each file a filename must be supplied, url information will be
stored if provided but not fetched on-demand like the upload 2.0/data fetch
endpoint.

Differences with respect to the Upload 2.0 YAML/JSON format: currently various
src tags such as 'url' are not supported, data cleaning options such as
to_posix_lines, and space_to_tab are not supported, unpacking zip files and
walking directories etc.. are not supported either. The format consumed by
this script should continue to evolve to converge with the upload 2.0 format.
"""

logging.basicConfig()
log = logging.getLogger(__name__)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    object_store_config = Bunch(
        object_store_store_by="uuid",
        object_store_config_file=args.object_store_config,
        object_store_check_old_style=False,
        jobs_directory=None,
        new_file_path=None,
        umask=os.umask(0o77),
        gid=os.getgid(),
    )
    object_store = build_object_store_from_config(object_store_config)
    galaxy.model.Dataset.object_store = object_store
    galaxy.model.set_datatypes_registry(example_datatype_registry_for_sample())
    from galaxy.model import mapping

    mapping.init("/tmp", "sqlite:///:memory:", create_tables=True)
    galaxy.model.setup_global_object_store_for_models(object_store)
    with open(args.objects) as f:
        targets = yaml.safe_load(f)
        if not isinstance(targets, list):
            targets = [targets]

    export_path = args.export
    export_type = args.export_type

    if export_type is None:
        export_type = "directory" if not export_path.endswith(".tgz") else "bag_archive"

    export_types = {
        "directory": store.DirectoryModelExportStore,
        "tar": store.TarModelExportStore,
        "bag_directory": store.BagDirectoryModelExportStore,
        "bag_archive": store.BagArchiveModelExportStore,
    }
    store_class = export_types[export_type]
    export_kwds = {
        "serialize_dataset_objects": True,
    }

    with store_class(export_path, **export_kwds) as export_store:
        for target in targets:
            persist_target_to_export_store(target, export_store, object_store, ".")


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("objects", metavar="OBJECT_CONFIG", help="config file describing files to build objects for")
    parser.add_argument("--object-store-config", help="object store configuration file")
    parser.add_argument("-e", "--export", default="export", help="export path")
    parser.add_argument("--export-type", default=None, help="export type (if needed)")
    return parser


if __name__ == "__main__":
    main()
