import os
import tempfile
from contextlib import contextmanager
from unittest import mock

from galaxy import model
from galaxy.managers.jobs import JobManager
from galaxy.managers.markdown_util import (
    ready_galaxy_markdown_for_export,
    to_basic_markdown,
)
from galaxy.model.orm.now import now
from .base import BaseTestCase


class BaseExportTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.app.hda_manager = mock.MagicMock()
        self.app.workflow_manager = mock.MagicMock()
        self.app.history_manager = mock.MagicMock()
        self.app.dataset_collection_manager = mock.MagicMock()

    def _new_history(self):
        history = model.History()
        history.id = 1
        history.name = "New History"
        return history

    def _new_hda(self, contents=None):
        hda = model.HistoryDatasetAssociation()
        hda.id = 1
        if contents is not None:
            hda.dataset = mock.MagicMock()
            hda.dataset.purged = False
            t = tempfile.NamedTemporaryFile(mode="w", delete=False)
            t.write(contents)
            hda.dataset.get_file_name.return_value = t.name
        return hda

    def _new_invocation(self):
        invocation = model.WorkflowInvocation()
        invocation.id = 1
        invocation.create_time = now()
        return invocation

    @contextmanager
    def _expect_get_history(self, history):
        self.app.history_manager.get_accessible.return_value = history
        yield
        self.app.history_manager.get_accessible.assert_called_once_with(history.id, self.trans.user)

    @contextmanager
    def _expect_get_hda(self, hda, hda_id=1):
        self.app.hda_manager.get_accessible.return_value = hda
        yield
        self.app.hda_manager.get_accessible.assert_called_once_with(hda.id, self.trans.user)

    def _new_pair_collection(self):
        hda_forward = self._new_hda(contents="Forward dataset.")
        hda_forward.id = 1
        hda_forward.extension = "txt"
        hda_reverse = self._new_hda(contents="Reverse dataset.")
        hda_reverse.id = 2
        hda_reverse.extension = "txt"

        collection = model.DatasetCollection()
        collection.id = 1
        element_forward = model.DatasetCollectionElement(
            collection=collection,
            element=hda_forward,
            element_index=0,
            element_identifier="forward",
        )
        element_forward.id = 1
        element_reverse = model.DatasetCollectionElement(
            collection=collection,
            element=hda_reverse,
            element_index=0,
            element_identifier="reverse",
        )
        element_reverse.id = 2
        collection.collection_type = "paired"
        return collection


