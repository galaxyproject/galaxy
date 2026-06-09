"""Unit tests for carrying a notebook page's markdown into a workflow report.

Covers the three pure pieces independently of a running server:
- the directive rewriter mechanics (id line -> label line / drop / passthrough),
- the label index resolution (input vs output vs step, job->ICJ fold, copy
  normalization),
- the auto-label reconcile (expose unstarred outputs, label unnamed inputs/steps,
  dedup against the shared namespace).

The full markdown walk against real datasets/jobs is proved by the API test.
"""

from types import SimpleNamespace

from galaxy import model
from galaxy.managers import workflow_extraction_report as report
from galaxy.managers.workflow_extraction_report import _ReportLabelRewriter
from galaxy.workflow.extract import ExtractionLabelIndex


class FakeIndex:
    """Stand-in resolver for the rewriter mechanics test."""

    def __init__(self, content_args=None, job_args=None):
        self._content_args = content_args or {}
        self._job_args = job_args or {}

    def content_label_arg(self, kind, content):
        return self._content_args.get((kind, content.id))

    def job_label_arg(self, job):
        return self._job_args.get(job.id)


def _hda(id_):
    return SimpleNamespace(id=id_)


# --- rewriter mechanics -----------------------------------------------------


def test_rewrite_dataset_to_output_label():
    rewriter = _ReportLabelRewriter(FakeIndex(content_args={("hda", 7): 'output="aligned"'}))
    line, whole_block = rewriter.handle_dataset_display("history_dataset_display(history_dataset_id=abc123)\n", _hda(7))
    assert line == 'history_dataset_display(output="aligned")\n'
    assert whole_block is False
    assert rewriter.warnings == []


def test_rewrite_dataset_preserves_other_args():
    rewriter = _ReportLabelRewriter(FakeIndex(content_args={("hda", 7): 'output="aligned"'}))
    line, _ = rewriter.handle_dataset_as_table(
        'history_dataset_as_table(history_dataset_id=abc123, title="Peek")\n', _hda(7)
    )
    assert line == 'history_dataset_as_table(output="aligned", title="Peek")\n'


def test_rewrite_collection_to_input_label():
    rewriter = _ReportLabelRewriter(FakeIndex(content_args={("hdca", 5): 'input="samples"'}))
    line, _ = rewriter.handle_dataset_collection_display(
        "history_dataset_collection_display(history_dataset_collection_id=def456)\n", _hda(5)
    )
    assert line == 'history_dataset_collection_display(input="samples")\n'


def test_rewrite_job_to_step_label():
    rewriter = _ReportLabelRewriter(FakeIndex(job_args={9: 'step="bwa_mem"'}))
    line, _ = rewriter.handle_job_metrics("job_metrics(job_id=abc123)\n", SimpleNamespace(id=9))
    assert line == 'job_metrics(step="bwa_mem")\n'


def test_unresolved_content_dropped_with_warning():
    rewriter = _ReportLabelRewriter(FakeIndex())
    line, whole_block = rewriter.handle_dataset_display("history_dataset_display(history_dataset_id=abc123)\n", _hda(7))
    assert line == ""
    assert whole_block is True
    assert len(rewriter.warnings) == 1


def test_unportable_directive_dropped_with_warning():
    rewriter = _ReportLabelRewriter(FakeIndex())
    line, whole_block = rewriter.handle_workflow_display("workflow_display(workflow_id=abc123)\n", object(), None)
    assert line == ""
    assert whole_block is True
    assert "cannot be expressed" in rewriter.warnings[0]


def test_idless_directive_passthrough():
    rewriter = _ReportLabelRewriter(FakeIndex())
    line, whole_block = rewriter.handle_generate_time("generate_time()\n", None)
    assert line == "generate_time()\n"
    assert whole_block is False
    assert rewriter.warnings == []


# --- label index resolution -------------------------------------------------


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


def _content_stub(id_, copied_from=None):
    return SimpleNamespace(id=id_, copied_from_history_dataset_association=copied_from)


def test_index_input_resolves_to_input_label():
    step = _input_step("my_input")
    index = ExtractionLabelIndex(content_to_step={("dataset", 11): (step, "output")}, job_to_step={}, icj_to_step={})
    assert index.content_label_arg("hda", _content_stub(11)) == 'input="my_input"'


