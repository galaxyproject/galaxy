from typing import (
    cast,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
)

from galaxy.tool_util.biotools import BiotoolsMetadataSource
from galaxy.tool_util.parser import ToolSource
from galaxy.util.resources import files


def _multi_dict_mapping(content: str) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for x in content.splitlines():
        if x.startswith("#"):
            continue
        key, value = cast(Tuple[str, str], tuple(x.split("\t")))
        mapping.setdefault(key, []).append(value)
    return mapping


def _read_ontology_data_text(filename: str) -> str:
    return files(PACKAGE).joinpath(filename).read_text()


PACKAGE = "galaxy.tool_util.ontologies"
BIOTOOLS_MAPPING_FILENAME = "biotools_mappings.tsv"
EDAM_OPERATION_MAPPING_FILENAME = "edam_operation_mappings.tsv"
EDAM_TOPIC_MAPPING_FILENAME = "edam_topic_mappings.tsv"

BIOTOOLS_MAPPING_CONTENT = _read_ontology_data_text(BIOTOOLS_MAPPING_FILENAME)
BIOTOOLS_MAPPING: Dict[str, str] = dict(
    [
        cast(Tuple[str, str], tuple(x.split("\t")))
        for x in BIOTOOLS_MAPPING_CONTENT.splitlines()
        if not x.startswith("#")
    ]
)
EDAM_OPERATION_MAPPING_CONTENT = _read_ontology_data_text(EDAM_OPERATION_MAPPING_FILENAME)
EDAM_OPERATION_MAPPING: Dict[str, List[str]] = _multi_dict_mapping(EDAM_OPERATION_MAPPING_CONTENT)

EDAM_TOPIC_MAPPING_CONTENT = _read_ontology_data_text(EDAM_TOPIC_MAPPING_FILENAME)
EDAM_TOPIC_MAPPING: Dict[str, List[str]] = _multi_dict_mapping(EDAM_TOPIC_MAPPING_CONTENT)


class OntologyData(NamedTuple):
    xrefs: List[Dict[str, str]]
    edam_operations: Optional[List[str]]
    edam_topics: Optional[List[str]]


def biotools_reference(xrefs):
    for xref in xrefs:
        if xref["reftype"] == "bio.tools":
            return xref["value"]
    return None


def legacy_biotools_external_reference(all_ids: List[str]) -> Optional[str]:
    for tool_id in all_ids:
        if tool_id in BIOTOOLS_MAPPING:
            return BIOTOOLS_MAPPING[tool_id]
    return None


def expand_ontology_data(
    tool_source: ToolSource, all_ids: List[str], biotools_metadata_source: Optional[BiotoolsMetadataSource]
) -> OntologyData:
    xrefs = tool_source.parse_xrefs()
    has_biotools_reference = any(x["reftype"] == "bio.tools" for x in xrefs)
    if not has_biotools_reference:
        legacy_biotools_ref = legacy_biotools_external_reference(all_ids)
        if legacy_biotools_ref is not None:
            xrefs.append({"value": legacy_biotools_ref, "reftype": "bio.tools"})

    edam_operations = tool_source.parse_edam_operations()
    edam_topics = tool_source.parse_edam_topics()

    for tool_id in all_ids:
        if tool_id in EDAM_OPERATION_MAPPING:
            edam_operations = EDAM_OPERATION_MAPPING[tool_id]
            break

    for tool_id in all_ids:
        if tool_id in EDAM_TOPIC_MAPPING:
            edam_topics = EDAM_TOPIC_MAPPING[tool_id]
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
    )
