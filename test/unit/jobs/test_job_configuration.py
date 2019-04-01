import datetime
import os
import shutil
import tempfile
import unittest

import mock

from galaxy.jobs import JobConfiguration
from galaxy.util import bunch
from galaxy.web.stack import ApplicationStack, UWSGIApplicationStack

# File would be slightly more readable if contents were embedded directly, but
# there are advantages to testing the documentation/examples.
SIMPLE_JOB_CONF = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "job_conf.xml.sample_basic")
ADVANCED_JOB_CONF = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "job_conf.xml.sample_advanced")
CONDITIONAL_RUNNER_JOB_CONF = os.path.join(os.path.dirname(__file__), "conditional_runners_job_conf.xml")
HANDLER_TEMPLATE_JOB_CONF = os.path.join(os.path.dirname(__file__), "handler_template_job_conf.xml")


class JobConfXmlParserTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.mkdtemp()
        self.config = bunch.Bunch(
            job_config_file=os.path.join(self.temp_directory, "job_conf.xml"),
            use_tasked_jobs=False,
            job_resource_params_file="/tmp/fake_absent_path",
            config_dict={},
            default_job_resubmission_condition="",
            track_jobs_in_database=True,
            server_name="main",
        )
        self.__write_config_from(SIMPLE_JOB_CONF)
        self.__app = None
        self.__application_stack = None
        self.__job_configuration = None
        self.__job_configuration_base_pools = None
        self.__uwsgi_opt = None

    def tearDown(self):
        shutil.rmtree(self.temp_directory)

    def test_load_simple_runner(self):
        runner_plugin = self.job_config.runner_plugins[0]
        assert runner_plugin["id"] == "local"
        assert runner_plugin["load"] == "galaxy.jobs.runners.local:LocalJobRunner"
        assert runner_plugin["workers"] == 4

    def test_tasks_disabled(self):
        assert len([r for r in self.job_config.runner_plugins if r["id"] == "tasks"]) == 0

    def test_configuration_of_tasks(self):
        self.config.use_tasked_jobs = True
        self.config.local_task_queue_workers = 5
        task_runners = [r for r in self.job_config.runner_plugins if r["id"] == "tasks"]
        assert len(task_runners) == 1
        assert task_runners[0]["workers"] == 5

    def test_explicit_handler_default(self):
        self.__with_handlers_config(
            handlers=[{'id': 'handler0', 'tags': 'handlers'}, {'id': 'handler1', 'tags': 'handlers'}],
            default='handlers'
        )
        assert self.job_config.default_handler_id == "handlers"

    def test_handler_tag_parsing(self):
        self.__with_handlers_config(
            handlers=[{'id': 'handler0', 'tags': 'handlers'}, {'id': 'handler1', 'tags': 'handlers'}],
            default='handlers'
        )
        assert "handler0" in self.job_config.handlers["handlers"]
        assert "handler1" in self.job_config.handlers["handlers"]

    def test_implict_db_self_handler_assign(self):
        assert self.job_config.handler_assignment_methods == ['db-self']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}

    def test_implicit_db_assign_handler_assign_with_explicit_handlers(self):
        self.__with_handlers_config(handlers=[{'id': 'handler0'}, {'id': 'handler1'}])
        assert self.job_config.handler_assignment_methods == ['db-preassign']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['handler0', 'handler1']

    def test_implict_uwsgi_mule_message_handler_assign(self):
        self.__with_uwsgi_application_stack(mule='lib/galaxy/main.py', farm='job-handlers:1')
        assert self.job_config.handler_assignment_methods == ['uwsgi-mule-message']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['main.job-handlers.1']

    def test_implict_uwsgi_mule_message_handler_assign_with_explicit_handlers(self):
        self.__with_handlers_config(handlers=[{'id': 'handler0'}, {'id': 'handler1'}])
        self.__with_uwsgi_application_stack(mule='lib/galaxy/main.py', farm='job-handlers:1')
        assert self.job_config.handler_assignment_methods == ['uwsgi-mule-message', 'db-preassign']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['handler0', 'handler1', 'main.job-handlers.1']

    def test_explicit_mem_self_handler_assign(self):
        self.__with_handlers_config(assign_with='mem-self')
        assert self.job_config.handler_assignment_methods == ['mem-self']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}
        assert not self.config.track_jobs_in_database

    def test_explicit_mem_self_handler_assign_with_handlers(self):
        self.__with_handlers_config(assign_with='mem-self', handlers=[{'id': 'handler0'}])
        assert self.job_config.handler_assignment_methods == ['mem-self']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['handler0']

    def test_explicit_db_preassign_handler_assign_with_uwsgi(self):
        self.__with_handlers_config(assign_with='db-preassign', handlers=[{'id': 'handler0'}])
        self.__with_uwsgi_application_stack(mule='lib/galaxy/main.py', farm='job-handlers:1')
        assert self.job_config.handler_assignment_methods == ['db-preassign']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['handler0', 'main.job-handlers.1']

    def test_explicit_db_transaction_isolation_handler_assign(self):
        self.__with_handlers_config(assign_with='db-transaction-isolation')
        assert self.job_config.handler_assignment_methods == ['db-transaction-isolation']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}

    def test_explicit_db_transaction_isolation_handler_assign_with_uwsgi(self):
        self.__with_handlers_config(assign_with='db-transaction-isolation', handlers=[{'id': 'handler0'}])
        self.__with_uwsgi_application_stack(mule='lib/galaxy/main.py', farm='job-handlers:1')
        assert self.job_config.handler_assignment_methods == ['db-transaction-isolation']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['handler0', 'main.job-handlers.1']

    def test_explicit_db_skip_locked_handler_assign(self):
        self.__with_handlers_config(assign_with='db-skip-locked')
        assert self.job_config.handler_assignment_methods == ['db-skip-locked']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}

    def test_explicit_db_skip_locked_handler_assign_with_uwsgi(self):
        self.__with_handlers_config(assign_with='db-skip-locked', handlers=[{'id': 'handler0'}])
        self.__with_uwsgi_application_stack(mule='lib/galaxy/main.py', farm='job-handlers:1')
        assert self.job_config.handler_assignment_methods == ['db-skip-locked']
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['handler0', 'main.job-handlers.1']

    def test_uwsgi_farms_as_handler_tags(self):
        self.__with_uwsgi_application_stack(
            mule=['lib/galaxy/main.py'] * 2,
            farm=['job-handlers:1', 'job-handlers.foo:2']
        )
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['main.job-handlers.1']
        assert self.job_config.handlers['foo'] == ['main.job-handlers.foo.1']

    def test_uwsgi_overlapping_pools(self):
        self.__with_handlers_config(base_pools=('workflow-schedulers', 'job-handlers'))
        self.__with_uwsgi_application_stack(
            mule=['lib/galaxy/main.py'] * 3,
            farm=['job-handlers:1', 'workflow-schedulers:2', 'job-handlers.foo:3']
        )
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers['_default_'] == ['main.workflow-schedulers.1']
        assert self.job_config.handlers['foo'] == ['main.job-handlers.foo.1']

    def test_load_simple_destination(self):
        local_dest = self.job_config.destinations["local"][0]
        assert local_dest.id == "local"
        assert local_dest.runner == "local"

    def test_load_destination_params(self):
        self.__with_advanced_config()
        pbs_dest = self.job_config.destinations["pbs_longjobs"][0]
        assert pbs_dest.id == "pbs_longjobs"
        assert pbs_dest.runner == "pbs"
        dest_params = pbs_dest.params
        assert dest_params["Resource_List"] == "walltime=72:00:00"

    def test_destination_tags(self):
        self.__with_advanced_config()
        longjob_dests = self.job_config.destinations["longjobs"]
        assert len(longjob_dests) == 2
        assert longjob_dests[0].id == "pbs_longjobs"
        assert longjob_dests[1].id == "remote_cluster"

    def test_load_tool(self):
        self.__with_advanced_config()
        baz_tool = self.job_config.tools["baz"][0]
        assert baz_tool.id == "baz"
        assert baz_tool.handler == "special_handlers"
        assert baz_tool.destination == "bigmem"

    def test_load_tool_params(self):
        self.__with_advanced_config()
        foo_tool = self.job_config.tools["foo"][0]
        assert foo_tool.params["source"] == "trackster"

    def test_default_limits(self):
        limits = self.job_config.limits
        assert limits.registered_user_concurrent_jobs is None
        assert limits.anonymous_user_concurrent_jobs is None
        assert limits.walltime is None
        assert limits.walltime_delta is None
        assert limits.total_walltime == {}
        assert limits.output_size is None
        assert limits.destination_user_concurrent_jobs == {}
        assert limits.destination_total_concurrent_jobs == {}

    def test_limit_overrides(self):
        self.__with_advanced_config()
        limits = self.job_config.limits
        assert limits.registered_user_concurrent_jobs == 2
        assert limits.anonymous_user_concurrent_jobs == 1
        assert limits.destination_user_concurrent_jobs["local"] == 1
        assert limits.destination_user_concurrent_jobs["mycluster"] == 2
        assert limits.destination_user_concurrent_jobs["longjobs"] == 1
        assert limits.walltime_delta == datetime.timedelta(0, 0, 0, 0, 0, 24)
        assert limits.total_walltime["delta"] == datetime.timedelta(0, 0, 0, 0, 0, 24)
        assert limits.total_walltime["window"] == 30

    def test_env_parsing(self):
        self.__with_advanced_config()
        env_dest = self.job_config.destinations["java_cluster"][0]
        assert len(env_dest.env) == 4, len(env_dest.env)
        assert env_dest.env[0]["name"] == "_JAVA_OPTIONS"
        assert env_dest.env[0]["value"] == '-Xmx6G'

        assert env_dest.env[1]["name"] == "ANOTHER_OPTION"
        assert env_dest.env[1]["raw"] is True

        assert env_dest.env[2]["file"] == "/mnt/java_cluster/environment_setup.sh"

        assert env_dest.env[3]["execute"] == "module load javastuff/2.10"

    def test_macro_expansion(self):
        self.__with_advanced_config()
        for name in ["foo_small", "foo_medium", "foo_large", "foo_longrunning"]:
            assert self.job_config.destinations[name]

    def test_conditional_runners(self):
        self.__write_config_from(CONDITIONAL_RUNNER_JOB_CONF)
        runner_ids = [r["id"] for r in self.job_config.runner_plugins]
        assert "local2" in runner_ids
        assert "local3" not in runner_ids

        assert "local2_dest" in self.job_config.destinations
        assert "local3_dest" not in self.job_config.destinations

    def test_conditional_runners_from_environ(self):
        self.__write_config_from(CONDITIONAL_RUNNER_JOB_CONF)
        os.environ["LOCAL2_ENABLED"] = "False"
        os.environ["LOCAL3_ENABLED"] = "True"
        try:
            runner_ids = [r["id"] for r in self.job_config.runner_plugins]
            assert "local2" not in runner_ids
            assert "local3" in runner_ids

            assert "local2_dest" not in self.job_config.destinations
            assert "local3_dest" in self.job_config.destinations
        finally:
            del os.environ["LOCAL2_ENABLED"]
            del os.environ["LOCAL3_ENABLED"]

    # TODO: Add job metrics parsing test.

    @property
    def app(self):
        if not self.__app:
            self.__app = bunch.Bunch(
                config=self.config,
                job_metrics=MockJobMetrics(),
                application_stack=self.application_stack
            )
        return self.__app

    @property
    def application_stack(self):
        if not self.__application_stack:
            self.__application_stack = ApplicationStack()
        return self.__application_stack

    @property
    def job_config(self):
        if not self.__job_configuration:
            base_handler_pools = self.__job_configuration_base_pools or JobConfiguration.DEFAULT_BASE_HANDLER_POOLS
            mock_uwsgi = mock.Mock()
            mock_uwsgi.mule_id = lambda: 1
            with mock.patch('galaxy.web.stack.uwsgi', mock_uwsgi), \
                    mock.patch('galaxy.web.stack.uwsgi.opt', self.__uwsgi_opt), \
                    mock.patch('galaxy.jobs.JobConfiguration.DEFAULT_BASE_HANDLER_POOLS', base_handler_pools):
                self.__job_configuration = JobConfiguration(self.app)
        return self.__job_configuration

    def __with_uwsgi_application_stack(self, **uwsgi_opt):
        self.__uwsgi_opt = uwsgi_opt
        self.__application_stack = UWSGIApplicationStack()

    def __with_advanced_config(self):
        self.__write_config_from(ADVANCED_JOB_CONF)

    def __with_handlers_config(self, assign_with=None, default=None, handlers=None, base_pools=None):
        handlers = handlers or []
        template = {
            'assign_with': ' assign_with="%s"' % assign_with if assign_with is not None else '',
            'default': ' default="%s"' % default if default is not None else '',
            'handlers': '\n'.join([
                '<handler id="{id}"{tags}/>'.format(
                    id=x['id'],
                    tags=' tags="%s"' % x['tags'] if 'tags' in x else ''
                ) for x in handlers]),
        }
        self.__job_configuration_base_pools = base_pools
        self.__write_config_from(HANDLER_TEMPLATE_JOB_CONF, template=template)

    def __write_config_from(self, path, template=None):
        template = template or {}
        self.__write_config(open(path, "r").read().format(**template))

    def __write_config(self, contents):
        with open(os.path.join(self.temp_directory, "job_conf.xml"), "w") as f:
            f.write(contents)


class MockJobMetrics(object):

    def __init__(self):
        pass

    def set_destination_conf_element(self, id, element):
        pass
