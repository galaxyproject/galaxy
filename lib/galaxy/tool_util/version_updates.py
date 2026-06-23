"""Workflow-safe tool version updates.

Maps tool IDs to version ranges where parameter schemas are unchanged,
so an older workflow referencing min_version can safely use current_version's
tool definition for validation and state inspection.
"""

from typing import (
    Dict,
    NamedTuple,
    Optional,
)

from .version import parse_version
from .version_util import AnyVersionT


class safe_update(NamedTuple):
    min_version: AnyVersionT
    current_version: AnyVersionT


WORKFLOW_SAFE_TOOL_VERSION_UPDATES: Dict[str, safe_update] = {
    "Filter1": safe_update(parse_version("1.1.0"), parse_version("1.1.1")),
    "__BUILD_LIST__": safe_update(parse_version("1.0.0"), parse_version("1.1.0")),
    "__APPLY_RULES__": safe_update(parse_version("1.0.0"), parse_version("1.1.0")),
    "__EXTRACT_DATASET__": safe_update(parse_version("1.0.0"), parse_version("1.0.2")),
    "__RELABEL_FROM_FILE__": safe_update(parse_version("1.0.0"), parse_version("1.1.0")),
    "Grep1": safe_update(parse_version("1.0.1"), parse_version("1.0.4")),
    "Show beginning1": safe_update(parse_version("1.0.0"), parse_version("1.0.2")),
    "Show tail1": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "sort1": safe_update(parse_version("1.1.0"), parse_version("1.2.0")),
    "Convert characters1": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "CONVERTER_interval_to_bgzip_0": safe_update(parse_version("1.0.1"), parse_version("1.0.2")),
    "CONVERTER_Bam_Bai_0": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "CONVERTER_cram_to_bam_0": safe_update(parse_version("1.0.1"), parse_version("1.0.2")),
    "CONVERTER_fasta_to_fai": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "CONVERTER_sam_to_bigwig_0": safe_update(parse_version("1.0.2"), parse_version("1.0.3")),
    "CONVERTER_bam_to_coodinate_sorted_bam": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "CONVERTER_bam_to_qname_sorted_bam": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
}


def is_workflow_safe_version(tool_id: str, requested_version: str) -> Optional[str]:
    """Check if requested_version falls within a safe update range for tool_id.

    Returns the current_version string if safe, None otherwise.
    """
    update = WORKFLOW_SAFE_TOOL_VERSION_UPDATES.get(tool_id)
    if update is None:
        return None
    requested = parse_version(requested_version)
    if update.min_version <= requested <= update.current_version:
        return str(update.current_version)
    return None
