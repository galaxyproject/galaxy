"""Helpers for suggesting workflow output labels during extraction."""

import re
from dataclasses import dataclass
from typing import (
    Literal,
)

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.jobs import get_output_name
from galaxy.managers.markdown_parse import UNQUOTABLE_ARGUMENT_CHARS
from galaxy.model import (
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    HistoryItem,
    Job,
)
from galaxy.tool_util.parser.output_objects import ToolOutputBase
from galaxy.workflow.extract import (
    get_original_hda,
    get_original_hdca,
    skip_output_assoc_name,
    tool_for_job,
)

SuggestedNameSource = Literal["renamed", "rendered_label", "bare_label", "port_name"]


@dataclass(frozen=True)
class SuggestedName:
    name: str
    source: SuggestedNameSource


MAX_LABEL_LENGTH = 255
UNQUOTABLE_PATTERN = re.compile(f"[{re.escape(UNQUOTABLE_ARGUMENT_CHARS)}]")


def normalize_label(value: str | None) -> str:
    """Collapse internal whitespace and clamp to the workflow-label length limit."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip())[:MAX_LABEL_LENGTH]


def normalize_generated_label(value: str | None) -> str:
    """``normalize_label`` minus characters a report directive cannot quote."""
    return normalize_label(UNQUOTABLE_PATTERN.sub(" ", value or ""))


def suggested_output_name(trans: ProvidesHistoryContext, content: HistoryItem) -> SuggestedName | None:
    """Return a best-effort workflow output label suggestion for an HDA/HDCA."""
    suggested: SuggestedName | None
    if isinstance(content, HistoryDatasetCollectionAssociation):
        suggested = _suggested_hdca_output_name(trans, get_original_hdca(content))
    else:
        suggested = _suggested_hda_output_name(trans, get_original_hda(content))
    if suggested is None:
        return None
    name = normalize_generated_label(suggested.name)
    return SuggestedName(name=name, source=suggested.source) if name else None


def _suggested_hda_output_name(trans: ProvidesHistoryContext, hda: HistoryDatasetAssociation) -> SuggestedName | None:
    assoc = next(
        (assoc for assoc in hda.creating_job_associations if not skip_output_assoc_name(assoc.name)),
        None,
    )
    if assoc is None:
        return _content_name(hda)
    job = assoc.job
    tool = tool_for_job(trans, job)
    tool_output = tool.outputs.get(assoc.name) if tool is not None else None
    params = _params_for_job(tool, job)
    return _apply_chain(content_name=hda.name, tool_output=tool_output, port_name=assoc.name, params=params, tool=tool)


def _suggested_hdca_output_name(
    trans: ProvidesHistoryContext, hdca: HistoryDatasetCollectionAssociation
) -> SuggestedName | None:
    output_name = hdca.implicit_output_name
    job: Job | None = None
    if output_name and hdca.implicit_collection_jobs is not None:
        job = hdca.implicit_collection_jobs.representative_job
    else:
        assoc = next(iter(hdca.creating_job_associations), None)
        if assoc is not None:
            job = assoc.job
            output_name = assoc.name

    if not output_name:
        return _content_name(hdca)

    tool = tool_for_job(trans, job) if job is not None else None
    tool_output = None
    if tool is not None:
        tool_output = tool.output_collections.get(output_name) or tool.outputs.get(output_name)
    params = _params_for_job(tool, job)
    return _apply_chain(
        content_name=hdca.name,
        tool_output=tool_output,
        port_name=output_name,
        params=params,
        tool=tool,
    )


def _params_for_job(tool, job: Job | None):
    if tool is None or job is None:
        return None
    try:
        return tool.get_param_values(job, ignore_errors=True)
    except Exception:
        return None


def _apply_chain(
    *,
    content_name: str | None,
    tool_output: ToolOutputBase | None,
    port_name: str | None,
    params: dict | None,
    tool,
) -> SuggestedName | None:
    rendered_name = None
    if tool is not None and tool_output is not None and params is not None:
        rendered_name = get_output_name(tool=tool, output=tool_output, params=dict(params))

    if rendered_name and content_name and content_name != rendered_name:
        return SuggestedName(content_name, "renamed")
    if tool_output is not None and tool_output.label:
        if rendered_name:
            return SuggestedName(rendered_name, "rendered_label")
        return SuggestedName(tool_output.label, "bare_label")
    if port_name:
        return SuggestedName(port_name, "port_name")
    return _content_name_from_string(content_name)


def _content_name(content) -> SuggestedName | None:
    return _content_name_from_string(getattr(content, "name", None))


def _content_name_from_string(content_name: str | None) -> SuggestedName | None:
    if content_name:
        return SuggestedName(content_name, "renamed")
    return None
