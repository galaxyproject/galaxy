"""Unit tests for carrying a notebook page's markdown into a workflow report.

Covers the three pure pieces independently of a running server:
- the directive rewriter mechanics (id line -> label line / drop / passthrough),
- the label index resolution (input vs output vs step, job->ICJ fold, copy
  normalization),
- the auto-label reconcile (expose unstarred outputs, label unnamed inputs/steps,
  dedup against the shared namespace).

The full markdown walk against real datasets/jobs is proved by the API test.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    cast,
)

import pytest

from galaxy import model
from galaxy.managers import workflow_extraction_report as report
from galaxy.managers.markdown_parse import validate_galaxy_markdown
from galaxy.managers.workflow_extraction_report import _ReportLabelRewriter
from galaxy.model import (
    HistoryItem,
    Job,
    StoredWorkflow,
)
from galaxy.workflow.extract import ExtractionLabelIndex


@dataclass
class ContentStub:
    """The history item attributes label resolution reads. Plain copies carry no creating
    job, so get_original_hda normalizes them back to their source."""

    id: int
    history_content_type: str = "dataset"
    copied_from_history_dataset_association: "ContentStub | None" = None
    creating_job_associations: tuple[Any, ...] = ()

    @property
    def hid(self) -> int:
        return self.id


@dataclass
class IcjAssociationStub:
    implicit_collection_jobs_id: int


@dataclass
class JobStub:
    id: int
    implicit_collection_jobs_association: IcjAssociationStub | None = None


def _content(id_: int, history_content_type: str = "dataset", copied_from: ContentStub | None = None) -> Any:
    return ContentStub(id_, history_content_type, copied_from)


def _job(id_: int, icj_id: int | None = None) -> Job:
    icj_association = IcjAssociationStub(icj_id) if icj_id is not None else None
    return cast(Job, JobStub(id_, icj_association))


class FakeIndex:
    """Stand-in resolver for the rewriter mechanics test."""

    def __init__(self, content_args=None, job_args=None):
        self._content_args = content_args or {}
        self._job_args = job_args or {}

    def content_label(self, content):
        return self._content_args.get(content.id)

    def job_label(self, job):
        return self._job_args.get(job.id)


PAGE_HISTORY_ID = 3


def _rewriter(**index_args) -> _ReportLabelRewriter:
    return _ReportLabelRewriter(cast(ExtractionLabelIndex, FakeIndex(**index_args)), PAGE_HISTORY_ID)


def test_rewrite_dataset_to_output_label():
    rewriter = _rewriter(content_args={7: ("output", "aligned")})
    line, whole_block = rewriter.handle_dataset_display(
        "history_dataset_display(history_dataset_id=abc123)\n", _content(7)
    )
    assert line == 'history_dataset_display(output="aligned")\n'
    assert whole_block is False
    assert rewriter.warnings == []


def test_rewrite_dataset_preserves_other_args():
    rewriter = _rewriter(content_args={7: ("output", "aligned")})
    line, _ = rewriter.handle_dataset_as_table(
        'history_dataset_as_table(history_dataset_id=abc123, title="Peek")\n', _content(7)
    )
    assert line == 'history_dataset_as_table(output="aligned", title="Peek")\n'


def test_rewrite_collection_to_input_label():
    rewriter = _rewriter(content_args={5: ("input", "samples")})
    line, _ = rewriter.handle_dataset_collection_display(
        "history_dataset_collection_display(history_dataset_collection_id=def456)\n",
        _content(5, "dataset_collection"),
    )
    assert line == 'history_dataset_collection_display(input="samples")\n'


def test_rewrite_job_to_step_label():
    rewriter = _rewriter(job_args={9: ("step", "bwa_mem")})
    line, _ = rewriter.handle_job_metrics("job_metrics(job_id=abc123)\n", _job(9))
    assert line == 'job_metrics(step="bwa_mem")\n'


def test_unresolved_content_dropped_with_warning():
    rewriter = _rewriter()
    line, whole_block = rewriter.handle_dataset_display(
        "history_dataset_display(history_dataset_id=abc123)\n", _content(7)
    )
    assert line == ""
    assert whole_block is True
    assert rewriter.warnings == ["Dropped a dataset reference from the report: it has no workflow-relative label."]


@pytest.mark.parametrize("label", ['say "hi"', "bwa\nmem", "bwa\rmem", "bwa\x85mem", "bwa mem"])
def test_unquotable_content_label_dropped_with_warning(label):
    step = _tool_step()
    step.create_or_update_workflow_output(output_name="out_file", label=label, uuid=None)
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    rewriter = _ReportLabelRewriter(index, PAGE_HISTORY_ID)
    line, whole_block = rewriter.handle_dataset_display(
        "history_dataset_display(history_dataset_id=abc123)\n", _content(12)
    )
    assert line == ""
    assert whole_block is True
    assert rewriter.warnings == [
        (
            f"Dropped a dataset reference from the report: its label {label!r} contains a double quote or "
            "line break, which report directives cannot express."
        )
    ]


def test_unquotable_input_label_dropped_with_warning():
    index = ExtractionLabelIndex(
        content_to_step={("dataset", 11): (_input_step('my "input"'), "output")}, job_to_step={}, icj_to_step={}
    )
    rewriter = _ReportLabelRewriter(index, PAGE_HISTORY_ID)
    line, _ = rewriter.handle_dataset_peek("history_dataset_peek(history_dataset_id=abc123)\n", _content(11))
    assert line == ""
    assert "contains a double quote or line break" in rewriter.warnings[0]


def test_unportable_directive_dropped_with_warning():
    rewriter = _rewriter()
    line, whole_block = rewriter.handle_workflow_display(
        "workflow_display(workflow_id=abc123)\n", cast(StoredWorkflow, object()), None
    )
    assert line == ""
    assert whole_block is True
    assert "cannot be expressed" in rewriter.warnings[0]


def test_idless_directive_passthrough():
    rewriter = _rewriter()
    line, whole_block = rewriter.handle_generate_time("generate_time()\n", datetime.now())
    assert line == "generate_time()\n"
    assert whole_block is False
    assert rewriter.warnings == []


def _input_step(label, type_="data_input"):
    step = model.WorkflowStep()
    step.type = type_
    step.label = label
    return step


def _tool_step(label=None):
    step = model.WorkflowStep()
    step.type = "tool"
    step.tool_id = "Cut1"
    step.label = label
    return step


def test_index_input_resolves_to_input_label():
    step = _input_step("my_input")
    index = ExtractionLabelIndex(content_to_step={("dataset", 11): (step, "output")}, job_to_step={}, icj_to_step={})
    assert index.content_label(_content(11)) == ("input", "my_input")


def test_index_tool_output_resolves_to_output_label():
    step = _tool_step()
    step.create_or_update_workflow_output(output_name="out_file", label="aligned", uuid=None)
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    assert index.content_label(_content(12)) == ("output", "aligned")


def test_index_tool_output_without_label_is_unresolved():
    step = _tool_step()
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    assert index.content_label(_content(12)) is None


def test_index_normalizes_copied_dataset_to_original():
    step = _tool_step()
    step.create_or_update_workflow_output(output_name="out_file", label="aligned", uuid=None)
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    copy = _content(99, copied_from=_content(12))
    assert index.content_label(copy) == ("output", "aligned")


def test_index_plain_job_resolves_to_step_label():
    step = _tool_step("bwa_mem")
    index = ExtractionLabelIndex(content_to_step={}, job_to_step={9: step}, icj_to_step={})
    assert index.job_label(_job(9)) == ("step", "bwa_mem")


def test_index_mapped_job_folds_to_icj_step_label():
    step = _tool_step("mapped_step")
    index = ExtractionLabelIndex(content_to_step={}, job_to_step={}, icj_to_step={4: step})
    assert index.job_label(_job(9, icj_id=4)) == ("step", "mapped_step")


def _reconcile(
    index: ExtractionLabelIndex,
    contents: Iterable[HistoryItem] = (),
    job_refs: Iterable[int] = (),
    suggested: str | None = None,
) -> list[str]:
    return report.reconcile_report_labels(index, contents, job_refs, (), lambda content: suggested)


def test_reconcile_exposes_unstarred_output():
    step = _tool_step()
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    warnings = _reconcile(index, [_content(12)], suggested="aligned_reads")
    workflow_output = step.workflow_output_for("out_file")
    assert workflow_output is not None
    assert workflow_output.label == "aligned_reads"
    assert warnings == ["Made history item 12 a workflow output ('aligned_reads') because the notebook report uses it."]


def test_reconcile_labels_unnamed_input():
    step = _input_step(None)
    index = ExtractionLabelIndex(content_to_step={("dataset", 11): (step, "output")}, job_to_step={}, icj_to_step={})
    warnings = _reconcile(index, [_content(11)], suggested="raw_input")
    assert step.label == "raw_input"
    assert warnings == []


def test_reconcile_dedupes_against_existing_label():
    starred = _input_step("aligned_reads")
    unstarred = _tool_step()
    index = ExtractionLabelIndex(
        content_to_step={("dataset", 10): (starred, "output"), ("dataset", 12): (unstarred, "out_file")},
        job_to_step={},
        icj_to_step={},
    )
    _reconcile(index, [_content(12)], suggested="aligned_reads")
    workflow_output = unstarred.workflow_output_for("out_file")
    assert workflow_output is not None and workflow_output.label == "aligned_reads_2"


def test_reconcile_label_from_quoted_name_is_directive_safe():
    """Auto-labels derive from suggested names, i.e. from user-controlled dataset
    names. The generated label must always have a directive form -- the user never
    typed it here, so there is nothing for them to correct."""
    step = _tool_step()
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    _reconcile(index, [_content(12)], suggested='say "hi"\nagain')

    assert index.content_label(_content(12)) == ("output", "say hi again")
    validate_galaxy_markdown('```galaxy\nhistory_dataset_display(output="say hi again")\n```\n')


def test_reconcile_deduped_label_stays_within_label_limit():
    starred = _input_step("a" * 255)
    unstarred = _tool_step()
    index = ExtractionLabelIndex(
        content_to_step={("dataset", 10): (starred, "output"), ("dataset", 12): (unstarred, "out_file")},
        job_to_step={},
        icj_to_step={},
    )
    _reconcile(index, [_content(12)], suggested="a" * 300)
    workflow_output = unstarred.workflow_output_for("out_file")
    assert workflow_output is not None and workflow_output.label == "a" * 253 + "_2"


def test_reconcile_labels_referenced_step():
    step = _tool_step()
    step.tool_id = "toolshed.g2.bx.psu.edu/repos/iuc/bwa/bwa_mem/0.7"
    index = ExtractionLabelIndex(content_to_step={}, job_to_step={9: step}, icj_to_step={})
    _reconcile(index, job_refs=[9])
    assert step.label == "bwa_mem"


def test_drop_instance_references_drops_hid_directive():
    swept, warnings = report._drop_instance_references("```galaxy\nhistory_dataset_peek(hid=4)\n```\n")
    assert "hid=" not in swept
    assert "(hid)" in warnings[0]


@pytest.mark.parametrize(
    "argument",
    ['history_dataset_id="5"', "history_dataset_id='abc123'", "history_dataset_id = 5"],
)
def test_drop_instance_references_drops_quoted_or_spaced_id_argument(argument):
    swept, warnings = report._drop_instance_references(f"```galaxy\nhistory_dataset_display({argument})\n```\n")
    assert "history_dataset_id" not in swept
    assert "(history_dataset_id)" in warnings[0]


def test_drop_instance_references_keeps_label_and_argless_directives():
    markdown = (
        '```galaxy\nhistory_dataset_display(output="my job_id=3 output")\n```\n'
        "```galaxy\nhistory_link()\n```\n"
        "```galaxy\ngenerate_time()\n```\n"
        "Prose may mention history_id=5 freely.\n"
    )
    swept, warnings = report._drop_instance_references(markdown)
    assert swept == markdown
    assert warnings == []


def test_drop_instance_references_drops_object_embeds_keeps_idless_embeds():
    markdown = (
        "Name ${galaxy history_dataset_name(history_dataset_id=5)} ran at ${galaxy invocation_time()}, "
        'image ${galaxy history_dataset_as_image(output="x")}, on ${galaxy generate_galaxy_version()} '
        "via ${galaxy instance_access_link()}.\n"
    )
    swept, warnings = report._drop_instance_references(markdown)
    assert (
        swept == "Name  ran at , image , on ${galaxy generate_galaxy_version()} via ${galaxy instance_access_link()}.\n"
    )
    assert warnings == [
        f"Dropped an inline [{container}] reference from the report: inline object references do not resolve "
        "in workflow reports."
        for container in ("history_dataset_name", "invocation_time", "history_dataset_as_image")
    ]


@pytest.mark.parametrize(
    "cell",
    [
        '```visualization\n{"visualization_name": "csv", "dataset_id": "f2db41e1fa331b3e"}\n```\n',
        '```visualization\n{"visualization_name": "csv", "dataset_url": "/api/datasets/f2db41e1fa331b3e/display"}\n```\n',
        '```visualization\n{"visualization_name": "csv", "dataset_label": {"invocation_id": "7", "output": "x"}}\n```\n',
        '```vitessce\n{"datasets": [{"files": [{"__gx_dataset_id": "f2db41e1fa331b3e"}]}]}\n```\n',
    ],
)
def test_drop_instance_references_drops_dataset_cells(cell):
    swept, warnings = report._drop_instance_references(f"# A\n\n{cell}\nAfter.\n")
    assert swept == "# A\n\n\nAfter.\n"
    cell_type = cell.split("\n", 1)[0][3:]
    assert warnings == [
        (
            f"Dropped a [{cell_type}] cell from the report: it names a specific dataset or invocation, which has no "
            "workflow-relative form."
        )
    ]


@pytest.mark.parametrize(
    "cell",
    [
        '  ```visualization\n{"visualization_name": "csv", "dataset_id": "f2db41e1fa331b3e"}\n  ```\n',
        '```visualization\r\n{"visualization_name": "csv", "dataset_id": "f2db41e1fa331b3e"}\r\n```\r\n',
    ],
    ids=["indented", "crlf"],
)
def test_drop_instance_references_drops_cells_the_client_parses(cell):
    markdown = f"# A\n\n{cell}\nAfter.\n"
    validate_galaxy_markdown(markdown)
    swept, warnings = report._drop_instance_references(markdown)
    assert "f2db41e1fa331b3e" not in swept
    assert "After." in swept
    assert len(warnings) == 1


def test_drop_instance_references_keeps_workflow_relative_visualization():
    markdown = (
        '```visualization\n{"visualization_name": "csv", "dataset_label": {"invocation_id": "", "output": "x"}}\n```\n'
    )
    swept, warnings = report._drop_instance_references(markdown)
    assert swept == markdown
    assert warnings == []
