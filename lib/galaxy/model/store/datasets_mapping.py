"""Human-readable mapping of exported datasets to archive file paths.

The mapping is a pure projection over the already-serialized dataset
dictionaries written to ``datasets_attrs.txt`` (and its ``.provenance``
companion), so the TSV can never disagree with the machine-readable
metadata. Only ``file_size`` and ``collection_name`` are not part of the
serialized dictionaries and are supplied by the caller.
"""

import csv
import os
from typing import (
    Any,
    NamedTuple,
)
from collections.abc import Iterable

from rocrate.rocrate import ROCrate

from galaxy import model
from galaxy.util.path import StrPath

DATASETS_MAPPING_FILENAME = "datasets_mapping.tsv"
DATASETS_MAPPING_ENCODING_FORMAT = "text/tab-separated-values"

DATASETS_MAPPING_COLUMNS = (
    "hid",
    "name",
    "exported_file",
    "extension",
    "state",
    "collection_name",
    "tags",
    "annotation",
    "file_size",
    "create_time",
    "update_time",
)


class MappingEntry(NamedTuple):
    serialized: dict[str, Any]
    file_size: str
    collection_name: str


def collection_names_by_dataset_id(
    included_collections: Iterable[model.DatasetCollection | model.HistoryDatasetCollectionAssociation,],
) -> dict[int, str]:
    names: dict[int, list[str]] = {}
    for collection in included_collections:
        if isinstance(collection, model.HistoryDatasetCollectionAssociation):
            for hda in collection.dataset_instances:
                if hda.id is not None:
                    names.setdefault(hda.id, []).append(collection.name or "")
    return {dataset_id: "; ".join(sorted(set(values))) for dataset_id, values in names.items()}


def file_size_of(dataset: model.DatasetInstance) -> str:
    if dataset.dataset is not None and dataset.dataset.file_size is not None:
        return str(dataset.dataset.file_size)
    return ""


def mapping_row(entry: MappingEntry) -> dict[str, str]:
    serialized = entry.serialized
    tags = serialized.get("tags") or []
    return {
        "hid": str(serialized.get("hid") or ""),
        "name": serialized.get("name") or "",
        "exported_file": serialized.get("file_name") or "",
        "extension": serialized.get("extension") or "",
        "state": str(serialized.get("state") or ""),
        "collection_name": entry.collection_name,
        "tags": ",".join(tags),
        "annotation": serialized.get("annotation") or "",
        "file_size": entry.file_size,
        "create_time": serialized.get("create_time") or "",
        "update_time": serialized.get("update_time") or "",
    }


def write_datasets_mapping(export_directory: StrPath, entries: list[MappingEntry]) -> None:
    if not entries:
        return
    rows = [mapping_row(entry) for entry in entries]
    rows.sort(key=lambda row: (row["hid"] == "", row["hid"].zfill(10), row["name"]))
    mapping_path = os.path.join(export_directory, DATASETS_MAPPING_FILENAME)
    with open(mapping_path, "w", encoding="utf-8", newline="") as mapping_file:
        writer = csv.DictWriter(
            mapping_file,
            fieldnames=list(DATASETS_MAPPING_COLUMNS),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def add_mapping_file_to_crate(crate: ROCrate, export_directory: StrPath) -> None:
    mapping_path = os.path.join(export_directory, DATASETS_MAPPING_FILENAME)
    if os.path.exists(mapping_path):
        crate.add_file(
            mapping_path,
            dest_path=DATASETS_MAPPING_FILENAME,
            properties={
                "name": DATASETS_MAPPING_FILENAME,
                "encodingFormat": DATASETS_MAPPING_ENCODING_FORMAT,
                "about": {"@id": "./"},
                "description": "Tabular mapping of Galaxy datasets to exported files",
            },
        )
