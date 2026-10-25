from unittest.mock import patch

from sqlalchemy import event

from galaxy import (
    job_metrics,
    model,
)
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.jobs import MinimalJobWrapper
from galaxy.util.unittest import TestCase


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
        with patch.object(self.app.job_metrics, "collect_properties", return_value={"core": {"runtime_seconds": 1}}):
            committed = self._finish_and_record_commits()

        assert committed[-1] == (model.Job.states.OK, model.Dataset.states.OK, True)
        for job_state, _, has_metrics in committed:
            if job_state == model.Job.states.OK:
                assert has_metrics

    def _finish_and_record_commits(self):
        session = self.app.model.context()
        committed = []

        def record(_session):
            committed.append((self.job.state, self.dataset.state, bool(self.job.numeric_metrics)))

        event.listen(session, "before_commit", record)
        try:
            wrapper = MinimalJobWrapper(self.job, self.app, tool=self.tool)
            wrapper.finish("", "", tool_exit_code=0)
        finally:
            event.remove(session, "before_commit", record)
        return committed
