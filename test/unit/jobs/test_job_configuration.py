import datetime
import os
import shutil
import tempfile
import unittest

from galaxy.jobs import JobConfiguration
from galaxy.util import bunch

# File would be slightly more readable if contents were embedded directly, but
# there are advantages to testing the documentation/examples.
SIMPLE_JOB_CONF = os.path.join( os.path.dirname( __file__ ), "..", "..", "..", "config", "job_conf.xml.sample_basic" )
ADVANCED_JOB_CONF = os.path.join( os.path.dirname( __file__ ), "..", "..", "..", "config", "job_conf.xml.sample_advanced" )


class JobConfXmlParserTestCase( unittest.TestCase ):

    def setUp( self ):
        self.temp_directory = tempfile.mkdtemp()
        self.config = bunch.Bunch(
            job_config_file=os.path.join( self.temp_directory, "job_conf.xml" ),
            use_tasked_jobs=False,
            job_resource_params_file="/tmp/fake_absent_path",
            config_dict={},
            default_job_resubmission_condition="",
        )
        self.__write_config_from( SIMPLE_JOB_CONF )
        self.app = bunch.Bunch( config=self.config, job_metrics=MockJobMetrics() )
        self.__job_configuration = None

    def tearDown( self ):
        shutil.rmtree( self.temp_directory )

    def test_load_simple_runner( self ):
        runner_plugin = self.job_config.runner_plugins[ 0 ]
        assert runner_plugin[ "id" ] == "local"
        assert runner_plugin[ "load" ] == "galaxy.jobs.runners.local:LocalJobRunner"
        assert runner_plugin[ "workers" ] == 4

    def test_tasks_disabled( self ):
        assert len( [ r for r in self.job_config.runner_plugins if r[ "id" ] == "tasks" ] ) == 0

    def test_configuration_of_tasks( self ):
        self.config.use_tasked_jobs = True
        self.config.local_task_queue_workers = 5
        task_runners = [ r for r in self.job_config.runner_plugins if r[ "id" ] == "tasks" ]
        assert len( task_runners ) == 1
        assert task_runners[ 0 ][ "workers" ] == 5

    def test_load_simple_handler( self ):
        main_handler = self.job_config.handlers[ "main" ]
        assert main_handler[ 0 ] == "main"

    def test_if_one_handler_implicit_default( self ):
        assert self.job_config.default_handler_id == "main"

    def test_explicit_handler_default( self ):
        self.__with_advanced_config()
        assert self.job_config.default_handler_id == "handlers"

    def test_handler_tag_parsing( self ):
        self.__with_advanced_config()
        assert "handler0" in self.job_config.handlers[ "handlers" ]
        assert "handler1" in self.job_config.handlers[ "handlers" ]

    def test_load_simple_destination( self ):
        local_dest = self.job_config.destinations[ "local" ][ 0 ]
        assert local_dest.id == "local"
        assert local_dest.runner == "local"

    def test_load_destination_params( self ):
        self.__with_advanced_config()
        pbs_dest = self.job_config.destinations[ "pbs_longjobs" ][ 0 ]
        assert pbs_dest.id == "pbs_longjobs"
        assert pbs_dest.runner == "pbs"
        dest_params = pbs_dest.params
        assert dest_params[ "Resource_List" ] == "walltime=72:00:00"

    def test_destination_tags( self ):
        self.__with_advanced_config()
        longjob_dests = self.job_config.destinations[ "longjobs" ]
        assert len( longjob_dests ) == 2
        assert longjob_dests[ 0 ].id == "pbs_longjobs"
        assert longjob_dests[ 1 ].id == "remote_cluster"

    def test_load_tool( self ):
        self.__with_advanced_config()
        baz_tool = self.job_config.tools[ "baz" ][ 0 ]
        assert baz_tool.id == "baz"
        assert baz_tool.handler == "special_handlers"
        assert baz_tool.destination == "bigmem"

    def test_load_tool_params( self ):
        self.__with_advanced_config()
        foo_tool = self.job_config.tools[ "foo" ][ 0 ]
        assert foo_tool.params[ "source" ] == "trackster"

    def test_default_limits( self ):
        limits = self.job_config.limits
        assert limits.registered_user_concurrent_jobs is None
        assert limits.anonymous_user_concurrent_jobs is None
        assert limits.walltime is None
        assert limits.walltime_delta is None
        assert limits.total_walltime == {}
        assert limits.output_size is None
        assert limits.destination_user_concurrent_jobs == {}
        assert limits.destination_total_concurrent_jobs == {}

    def test_limit_overrides( self ):
        self.__with_advanced_config()
        limits = self.job_config.limits
        assert limits.registered_user_concurrent_jobs == 2
        assert limits.anonymous_user_concurrent_jobs == 1
        assert limits.destination_user_concurrent_jobs[ "local" ] == 1
        assert limits.destination_user_concurrent_jobs[ "mycluster" ] == 2
        assert limits.destination_user_concurrent_jobs[ "longjobs" ] == 1
        assert limits.walltime_delta == datetime.timedelta( 0, 0, 0, 0, 0, 24 )
        assert limits.total_walltime["delta"] == datetime.timedelta( 0, 0, 0, 0, 0, 24)
        assert limits.total_walltime["window"] == 30

    def test_env_parsing( self ):
        self.__with_advanced_config()
        env_dest = self.job_config.destinations[ "java_cluster" ][ 0 ]
        assert len( env_dest.env ) == 4, len( env_dest.env )
        assert env_dest.env[ 0 ][ "name" ] == "_JAVA_OPTIONS"
        assert env_dest.env[ 0 ][ "value" ] == '-Xmx6G'

        assert env_dest.env[ 1 ][ "name" ] == "ANOTHER_OPTION"
        assert env_dest.env[ 1 ][ "raw" ] is True

        assert env_dest.env[ 2 ][ "file" ] == "/mnt/java_cluster/environment_setup.sh"

        assert env_dest.env[ 3 ][ "execute" ] == "module load javastuff/2.10"

    def test_macro_expansion( self ):
        self.__with_advanced_config()
        for name in ["foo_small", "foo_medium", "foo_large", "foo_longrunning"]:
            assert self.job_config.destinations[ name ]

    # TODO: Add job metrics parsing test.

    @property
    def job_config( self ):
        if not self.__job_configuration:
            self.__job_configuration = JobConfiguration( self.app )
        return self.__job_configuration

    def __with_advanced_config( self ):
        self.__write_config_from( ADVANCED_JOB_CONF )

    def __write_config_from( self, path ):
        self.__write_config( open( path, "r" ).read() )

    def __write_config( self, contents ):
        with open( os.path.join( self.temp_directory, "job_conf.xml" ), "w" ) as f:
            f.write( contents )


class MockJobMetrics( object ):

    def __init__( self ):
        pass

    def set_destination_conf_element( self, id, element ):
        pass
