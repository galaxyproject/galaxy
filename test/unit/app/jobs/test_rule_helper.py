import uuid

from galaxy import model
from galaxy.jobs.rule_helper import RuleHelper
from galaxy.model import mapping
from galaxy.util import bunch

USER_EMAIL_1 = "u1@example.com"
USER_EMAIL_2 = "u2@example.com"
USER_EMAIL_3 = "u3@example.com"


def test_job_count():
    rule_helper = __rule_helper()
    __assert_job_count_is(0, rule_helper)

    __setup_fixtures(rule_helper.app)

    # Test raw counts for users...
    __assert_job_count_is(7, rule_helper, for_user_email=USER_EMAIL_1)
    __assert_job_count_is(2, rule_helper, for_user_email=USER_EMAIL_2)
    __assert_job_count_is(0, rule_helper, for_user_email=USER_EMAIL_3)

    # Test desitnation counts
    __assert_job_count_is(2, rule_helper, for_destination="local")
    __assert_job_count_is(7, rule_helper, for_destination="cluster1")

    __assert_job_count_is(9, rule_helper, for_destinations=["cluster1", "local"])

    # Test per user destination counts
    __assert_job_count_is(5, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1)
    __assert_job_count_is(2, rule_helper, for_destination="local", for_user_email=USER_EMAIL_1)
    __assert_job_count_is(7, rule_helper, for_destinations=["cluster1", "local"], for_user_email=USER_EMAIL_1)

    __assert_job_count_is(2, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_2)
    __assert_job_count_is(0, rule_helper, for_destination="local", for_user_email=USER_EMAIL_2)

    # Test per user, per state destination counts
    __assert_job_count_is(
        3, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1, for_job_states=["queued"]
    )
    __assert_job_count_is(
        2, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1, for_job_states=["running"]
    )
    __assert_job_count_is(
        0, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1, for_job_states=["error"]
    )
    __assert_job_count_is(
        5,
        rule_helper,
        for_destination="cluster1",
        for_user_email=USER_EMAIL_1,
        for_job_states=["queued", "running", "error"],
    )


def __assert_job_count_is(expected_count, rule_helper, **kwds):
    acutal_count = rule_helper.job_count(**kwds)

    if expected_count != acutal_count:
        template = "Expected job count %d, actual job count %s for params %s"
        raise AssertionError(template % (expected_count, acutal_count, kwds))


def __setup_fixtures(app):
    # user1 has 3 jobs queued and 2 jobs running on cluster1 and one queued and
    # on running job on local. user2 has a queued and running job on the cluster.
    # user3 has no jobs.
    user1 = model.User(email=USER_EMAIL_1, password="pass1")
    user2 = model.User(email=USER_EMAIL_2, password="pass2")
    user3 = model.User(email=USER_EMAIL_2, password="pass2")

    app.add(user1, user2, user3)

    app.add(__new_job(user=user1, destination_id="cluster1", state="queued"))
    app.add(__new_job(user=user1, destination_id="cluster1", state="queued"))
    app.add(__new_job(user=user1, destination_id="cluster1", state="queued"))
    app.add(__new_job(user=user1, destination_id="cluster1", state="running"))
    app.add(__new_job(user=user1, destination_id="cluster1", state="running"))

    app.add(__new_job(user=user1, destination_id="local", state="queued"))
    app.add(__new_job(user=user1, destination_id="local", state="running"))

    app.add(__new_job(user=user2, destination_id="cluster1", state="queued"))
    app.add(__new_job(user=user2, destination_id="cluster1", state="running"))


def test_choose_one_unhashed():
    rule_helper = __rule_helper()

    # Random choices if hash not set.
    chosen_ones = set()
    __do_a_bunch(lambda: chosen_ones.add(rule_helper.choose_one(["a", "b"])))

    assert chosen_ones == {"a", "b"}


def test_choose_one_hashed():
    rule_helper = __rule_helper()

    # Hashed, so all choosen ones should be the same...
    chosen_ones = set()
    __do_a_bunch(lambda: chosen_ones.add(rule_helper.choose_one(["a", "b"], hash_value=1234)))
    assert len(chosen_ones) == 1

    # ... also can verify hashing on strings
    chosen_ones = set()
    __do_a_bunch(lambda: chosen_ones.add(rule_helper.choose_one(["a", "b"], hash_value="i am a string")))

    assert len(chosen_ones) == 1


def test_job_hash_unique_by_default():
    rule_helper = __rule_helper()
    job1, job2 = __two_jobs_in_a_history()

    assert rule_helper.job_hash(job1) != rule_helper.job_hash(job2)


def test_job_hash_history():
    rule_helper = __rule_helper()
    job1, job2 = __two_jobs_in_a_history()

    __assert_same_hash(rule_helper, job1, job2, hash_by="history")


def test_job_hash_workflow_invocation():
    rule_helper = __rule_helper()
    job1, job2 = __two_jobs()
    wi_uuid = uuid.uuid1().hex

    job1.add_parameter("__workflow_invocation_uuid__", wi_uuid)
    job2.add_parameter("__workflow_invocation_uuid__", wi_uuid)

    __assert_same_hash(rule_helper, job1, job2, hash_by="workflow_invocation")


def test_job_hash_fallback():
    rule_helper = __rule_helper()
    job1, job2 = __two_jobs_in_a_history()

    __assert_same_hash(rule_helper, job1, job2, hash_by="workflow_invocation,history")


def test_should_burst():
    rule_helper = __rule_helper()
    __setup_fixtures(rule_helper.app)
    # cluster1 fixture has 4 queued jobs, 3 running
    assert rule_helper.should_burst(["cluster1"], "7")
    assert not rule_helper.should_burst(["cluster1"], "10")

    assert rule_helper.should_burst(["cluster1"], "2", job_states="queued")
    assert not rule_helper.should_burst(["cluster1"], "6", job_states="queued")


def __assert_same_hash(rule_helper, job1, job2, hash_by):
    job1_hash = rule_helper.job_hash(job1, hash_by=hash_by)
    job2_hash = rule_helper.job_hash(job2, hash_by=hash_by)
    assert job1_hash == job2_hash


def __two_jobs_in_a_history():
    job1, job2 = __two_jobs()
    job1.history_id = 4
    job2.history_id = 4
    return job1, job2


def __two_jobs():
    job1 = model.Job()
    job1.id = 1
    job2 = model.Job()
    job2.id = 2
    return job1, job2


def __do_a_bunch(work):
    for _ in range(20):
        work()


def __new_job(**kwds):
    job = model.Job()
    for key, value in kwds.items():
        setattr(job, key, value)
    return job


def __rule_helper():
    app = MockApp()
    rule_helper = RuleHelper(app)
    return rule_helper


class MockApp:
    def __init__(self):
        self.config = bunch.Bunch()
        self.model = mapping.init("/tmp", "sqlite:///:memory:", create_tables=True)

    def add(self, *args):
        for arg in args:
            self.model.context.add(arg)
        self.model.context.flush()
