import os
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from galaxy import (
    job_metrics,
    model,
)
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.jobs import MinimalJobWrapper
from galaxy.model import store
from galaxy.util.hash_util import HashFunctionNameEnum
from galaxy.util.unittest import TestCase


class FixedJobMetrics(job_metrics.JobMetrics):
    def collect_properties(self, destination_id, job, job_directory):
        return {"core": {"runtime_seconds": 1}}


class TestJobWrapperFinish(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()
        self._init_tool()
        session = self.app.model.context
        user = model.User(email="finish@example.org", password="password")
        history = model.History(user=user)
        job = model.Job()
        job.user = user
        job.history = history
        job.tool_id = self.tool.id
        job.state = model.Job.states.RUNNING
        job.object_store_id = "default"
        dataset = model.Dataset(state=model.Dataset.states.RUNNING)
        hda = model.HistoryDatasetAssociation(history=history, extension="txt", dataset=dataset)
        job.add_output_dataset("out1", hda)
        session.add_all([user, history, job, hda])
        session.commit()
        self.app.object_store.create(dataset)
        with open(hda.get_file_name(), "w") as out:
            out.write("output\n")
        self.app.config.retry_job_output_collection = 0
        self.app.config.calculate_dataset_hash = "never"
        self.app.job_metrics = job_metrics.JobMetrics()
        self.job = job
        self.dataset = dataset

    def tearDown(self):
        self.tear_down_app()

    def test_outputs_and_final_job_state_are_committed_together(self):
        committed = self._finish_and_record_commits()

        assert committed[-1][:2] == (model.Job.states.OK, model.Dataset.states.OK)
        for job_state, dataset_state, _ in committed:
            if dataset_state == model.Dataset.states.OK:
                assert job_state == model.Job.states.OK

    def test_metrics_are_committed_with_final_job_state(self):
        self.app.job_metrics = FixedJobMetrics()
        committed = self._finish_and_record_commits()

        assert committed[-1] == (model.Job.states.OK, model.Dataset.states.OK, True)
        for job_state, _, has_metrics in committed:
            if job_state == model.Job.states.OK:
                assert has_metrics

    def test_hash_tasks_are_queued_after_outputs_are_committed(self):
        self.app.config.calculate_dataset_hash = "always"
        self.app.config.enable_celery_tasks = True
        self.app.config.hash_function = HashFunctionNameEnum.md5
        committed_when_queued = []
        with patch("galaxy.celery.tasks.compute_dataset_hash.delay") as delay:
            delay.side_effect = lambda request: committed_when_queued.append(list(self.committed))
            self._finish_and_record_commits()

        assert len(committed_when_queued) == 1
        assert (model.Job.states.OK, model.Dataset.states.OK) in [c[:2] for c in committed_when_queued[0]]

    def test_hash_queue_failure_keeps_committed_job_state(self):
        self.app.config.calculate_dataset_hash = "always"
        self.app.config.enable_celery_tasks = True
        self.app.config.hash_function = HashFunctionNameEnum.md5
        with patch("galaxy.celery.tasks.compute_dataset_hash.delay", side_effect=ConnectionError):
            committed = self._finish_and_record_commits()

        assert committed[-1][:2] == (model.Job.states.OK, model.Dataset.states.OK)
        assert self.job.state == model.Job.states.OK

    def test_update_time_failure_keeps_committed_job_state(self):
        with patch.object(model.Job, "touch_dependent_update_times", side_effect=OperationalError("", {}, Exception())):
            committed = self._finish_and_record_commits()

        assert committed[-1][:2] == (model.Job.states.OK, model.Dataset.states.OK)
        assert self.job.state == model.Job.states.OK

    def test_extended_metadata_outputs_and_final_job_state_are_committed_together(self):
        self.app.config.metadata_strategy = "extended"
        wrapper = MinimalJobWrapper(self.job, self.app, tool=self.tool)
        assert wrapper.external_output_metadata.extended
        self.dataset.state = model.Dataset.states.OK
        with store.DirectoryModelExportStore(
            os.path.join(wrapper.working_directory, "metadata", "outputs_populated"),
            serialize_dataset_objects=True,
            for_edit=True,
            strip_metadata_files=False,
            serialize_jobs=True,
        ) as export_store:
            export_store.add_dataset(self.job.output_datasets[0].dataset)
        self.app.model.context.rollback()

        committed = self._finish_and_record_commits(wrapper)

        assert committed[-1][:2] == (model.Job.states.OK, model.Dataset.states.OK)
        for job_state, dataset_state, _ in committed:
            if dataset_state == model.Dataset.states.OK:
                assert job_state == model.Job.states.OK

    def _finish_and_record_commits(self, wrapper=None):
        wrapper = wrapper or MinimalJobWrapper(self.job, self.app, tool=self.tool)
        session = self.app.model.context()
        committed = self.committed = []

        def record(_session):
            committed.append((self.job.state, self.dataset.state, bool(self.job.numeric_metrics)))

        event.listen(session, "before_commit", record)
        try:
            wrapper.finish("", "", tool_exit_code=0)
        finally:
            event.remove(session, "before_commit", record)
        return committed
