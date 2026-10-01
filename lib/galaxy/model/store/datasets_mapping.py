"""Human-readable mapping of exported datasets to archive file paths.

The mapping is a pure projection over the already-serialized dataset
dictionaries written to ``datasets_attrs.txt`` (and its ``.provenance``
companion), so the TSV can never disagree with the machine-readable
metadata. Only ``file_size`` and collection membership are not part of the
serialized dictionaries and are supplied by the caller.

The file follows the IANA ``text/tab-separated-values`` format: values are
never quoted, and tabs or line breaks inside values are replaced with a
single space. ``datasets_attrs.txt`` keeps the exact values.
"""

import csv
import os
import re
from collections.abc import (
    Iterable,
    Iterator,
)
from typing import (
    Any,
    NamedTuple,
)

from galaxy import model
from galaxy.util.path import StrPath

DATASETS_MAPPING_FILENAME = "datasets_mapping.tsv"

DATASETS_MAPPING_COLUMNS = (
    "hid",
    "name",
    "exported_file",
    "extension",
    "state",
    "collection_name",
    "element_identifier",
    "tags",
    "annotation",
    "file_size",
    "create_time",
    "update_time",
)

TSV_UNSAFE_WHITESPACE = re.compile(r"[\t\r\n]+")


class CollectionMembership(NamedTuple):
    """A dataset's place in an exported collection.

    ``element_identifier`` is the identifier path within nested collections, e.g. ``sample1/forward``.
    """

    collection_name: str
    element_identifier: str


class MappingEntry(NamedTuple):
    serialized: dict[str, Any]
    file_size: str
    collections: list[CollectionMembership]


def _dataset_element_identifiers(
    collection: model.DatasetCollection, parent_identifiers: tuple[str, ...] = ()
) -> Iterator[tuple[model.HistoryDatasetAssociation, str]]:
    for element in collection.elements:
        identifiers = (*parent_identifiers, element.element_identifier or "")
        if element.child_collection is not None:
            yield from _dataset_element_identifiers(element.child_collection, identifiers)
        elif element.hda is not None:
            yield element.hda, "/".join(identifiers)


def collection_memberships_by_hda_id(
    included_collections: Iterable[model.DatasetCollection | model.HistoryDatasetCollectionAssociation],
) -> dict[int, list[CollectionMembership]]:
    memberships: dict[int, list[CollectionMembership]] = {}
    for collection in included_collections:
        if isinstance(collection, model.HistoryDatasetCollectionAssociation):
            for hda, element_identifier in _dataset_element_identifiers(collection.collection):
                if hda.id is not None:
                    membership = CollectionMembership(collection.name or "", element_identifier)
                    memberships.setdefault(hda.id, []).append(membership)
    return memberships


def collection_memberships_of(
    dataset: model.DatasetInstance, memberships_by_hda_id: dict[int, list[CollectionMembership]]
) -> list[CollectionMembership]:
    if isinstance(dataset, model.HistoryDatasetAssociation) and dataset.id is not None:
        return memberships_by_hda_id.get(dataset.id, [])
    return []


def file_size_of(dataset: model.DatasetInstance) -> str:
    if dataset.dataset is not None and dataset.dataset.file_size is not None:
        return str(dataset.dataset.file_size)
    return ""


def tsv_safe(value: str) -> str:
    return TSV_UNSAFE_WHITESPACE.sub(" ", value)


def mapping_row(entry: MappingEntry) -> dict[str, str]:
    serialized = entry.serialized
    tags = serialized.get("tags") or []
    collections = sorted(set(entry.collections))
    row = {
        "hid": str(serialized.get("hid") or ""),
        "name": serialized.get("name") or "",
        "exported_file": serialized.get("file_name") or "",
        "extension": serialized.get("extension") or "",
        "state": str(serialized.get("state") or ""),
        "collection_name": "; ".join(membership.collection_name for membership in collections),
        "element_identifier": "; ".join(membership.element_identifier for membership in collections),
        "tags": ",".join(tags),
        "annotation": serialized.get("annotation") or "",
        "file_size": entry.file_size,
        "create_time": serialized.get("create_time") or "",
        "update_time": serialized.get("update_time") or "",
    }
    return {column: tsv_safe(value) for column, value in row.items()}


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
            quoting=csv.QUOTE_NONE,
            quotechar=None,
        )
        writer.writeheader()
        writer.writerows(rows)
