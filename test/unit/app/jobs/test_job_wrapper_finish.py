import os
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import (
    event,
    select,
)
from sqlalchemy.exc import OperationalError

from galaxy import (
    job_metrics,
    model,
)
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.jobs import MinimalJobWrapper
from galaxy.model import store
from galaxy.model.metadata import MetadataTempFilePathError
from galaxy.util.hash_util import HashFunctionNameEnum
from galaxy.util.unittest import TestCase

OLD_UPDATE_TIME = datetime(2020, 1, 1)


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
            assert (job_state == model.Job.states.OK) == (dataset_state == model.Dataset.states.OK)

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

    def test_collection_update_time_is_bumped(self):
        hdca = self._add_output_collection()

        self._finish_and_record_commits()

        self.app.model.context.refresh(hdca)
        assert hdca.update_time > OLD_UPDATE_TIME

    def test_collection_update_time_is_committed_with_final_job_state(self):
        # The history's update_time follows its collections, so a client that sees the finished
        # job must also see the history's final update_time.
        hdca = self._add_output_collection()
        session = self.app.model.context()
        hdca_table = model.HistoryDatasetCollectionAssociation.table
        hdca_update_times = []

        def record(_session):
            if self.job.state == model.Job.states.OK:
                update_time = session.scalar(select(hdca_table.c.update_time).where(hdca_table.c.id == hdca.id))
                hdca_update_times.append(update_time)

        event.listen(session, "before_commit", record)
        try:
            self._finish_and_record_commits()
        finally:
            event.remove(session, "before_commit", record)

        assert hdca_update_times[0] > OLD_UPDATE_TIME

    def test_update_time_failure_keeps_committed_job_state(self):
        with patch.object(
            model.Job, "touch_invocation_steps_update_time", side_effect=OperationalError("", {}, Exception())
        ):
            committed = self._finish_and_record_commits()

        assert committed[-1][:2] == (model.Job.states.OK, model.Dataset.states.OK)
        assert self.job.state == model.Job.states.OK

    def test_metadata_temp_file_outside_metadata_directory_fails_metadata_only(self):
        wrapper = MinimalJobWrapper(self.job, self.app, tool=self.tool)
        metadata = wrapper.external_output_metadata
        with (
            patch.object(metadata, "external_metadata_set_successfully", return_value=True),
            patch.object(metadata, "load_metadata", side_effect=MetadataTempFilePathError("/etc/passwd")),
        ):
            self._finish_and_record_commits(wrapper)

        assert self.job.state == model.Job.states.OK
        assert self.job.output_datasets[0].dataset.state == model.HistoryDatasetAssociation.states.FAILED_METADATA

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
            assert (job_state == model.Job.states.OK) == (dataset_state == model.Dataset.states.OK)

    def test_invalid_validated_output_is_errored_and_pauses_dependents(self):
        self.app.config.fail_invalid_validated_outputs = True
        dependent_job = self._add_dependent_job()

        self._finish_with_validated_state(model.DatasetInstance.validated_states.INVALID, "File is truncated.")

        hda = self.job.output_datasets[0].dataset
        assert self.job.state == model.Job.states.OK
        assert self.dataset.state == model.Dataset.states.ERROR
        assert "File is truncated." in hda.info
        assert dependent_job.state == model.Job.states.PAUSED

    def test_invalid_validated_output_stays_ok_by_default(self):
        dependent_job = self._add_dependent_job()

        self._finish_with_validated_state(model.DatasetInstance.validated_states.INVALID, "File is truncated.")

        assert self.job.output_datasets[0].dataset.validated_state == model.DatasetInstance.validated_states.INVALID
        assert self.dataset.state == model.Dataset.states.OK
        assert dependent_job.state == model.Job.states.NEW

    def test_valid_validated_output_stays_ok(self):
        self.app.config.fail_invalid_validated_outputs = True

        self._finish_with_validated_state(model.DatasetInstance.validated_states.OK, None)

        assert self.dataset.state == model.Dataset.states.OK

    def _add_dependent_job(self):
        session = self.app.model.context
        dependent_job = model.Job()
        dependent_job.user = self.job.user
        dependent_job.history = self.job.history
        dependent_job.tool_id = self.tool.id
        dependent_job.state = model.Job.states.NEW
        dependent_job.add_input_dataset("input1", self.job.output_datasets[0].dataset)
        session.add(dependent_job)
        session.commit()
        return dependent_job

    def _finish_with_validated_state(self, validated_state, message):
        wrapper = MinimalJobWrapper(self.job, self.app, tool=self.tool)
        metadata = wrapper.external_output_metadata

        def load_metadata(dataset, *args, **kwds):
            dataset.validated_state = validated_state
            dataset.validated_state_message = message

        with (
            patch.object(metadata, "external_metadata_set_successfully", return_value=True),
            patch.object(metadata, "load_metadata", side_effect=load_metadata),
        ):
            self._finish_and_record_commits(wrapper)

    def _add_output_collection(self):
        session = self.app.model.context
        hdca = model.HistoryDatasetCollectionAssociation(
            history=self.job.history, collection=model.DatasetCollection(collection_type="list"), job=self.job
        )
        session.add(hdca)
        session.commit()
        hdca.update_time = OLD_UPDATE_TIME
        session.commit()
        return hdca

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