class ToBasicMarkdownTestCase(BaseExportTestCase):
    def setUp(self):
        super().setUp()
        self.test_dataset_path = None

    def tearDown(self):
        super().tearDown()
        if self.test_dataset_path is not None:
            os.remove(self.test_dataset_path)

    def test_noop_on_non_galaxy_blocks(self):
        example = """# Example

## Some Syntax

*Foo* **bar** [Google](http://google.com/).

## Code Blocks

```
history_dataset_display(history_dataset_id=4)
```

Another kind of code block:

    job_metrics(job_id=4)

"""
        result = self._to_basic(example)
        assert result == example

    def test_history_dataset_peek(self):
        hda = self._new_hda()
        hda.peek = "My Cool Peek"
        example = """# Example
```galaxy
history_dataset_peek(history_dataset_id=1)
```
"""
        with self._expect_get_hda(hda):
            result = self._to_basic(example)
        assert "\n    My Cool Peek\n\n" in result

    def test_history_dataset_peek_empty(self):
        hda = self._new_hda()
        example = """# Example
```galaxy
history_dataset_peek(history_dataset_id=1)
```
"""
        with self._expect_get_hda(hda):
            result = self._to_basic(example)
        assert "\n*No Dataset Peek Available*\n" in result

    def test_history_link(self):
        history = self._new_history()
        example = """# Example
```galaxy
history_link(history_id=1)
```
"""
        with self._expect_get_history(history):
            result = self._to_basic(example)
        assert "\n    New History\n\n" in result

    def test_history_display_binary(self):
        hda = self._new_hda()
        hda.extension = "ab1"
        example = """# Example
```galaxy
history_dataset_display(history_dataset_id=1)
```
"""
        with self._expect_get_hda(hda):
            result = self._to_basic(example)
        assert "**Contents:**\n*cannot display binary content*\n" in result

    def test_history_display_text(self):
        hda = self._new_hda(contents="MooCow")
        hda.extension = "txt"
        example = """# Example
```galaxy
history_dataset_display(history_dataset_id=1)
```
"""
        with self._expect_get_hda(hda):
            result = self._to_basic(example)
        assert "**Contents:**\n\n    MooCow\n\n" in result

    def test_history_display_gtf(self):
        gtf = """chr13	Cufflinks	transcript	3405463	3405542	1000	.	.	gene_id "CUFF.50189"; transcript_id "CUFF.50189.1"; FPKM "6.3668918357"; frac "1.000000"; conf_lo "0.000000"; conf_hi "17.963819"; cov "0.406914";
chr13	Cufflinks	exon	3405463	3405542	1000	.	.	gene_id "CUFF.50189"; transcript_id "CUFF.50189.1"; exon_number "1"; FPKM "6.3668918357"; frac "1.000000"; conf_lo "0.000000"; conf_hi "17.963819"; cov "0.406914";
chr13	Cufflinks	transcript	3473337	3473372	1000	.	.	gene_id "CUFF.50191"; transcript_id "CUFF.50191.1"; FPKM "11.7350749444"; frac "1.000000"; conf_lo "0.000000"; conf_hi "35.205225"; cov "0.750000";
"""
        example = """# Example
```galaxy
history_dataset_display(history_dataset_id=1)
```
"""
        hda = self._new_hda(contents=gtf)
        hda.extension = "gtf"
        from galaxy.datatypes.tabular import Tabular

        assert isinstance(hda.datatype, Tabular)
        with self._expect_get_hda(hda):
            result = self._to_basic(example)
        assert "<table" in result

    def test_dataset_name(self):
        hda = self._new_hda()
        hda.name = "cool name"
        example = """# Example
```galaxy
history_dataset_name(history_dataset_id=1)
```
"""
        with self._expect_get_hda(hda):
            result = self._to_basic(example)
        assert "\n    cool name" in result

    def test_dataset_extension(self):
        hda = self._new_hda()
        hda.extension = "gtf"
        example = """# Example
```galaxy
history_dataset_type(history_dataset_id=1)
```
"""
        with self._expect_get_hda(hda):
            result = self._to_basic(example)
        assert "\n    gtf" in result

    def test_history_collection_paired(self):
        hdca = model.HistoryDatasetCollectionAssociation()
        hdca.name = "cool name"
        hdca.collection = self._new_pair_collection()
        hdca.id = 1

        self.trans.app.dataset_collection_manager.get_dataset_collection_instance.return_value = hdca
        example = """# Example
```galaxy
history_dataset_collection_display(history_dataset_collection_id=1)
```
"""
        result = self._to_basic(example)
        assert "**Dataset Collection:** cool name\n" in result
        assert "**Element:** forward" in result, result
        assert "**Element Contents:**\n" in result
        assert "\n    Forward dataset.\n" in result
        assert "**Element:** reverse" in result, result
        assert "\n    Reverse dataset.\n" in result

    def test_workflow_export(self):
        stored_workflow = model.StoredWorkflow()
        stored_workflow.name = "My Cool Workflow"
        workflow = model.Workflow()
        stored_workflow.latest_workflow = workflow
        workflow_step_0 = model.WorkflowStep()
        workflow.steps = [workflow_step_0]
        self.trans.app.workflow_manager.get_stored_accessible_workflow.return_value = stored_workflow
        example = """# Example
```galaxy
workflow_display(workflow_id=1)
```
"""
        result = self._to_basic(example)
        assert "**Workflow:** My Cool Workflow\n" in result
        assert "**Steps:**\n" in result

    def test_galaxy_version(self):
        example = """# Example
```galaxy
generate_galaxy_version()
```
"""
        result = self._to_basic(example)
        assert "\n    19.09" in result

    def test_generate_time(self):
        example = """# Example
```galaxy
generate_time()
```
"""
        result = self._to_basic(example)
        assert "\n    20" in result

    def test_generate_invocation_time(self):
        example = """# Example
```galaxy
invocation_time(invocation_id=1)
```
"""
        invocation = self._new_invocation()
        self.app.workflow_manager.get_invocation.side_effect = [invocation]
        result = self._to_basic(example)
        assert "\n    %s" % invocation.create_time.isoformat() in result

    def test_job_parameters(self):
        job = model.Job()
        job.id = 1
        example = """# Example
```galaxy
job_parameters(job_id=1)
```
"""
        parameters = [
            {"text": "Num Lines", "value": "6", "depth": 1},
            {"text": "Plot", "value": "coolselect", "depth": 2},
            {"text": "Input Dataset", "value": [{"src": "hda", "hid": 5, "name": "Cool Data"}], "depth": 1},
        ]
        response = {"parameters": parameters}
        with mock.patch.object(JobManager, "get_accessible_job", return_value=job):
            with mock.patch("galaxy.managers.markdown_util.summarize_job_parameters", return_value=response):
                result = self._to_basic(example)
        assert "| Num Lines |" in result
        assert "| > Plot |" in result
        assert "| Input Dataset | " in result
        assert "| 5: Cool Data |\n" in result

    def test_job_metrics(self):
        job = model.Job()
        job.id = 1
        example = """# Example
```galaxy
job_metrics(job_id=1)
```
"""
        metrics = [
            {"plugin": "core", "title": "Cores Allocated", "value": 1},
            {"plugin": "core", "title": "Job Start Time", "value": "2019-12-17 11:53:13"},
            {"plugin": "env", "title": "GALAXY_HOME", "value": "/path/to/home"},
        ]
        with mock.patch.object(JobManager, "get_accessible_job", return_value=job):
            with mock.patch("galaxy.managers.markdown_util.summarize_job_metrics", return_value=metrics):
                result = self._to_basic(example)
        assert "**core**\n" in result
        assert "**env**\n" in result
        assert "| Cores Allocated | 1 |\n" in result
        assert "| GALAXY_HOME | /path/to/home |\n" in result

    def _to_basic(self, example):
        return to_basic_markdown(self.trans, example)


