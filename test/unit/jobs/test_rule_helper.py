from galaxy.util import bunch
from galaxy import model
from galaxy.model import mapping

from galaxy.jobs.rule_helper import RuleHelper

USER_EMAIL_1 = "u1@example.com"
USER_EMAIL_2 = "u2@example.com"
USER_EMAIL_3 = "u3@example.com"


def test_job_count():
    rule_helper = __rule_helper()
    __assert_job_count_is( 0, rule_helper )

    __setup_fixtures( rule_helper.app )

    # Test raw counts for users...
    __assert_job_count_is( 7, rule_helper, for_user_email=USER_EMAIL_1 )
    __assert_job_count_is( 2, rule_helper, for_user_email=USER_EMAIL_2 )
    __assert_job_count_is( 0, rule_helper, for_user_email=USER_EMAIL_3 )

    # Test desitnation counts
    __assert_job_count_is( 2, rule_helper, for_destination="local" )
    __assert_job_count_is( 7, rule_helper, for_destination="cluster1" )

    __assert_job_count_is( 9, rule_helper, for_destinations=["cluster1", "local"] )

    # Test per user destination counts
    __assert_job_count_is( 5, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1 )
    __assert_job_count_is( 2, rule_helper, for_destination="local", for_user_email=USER_EMAIL_1 )
    __assert_job_count_is( 7, rule_helper, for_destinations=["cluster1", "local"], for_user_email=USER_EMAIL_1 )

    __assert_job_count_is( 2, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_2 )
    __assert_job_count_is( 0, rule_helper, for_destination="local", for_user_email=USER_EMAIL_2 )

    # Test per user, per state destination counts
    __assert_job_count_is( 3, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1, for_job_states=[ "queued" ] )
    __assert_job_count_is( 2, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1, for_job_states=[ "running" ] )
    __assert_job_count_is( 0, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1, for_job_states=[ "error" ] )
    __assert_job_count_is( 5, rule_helper, for_destination="cluster1", for_user_email=USER_EMAIL_1, for_job_states=[ "queued", "running", "error" ] )


def __assert_job_count_is( expected_count, rule_helper, **kwds ):
    acutal_count = rule_helper.job_count( **kwds )

    if expected_count != acutal_count:
        template = "Expected job count %d, actual job count %s for params %s"
        raise AssertionError( template % ( expected_count, acutal_count, kwds ) )


def __setup_fixtures( app ):
    # user1 has 3 jobs queued and 2 jobs running on cluster1 and one queued and
    # on running job on local. user2 has a queued and running job on the cluster.
    # user3 has no jobs.
    user1 = model.User( email=USER_EMAIL_1, password="pass1" )
    user2 = model.User( email=USER_EMAIL_2, password="pass2" )
    user3 = model.User( email=USER_EMAIL_2, password="pass2" )

    app.add( user1, user2, user3 )

    app.add( __new_job( user=user1, destination_id="cluster1", state="queued" ) )
    app.add( __new_job( user=user1, destination_id="cluster1", state="queued" ) )
    app.add( __new_job( user=user1, destination_id="cluster1", state="queued" ) )
    app.add( __new_job( user=user1, destination_id="cluster1", state="running" ) )
    app.add( __new_job( user=user1, destination_id="cluster1", state="running" ) )

    app.add( __new_job( user=user1, destination_id="local", state="queued" ) )
    app.add( __new_job( user=user1, destination_id="local", state="running" ) )

    app.add( __new_job( user=user2, destination_id="cluster1", state="queued" ) )
    app.add( __new_job( user=user2, destination_id="cluster1", state="running" ) )


def __rule_helper():
    app = MockApp()
    rule_helper = RuleHelper( app )
    return rule_helper


def __new_job( **kwds ):
    job = model.Job()
    for key, value in kwds.items():
        setattr( job, key, value )
    return job


class MockApp( object ):

    def __init__( self ):
        self.config = bunch.Bunch( )
        self.model = mapping.init(
            "/tmp",
            "sqlite:///:memory:",
            create_tables=True
        )

    def add( self, *args ):
        for arg in args:
            self.model.context.add( arg )
        self.model.context.flush()