def test_index_tool_output_resolves_to_output_label():
    step = _tool_step()
    step.create_or_update_workflow_output(output_name="out_file", label="aligned", uuid=None)
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    assert index.content_label_arg("hda", _content_stub(12)) == 'output="aligned"'


def test_index_tool_output_without_label_is_unresolved():
    step = _tool_step()
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    assert index.content_label_arg("hda", _content_stub(12)) is None


def test_index_normalizes_copied_dataset_to_original():
    step = _tool_step()
    step.create_or_update_workflow_output(output_name="out_file", label="aligned", uuid=None)
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    original = _content_stub(12)
    copy = _content_stub(99, copied_from=original)
    assert index.content_label_arg("hda", copy) == 'output="aligned"'


def test_index_plain_job_resolves_to_step_label():
    step = _tool_step("bwa_mem")
    index = ExtractionLabelIndex(content_to_step={}, job_to_step={9: step}, icj_to_step={})
    job = SimpleNamespace(id=9, implicit_collection_jobs_association=None)
    assert index.job_label_arg(job) == 'step="bwa_mem"'


def test_index_mapped_job_folds_to_icj_step_label():
    step = _tool_step("mapped_step")
    index = ExtractionLabelIndex(content_to_step={}, job_to_step={}, icj_to_step={4: step})
    job = SimpleNamespace(id=9, implicit_collection_jobs_association=SimpleNamespace(implicit_collection_jobs_id=4))
    assert index.job_label_arg(job) == 'step="mapped_step"'


# --- reconcile --------------------------------------------------------------


def _referenced(refs=None, job_refs=None, icj_refs=None):
    return SimpleNamespace(refs=refs or [], job_refs=job_refs or [], icj_refs=icj_refs or [], warnings=[])


def _patch_resolution(monkeypatch, contents, suggested):
    monkeypatch.setattr(report, "_resolve_content", lambda trans, kind, content_id: contents.get((kind, content_id)))
    monkeypatch.setattr(
        report, "suggested_output_name", lambda trans, content_id, kind: SimpleNamespace(name=suggested)
    )


def test_reconcile_exposes_unstarred_output(monkeypatch):
    step = _tool_step()
    index = ExtractionLabelIndex(content_to_step={("dataset", 12): (step, "out_file")}, job_to_step={}, icj_to_step={})
    _patch_resolution(monkeypatch, {("hda", 12): _content_stub(12)}, "aligned_reads")
    report.reconcile_report_labels(None, index, _referenced(refs=[("hda", 12)]))
    workflow_output = step.workflow_output_for("out_file")
    assert workflow_output is not None
    assert workflow_output.label == "aligned_reads"


def test_reconcile_labels_unnamed_input(monkeypatch):
    step = _input_step(None)
    index = ExtractionLabelIndex(content_to_step={("dataset", 11): (step, "output")}, job_to_step={}, icj_to_step={})
    _patch_resolution(monkeypatch, {("hda", 11): _content_stub(11)}, "raw_input")
    report.reconcile_report_labels(None, index, _referenced(refs=[("hda", 11)]))
    assert step.label == "raw_input"


def test_reconcile_dedupes_against_existing_label(monkeypatch):
    starred = _input_step("aligned_reads")
    unstarred = _tool_step()
    index = ExtractionLabelIndex(
        content_to_step={("dataset", 10): (starred, "output"), ("dataset", 12): (unstarred, "out_file")},
        job_to_step={},
        icj_to_step={},
    )
    _patch_resolution(monkeypatch, {("hda", 12): _content_stub(12)}, "aligned_reads")
    report.reconcile_report_labels(None, index, _referenced(refs=[("hda", 12)]))
    assert unstarred.workflow_output_for("out_file").label == "aligned_reads_2"


def test_reconcile_labels_referenced_step(monkeypatch):
    step = _tool_step()
    step.tool_id = "toolshed.g2.bx.psu.edu/repos/iuc/bwa/bwa_mem/0.7"
    index = ExtractionLabelIndex(content_to_step={}, job_to_step={9: step}, icj_to_step={})
    report.reconcile_report_labels(None, index, _referenced(job_refs=[9]))
    assert step.label == "bwa_mem"
