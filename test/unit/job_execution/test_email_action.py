"""EmailAction sends one email for a whole map-over, once all its jobs have settled.

The end-to-end emails are covered by ``test/integration/test_completion_notifications.py``.
"""

import pytest

from galaxy import model
from galaxy.job_execution.actions.post import ActionBox
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.util.unittest_utils import read_mock_emails


@pytest.fixture
def email_dir(tmp_path):
    return tmp_path


@pytest.fixture
def app(email_dir) -> GalaxyDataTestApp:
    return GalaxyDataTestApp(
        email_from="galaxy@example.org",
        galaxy_infrastructure_url="https://galaxy.example.org",
        smtp_server=f"mock_emails_to_path://{email_dir}",
        enable_notification_system=False,
    )


@pytest.fixture
def history(app) -> model.History:
    user = model.User(email="user@example.org", password="password")
    history = model.History(name="Analysis", user=user)
    app.model.session.add(history)
    return history


def make_job(app, history, state) -> model.Job:
    job = model.Job()
    job.user = history.user
    job.history = history
    job.state = state
    job.add_post_job_action(model.PostJobAction("EmailAction"))
    app.model.session.add(job)
    return job


def make_map_over(app, history, job_states, populated_state="ok") -> list[model.Job]:
    """Jobs of one map-over that populates the collection 'trimmed reads'."""
    implicit_collection_jobs = model.ImplicitCollectionJobs(populated_state=populated_state)
    hdca = model.HistoryDatasetCollectionAssociation(name="trimmed reads", hid=1, history=history)
    hdca.implicit_collection_jobs = implicit_collection_jobs
    app.model.session.add(hdca)
    jobs = []
    for order_index, state in enumerate(job_states):
        job = make_job(app, history, state)
        job.add_output_dataset_collection("output", hdca)
        job_assoc = model.ImplicitCollectionJobsJobAssociation()
        job_assoc.order_index = order_index
        job_assoc.implicit_collection_jobs = implicit_collection_jobs
        job_assoc.job = job
        app.model.session.add(job_assoc)
        jobs.append(job)
    app.model.session.commit()
    return jobs


def run_email_actions(app, *jobs):
    ActionBox.execute_after_commit(app, app.model.session, jobs)


def test_paused_job_not_mapped_over_sends_nothing(app, history, email_dir):
    job = make_job(app, history, model.Job.states.PAUSED)
    app.model.session.commit()

    run_email_actions(app, job)
    sent_emails = read_mock_emails(email_dir)

    assert sent_emails == []


@pytest.mark.parametrize(
    "populated_state, job_states, expected_completion",
    [
        pytest.param(
            "ok",
            [model.Job.states.OK, model.Job.states.ERROR, model.Job.states.OK],
            "Your 3 Galaxy jobs generating collection(s):\n\ntrimmed reads\n\nare complete (1 error, 2 ok)",
            id="all_jobs_finished",
        ),
        pytest.param(
            "ok",
            [model.Job.states.OK, model.Job.states.PAUSED, model.Job.states.OK],
            "Your 3 Galaxy jobs generating collection(s):\n\ntrimmed reads\n\nare complete (2 ok, 1 paused)",
            id="a_job_paused",
        ),
        pytest.param(
            "failed",
            [model.Job.states.OK, model.Job.states.OK],
            "Your 2 Galaxy jobs generating collection(s):\n\ntrimmed reads\n\nare complete (2 ok)",
            id="some_jobs_could_not_be_created",
        ),
        pytest.param(
            "ok",
            [model.Job.states.OK],
            "Your 1 Galaxy job generating collection(s):\n\ntrimmed reads\n\nis complete (1 ok)",
            id="single_job",
        ),
    ],
)
def test_settled_map_over_sends_one_summary_email(
    app, history, email_dir, populated_state, job_states, expected_completion
):
    *_, last_job = make_map_over(app, history, job_states, populated_state)

    run_email_actions(app, last_job)
    sent_emails = read_mock_emails(email_dir)

    assert len(sent_emails) == 1
    assert sent_emails[0]["body"].startswith(f"{expected_completion} as of ")


@pytest.mark.parametrize(
    "populated_state, job_states",
    [
        pytest.param(
            "ok", [model.Job.states.OK, model.Job.states.RUNNING, model.Job.states.OK], id="a_job_still_running"
        ),
        pytest.param(
            "ok", [model.Job.states.OK, model.Job.states.QUEUED, model.Job.states.OK], id="a_job_still_queued"
        ),
        pytest.param("new", [model.Job.states.OK, model.Job.states.OK], id="more_jobs_still_to_be_created"),
        pytest.param("ok", [model.Job.states.OK, model.Job.states.DELETED], id="last_job_cancelled"),
    ],
)
def test_mapped_over_job_sends_no_summary(app, history, email_dir, populated_state, job_states):
    *_, last_job = make_map_over(app, history, job_states, populated_state)

    run_email_actions(app, last_job)
    sent_emails = read_mock_emails(email_dir)

    assert sent_emails == []


def test_map_over_settled_by_several_jobs_at_once_sends_one_email(app, history, email_dir):
    jobs = make_map_over(app, history, [model.Job.states.PAUSED, model.Job.states.PAUSED])

    run_email_actions(app, *jobs)
    sent_emails = read_mock_emails(email_dir)

    assert len(sent_emails) == 1


def test_map_over_job_without_email_action_does_not_hide_the_summary(app, history, email_dir):
    job_without_email, job_with_email = make_map_over(app, history, [model.Job.states.OK, model.Job.states.OK])
    app.model.session.delete(job_without_email.post_job_actions[0])
    app.model.session.commit()

    run_email_actions(app, job_without_email, job_with_email)
    sent_emails = read_mock_emails(email_dir)

    assert len(sent_emails) == 1