class ReadyExportTestCase(BaseExportTestCase):
    def test_ready_dataset_display(self):
        hda = self._new_hda()
        example = """
```galaxy
history_dataset_display(history_dataset_id=1)
```
"""
        with self._expect_get_hda(hda):
            export_markdown, extra_data = self._ready_export(example)
        assert "history_datasets" in extra_data
        assert len(extra_data["history_datasets"]) == 1

    def test_ready_export_two_datasets(self):
        hda = self._new_hda()
        hda2 = self._new_hda()
        hda2.id = 2
        example = """
```galaxy
history_dataset_display(history_dataset_id=1)
```

```galaxy
history_dataset_display(history_dataset_id=2)
```
"""
        self.app.hda_manager.get_accessible.side_effect = [hda, hda2]
        export_markdown, extra_data = self._ready_export(example)
        assert "history_datasets" in extra_data
        assert len(extra_data["history_datasets"]) == 2

    def test_export_dataset_collection_paired(self):
        hdca = model.HistoryDatasetCollectionAssociation()
        hdca.name = "cool name"
        hdca.collection = self._new_pair_collection()
        hdca.id = 1
        hdca.history_id = 1
        hdca.collection_id = hdca.collection.id

        self.trans.app.dataset_collection_manager.get_dataset_collection_instance.return_value = hdca
        example = """# Example
```galaxy
history_dataset_collection_display(history_dataset_collection_id=1)
```
"""
        # Patch out url_for since we haven't initialized an app.
        from galaxy.managers.hdcas import HDCASerializer

        with mock.patch.object(HDCASerializer, "url_for", return_value="http://google.com"):
            export, extra_data = self._ready_export(example)
        assert "history_dataset_collections" in extra_data
        assert len(extra_data.get("history_dataset_collections")) == 1

    def test_galaxy_version(self):
        example = """# Example
```galaxy
generate_galaxy_version()
```
"""
        result, extra_data = self._ready_export(example)
        assert "generate_version" in extra_data
        assert extra_data["generate_version"] == "19.09"

    def test_generate_time(self):
        example = """# Example
```galaxy
generate_time()
```
"""
        result, extra_data = self._ready_export(example)
        assert "generate_time" in extra_data

    def test_get_invocation_time(self):
        invocation = self._new_invocation()
        self.app.workflow_manager.get_invocation.side_effect = [invocation]
        example = """# Example
```galaxy
invocation_time(invocation_id=1)
```
"""
        result, extra_data = self._ready_export(example)
        assert "invocations" in extra_data
        assert "create_time" in extra_data["invocations"]["be8be0fd2ce547f6"]
        assert extra_data["invocations"]["be8be0fd2ce547f6"]["create_time"] == invocation.create_time.isoformat()

    def _ready_export(self, example):
        return ready_galaxy_markdown_for_export(self.trans, example)
