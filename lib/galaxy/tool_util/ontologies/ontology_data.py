import logging
from collections import defaultdict
from functools import lru_cache
from typing import (
    cast,
    NamedTuple,
)

import yaml

from galaxy.tool_util.biotools import BiotoolsMetadataSource
from galaxy.tool_util.parser import ToolSource
from galaxy.tool_util_models.tool_source import XrefDict
from galaxy.util.resources import resource_string

log = logging.getLogger(__name__)


def _multi_dict_mapping(content: str) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for x in content.splitlines():
        if x.startswith("#"):
            continue
        key, value = cast(tuple[str, str], tuple(x.split("\t")))
        mapping.setdefault(key, []).append(value)
    return mapping


def _read_ontology_data_text(filename: str) -> str:
    return resource_string(__name__, filename)


BIOTOOLS_MAPPING_FILENAME = "biotools_mappings.tsv"
EDAM_OPERATION_MAPPING_FILENAME = "edam_operation_mappings.tsv"
EDAM_TOPIC_MAPPING_FILENAME = "edam_topic_mappings.tsv"
TOOL_TAG_MAPPING_FILENAME = "tool_tag_mappings.yml"


@lru_cache(maxsize=1)
def _biotools_mapping() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    for line in _read_ontology_data_text(BIOTOOLS_MAPPING_FILENAME).splitlines():
        if not line.startswith("#"):
            tool_id, xref = line.split("\t")
            mapping[tool_id].append(xref)
    return mapping


@lru_cache(maxsize=1)
def _edam_operation_mapping() -> dict[str, list[str]]:
    return _multi_dict_mapping(_read_ontology_data_text(EDAM_OPERATION_MAPPING_FILENAME))


@lru_cache(maxsize=1)
def _edam_topic_mapping() -> dict[str, list[str]]:
    return _multi_dict_mapping(_read_ontology_data_text(EDAM_TOPIC_MAPPING_FILENAME))


def _load_tool_tag_mapping(content: str) -> dict[str, list[str]]:
    raw = cast(
        dict[str, list[str]],
        (yaml.safe_load(content) or {}).get("tool_tags", {}),
    )
    # `Tool.all_ids` is built from lowercased tool ids (see `Tool.parse` in
    # `lib/galaxy/tools/__init__.py`, around the `self_ids = [self.id.lower()]`
    # block), so the curated mapping must use lowercase keys to be looked up
    # successfully. Normalize at load time so admin-supplied YAML files don't
    # have to worry about case.
    return {tool_id.lower(): tags for tool_id, tags in raw.items()}


_TOOL_TAG_MAPPING_OVERRIDE: dict[str, list[str]] | None = None


def _tool_tag_mapping() -> dict[str, list[str]]:
    if _TOOL_TAG_MAPPING_OVERRIDE is not None:
        return _TOOL_TAG_MAPPING_OVERRIDE
    return _bundled_tool_tag_mapping()


@lru_cache(maxsize=1)
def _bundled_tool_tag_mapping() -> dict[str, list[str]]:
    return _load_tool_tag_mapping(_read_ontology_data_text(TOOL_TAG_MAPPING_FILENAME))


def configure_tool_tag_mapping(file_path: str | None) -> None:
    """Replace the in-memory curated tool → tag mapping.

    Galaxy calls this once at startup with the value of the
    ``tool_tag_mappings_file`` config option. If ``file_path`` is empty or
    ``None``, the bundled minimal mapping (see ``tool_tag_mappings.yml``) is
    retained. Missing or unreadable files are logged and the in-memory
    mapping is left untouched so a typo in ``galaxy.yml`` doesn't take down
    tool loading.
    """
    if not file_path:
        return
    try:
        with open(file_path, encoding="utf-8") as fh:
            new_mapping = _load_tool_tag_mapping(fh.read())
    except OSError:
        # Surface the failure but keep the bundled fallback active.
        log.warning(
            "Could not read tool_tag_mappings_file %s; falling back to bundled mapping.",
            file_path,
        )
        return
    global _TOOL_TAG_MAPPING_OVERRIDE
    _TOOL_TAG_MAPPING_OVERRIDE = new_mapping


class OntologyData(NamedTuple):
    xrefs: list[XrefDict]
    edam_operations: list[str] | None
    edam_topics: list[str] | None
    tool_tags: list[str]


def biotools_reference(xrefs):
    for xref in xrefs:
        if xref["type"] == "bio.tools":
            return xref["value"]
    return None


def legacy_biotools_external_reference(all_ids: list[str]) -> list[str]:
    biotools_mapping = _biotools_mapping()
    for tool_id in all_ids:
        if tool_id in biotools_mapping:
            return biotools_mapping[tool_id]
    return []


def curated_tool_tags(all_ids: list[str]) -> list[str]:
    mapping = _tool_tag_mapping()
    seen = set()
    tags: list[str] = []
    for tool_id in all_ids:
        for tag in mapping.get(tool_id, []):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


def expand_ontology_data(
    tool_source: ToolSource, all_ids: list[str], biotools_metadata_source: BiotoolsMetadataSource | None
) -> OntologyData:
    xrefs = tool_source.parse_xrefs()
    has_biotools_reference = any(x["type"] == "bio.tools" for x in xrefs)
    if not has_biotools_reference:
        for legacy_biotools_ref in legacy_biotools_external_reference(all_ids):
            if legacy_biotools_ref is not None:
                xrefs.append({"value": legacy_biotools_ref, "type": "bio.tools"})

    edam_operations = tool_source.parse_edam_operations()
    edam_topics = tool_source.parse_edam_topics()

    edam_operation_mapping = _edam_operation_mapping()
    for tool_id in all_ids:
        if tool_id in edam_operation_mapping:
            edam_operations = edam_operation_mapping[tool_id]
            break

    edam_topic_mapping = _edam_topic_mapping()
    for tool_id in all_ids:
        if tool_id in edam_topic_mapping:
            edam_topics = edam_topic_mapping[tool_id]
            break

    has_missing_data = len(edam_operations) == 0 or len(edam_topics) == 0
    if has_missing_data:
        biotools_reference_str = biotools_reference(xrefs)
        if biotools_reference_str and biotools_metadata_source:
            biotools_entry = biotools_metadata_source.get_biotools_metadata(biotools_reference_str)
            if biotools_entry:
                edam_info = biotools_entry.edam_info
                if len(edam_operations) == 0:
                    edam_operations = edam_info.edam_operations
                if len(edam_topics) == 0:
                    edam_topics = edam_info.edam_topics

    return OntologyData(
        xrefs,
        edam_operations,
        edam_topics,
        curated_tool_tags(all_ids),
    )
