import datetime
import os
import shutil
import tempfile
import unittest
from unittest import mock

from pykwalify.core import Core

from galaxy.config import GALAXY_SCHEMAS_PATH
from galaxy.job_metrics import JobMetrics
from galaxy.jobs import JobConfiguration
from galaxy.util import (
    galaxy_directory,
    galaxy_samples_directory,
)
from galaxy.web_stack import ApplicationStack
from galaxy.web_stack.handlers import HANDLER_ASSIGNMENT_METHODS

# File would be slightly more readable if contents were embedded directly, but
# there are advantages to testing the documentation/examples.
SIMPLE_JOB_CONF = os.path.join(galaxy_samples_directory(), "job_conf.xml.sample_basic")
ADVANCED_JOB_CONF = os.path.join(galaxy_samples_directory(), "job_conf.xml.sample_advanced")
ADVANCED_JOB_CONF_YAML = os.path.join(os.path.dirname(__file__), "job_conf.sample_advanced.yml")
CONDITIONAL_RUNNER_JOB_CONF = os.path.join(os.path.dirname(__file__), "conditional_runners_job_conf.xml")
HANDLER_TEMPLATE_JOB_CONF = os.path.join(os.path.dirname(__file__), "handler_template_job_conf.xml")


class TestApplicationStack(ApplicationStack):
    def get_preferred_handler_assignment_method(self):
        return HANDLER_ASSIGNMENT_METHODS.DB_SKIP_LOCKED


class BaseJobConfXmlParserTestCase(unittest.TestCase):
    extension = "xml"

    def setUp(self):
        self.temp_directory = tempfile.mkdtemp()
        self.config = mock.Mock(
            job_config_file=os.path.join(self.temp_directory, "job_conf.%s" % self.extension),
            use_tasked_jobs=False,
            job_resource_params_file="/tmp/fake_absent_path",
            config_dict={},
            default_job_resubmission_condition="",
            track_jobs_in_database=True,
            server_name="main",
        )
        self._write_config_from(SIMPLE_JOB_CONF)
        self._app = None
        self._application_stack = None
        self._job_configuration = None
        self._job_configuration_base_pools = None

    def tearDown(self):
        shutil.rmtree(self.temp_directory)

    # TODO: Add job metrics parsing test.

    @property
    def app(self):
        if not self._app:
            self._app = mock.Mock(
                config=self.config, job_metrics=JobMetrics(), application_stack=self.application_stack
            )
        return self._app

    @property
    def application_stack(self) -> ApplicationStack:
        if not self._application_stack:
            self._application_stack = TestApplicationStack()
        return self._application_stack

    @property
    def job_config(self):
        if not self._job_configuration:
            self._job_configuration = JobConfiguration(self.app)
        return self._job_configuration

    def _with_handlers_config(self, assign_with=None, default=None, handlers=None, base_pools=None):
        handlers = handlers or []
        template = {
            "assign_with": ' assign_with="%s"' % assign_with if assign_with is not None else "",
            "default": ' default="%s"' % default if default is not None else "",
            "handlers": "\n".join(
                '<handler id="{id}"{tags}/>'.format(id=x["id"], tags=' tags="%s"' % x["tags"] if "tags" in x else "")
                for x in handlers
            ),
        }
        self._job_configuration_base_pools = base_pools
        self._write_config_from(HANDLER_TEMPLATE_JOB_CONF, template=template)

    def _write_config_from(self, path, template=None):
        template = template or {}
        try:
            contents = open(path).read()
        except FileNotFoundError:
            dir_path = os.path.dirname(path)
            if os.path.exists(dir_path):
                dir_contents = os.listdir(dir_path)
                raise Exception(f"Failed to find file {path}, directory {dir_path} exists and contains {dir_contents}")
            else:
                dir_that_exists = dir_path
                while not os.path.exists(dir_that_exists):
                    dir_that_exists = os.path.dirname(dir_that_exists)
                dir_contents = os.listdir(dir_that_exists)
                raise Exception(
                    f"Failed to find file {path}, directory {dir_path} does not exist - {dir_that_exists} is the first root that exists and contains {dir_contents}."
                )
        if template:
            contents = contents.format(**template)
        self._write_config(contents)

    def _write_config(self, contents):
        with open(os.path.join(self.temp_directory, "job_conf.%s" % self.extension), "w") as f:
            f.write(contents)

    def _with_advanced_config(self):
        if self.extension == "xml":
            self._write_config_from(ADVANCED_JOB_CONF)
        else:
            self._write_config_from(ADVANCED_JOB_CONF_YAML)


class SimpleJobConfXmlParserTestCase(BaseJobConfXmlParserTestCase):
    extension = "xml"

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
        self._with_handlers_config(
            handlers=[{"id": "handler0", "tags": "handlers"}, {"id": "handler1", "tags": "handlers"}],
            default="handlers",
        )
        assert self.job_config.default_handler_id == "handlers"

    def test_handler_tag_parsing(self):
        self._with_handlers_config(
            handlers=[{"id": "handler0", "tags": "handlers"}, {"id": "handler1", "tags": "handlers"}],
            default="handlers",
        )
        assert "handler0" in self.job_config.handlers["handlers"]
        assert "handler1" in self.job_config.handlers["handlers"]

    def test_implict_db_self_handler_assign(self):
        assert self.job_config.handler_assignment_methods == ["db-skip-locked"]
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}

    def test_implicit_db_assign_handler_assign_with_explicit_handlers(self):
        self._with_handlers_config(handlers=[{"id": "handler0"}, {"id": "handler1"}])
        assert self.job_config.handler_assignment_methods == ["db-skip-locked"]
        assert self.job_config.default_handler_id is None
        assert sorted(self.job_config.handlers["_default_"]) == ["handler0", "handler1"]

    def test_explicit_mem_self_handler_assign(self):
        self._with_handlers_config(assign_with="mem-self")
        assert self.job_config.handler_assignment_methods == ["mem-self"]
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}
        assert not self.config.track_jobs_in_database

    def test_explicit_mem_self_handler_assign_with_handlers(self):
        self._with_handlers_config(assign_with="mem-self", handlers=[{"id": "handler0"}])
        assert self.job_config.handler_assignment_methods == ["mem-self"]
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers["_default_"] == ["handler0"]

    def test_explicit_db_transaction_isolation_handler_assign(self):
        self._with_handlers_config(assign_with="db-transaction-isolation")
        assert self.job_config.handler_assignment_methods == ["db-transaction-isolation"]
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}

    def test_explicit_db_skip_locked_handler_assign(self):
        self._with_handlers_config(assign_with="db-skip-locked")
        assert self.job_config.handler_assignment_methods == ["db-skip-locked"]
        assert self.job_config.default_handler_id is None
        assert self.job_config.handlers == {}

    def test_load_simple_destination(self):
        local_dest = self.job_config.destinations["local"][0]
        assert local_dest.id == "local"
        assert local_dest.runner == "local"

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

    def test_conditional_runners(self):
        self._write_config_from(CONDITIONAL_RUNNER_JOB_CONF)
        runner_ids = [r["id"] for r in self.job_config.runner_plugins]
        assert "local2" in runner_ids
        assert "local3" not in runner_ids

        assert "local2_dest" in self.job_config.destinations
        assert "local3_dest" not in self.job_config.destinations

    def test_conditional_runners_from_environ(self):
        self._write_config_from(CONDITIONAL_RUNNER_JOB_CONF)
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

    def test_macro_expansion(self):
        self._with_advanced_config()
        for name in ["foo_small", "foo_medium", "foo_large", "foo_longrunning"]:
            assert self.job_config.destinations[name]


class AdvancedJobConfXmlParserTestCase(BaseJobConfXmlParserTestCase):
    def test_disable_job_metrics(self):
        self._with_advanced_config()
        self.job_config.destinations["multicore_local"]
        assert len(self.app.job_metrics.job_instrumenters["multicore_local"].plugins) == 0

    def test_default_job_metrics(self):
        self._with_advanced_config()
        self.job_config.destinations["pbs_longjobs"]
        assert self.app.job_metrics.job_instrumenters["pbs_longjobs"] == self.app.job_metrics.default_job_instrumenter

    def test_load_destination_params(self):
        self._with_advanced_config()
        pbs_dest = self.job_config.destinations["pbs_longjobs"][0]
        assert pbs_dest.id == "pbs_longjobs", pbs_dest
        assert pbs_dest.runner == "pbs"
        dest_params = pbs_dest.params
        assert dest_params["Resource_List"] == "walltime=72:00:00"

    def test_destination_tags(self):
        self._with_advanced_config()
        longjob_dests_ids = sorted(j.id for j in self.job_config.destinations["longjobs"])
        assert len(longjob_dests_ids) == 2
        assert longjob_dests_ids[0] == "pbs_longjobs"
        assert longjob_dests_ids[1] == "remote_cluster"

    def test_load_tool(self):
        self._with_advanced_config()
        baz_tool = self.job_config.tools["baz"][0]
        assert baz_tool.id == "baz"
        assert baz_tool.handler == "special_handlers"
        assert baz_tool.destination == "bigmem"

    def test_load_tool_params(self):
        self._with_advanced_config()
        foo_tool = self.job_config.tools["foo"][0]
        assert foo_tool.params["source"] == "trackster"

    def test_limit_overrides(self):
        self._with_advanced_config()
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
        self._with_advanced_config()
        env_dest = self.job_config.destinations["java_cluster"][0]
        assert len(env_dest.env) == 4, len(env_dest.env)
        assert env_dest.env[0]["name"] == "_JAVA_OPTIONS"
        assert env_dest.env[0]["value"] == "-Xmx6G"

        assert env_dest.env[1]["name"] == "ANOTHER_OPTION"
        assert env_dest.env[1]["raw"] is True

        assert env_dest.env[2]["file"] == "/mnt/java_cluster/environment_setup.sh"

        assert env_dest.env[3]["execute"] == "module load javastuff/2.10"

    def test_runners_kwds(self):
        self._with_advanced_config()
        sge_runner = [r for r in self.job_config.runner_plugins if r["id"] == "sge"][0]
        assert sge_runner["kwds"]["drmaa_library_path"] == "/sge/lib/libdrmaa.so"

        drmaa_runner = [r for r in self.job_config.runner_plugins if r["id"] == "drmaa"][0]
        assert drmaa_runner["kwds"]["invalidjobexception_state"] == "ok"

        assert self.job_config.dynamic_params["rules_module"] == "galaxy.jobs.rules"

    def test_container_tag_in_destination(self):
        self._with_advanced_config()
        container_dest = self.job_config.destinations["customized_container"][0]
        assert "container" in container_dest.params
        assert "container_override" in container_dest.params
        container = container_dest.params["container"]
        assert len(container) == 2
        container0 = container[0]
        assert container0["type"] == "docker"
        assert container0["identifier"] == "busybox:ubuntu-14.04"

        container_override = container_dest.params["container_override"]
        assert len(container_override) == 2

        container_override1 = container_override[1]
        assert container_override1["type"] == "singularity"
        assert container_override1["identifier"] == "/path/to/default/container"
        assert not container_override1["resolve_dependencies"]

    def test_tool_mapping_parameters(self):
        self._with_advanced_config()
        assert self.job_config.tools["foo"][-1].params["source"] == "trackster"
        assert self.job_config.tools["longbar"][-1].destination == "dynamic"
        assert self.job_config.tools["longbar"][-1].resources == "all"
        assert "resources" not in self.job_config.tools["longbar"][-1].params

    def test_handler_runner_plugins(self):
        self._with_advanced_config()
        assert self.job_config.handler_runner_plugins["sge_handler"] == ["sge"]
        assert "special_handler1" not in self.job_config.handler_runner_plugins

    def test_resource_groups(self):
        self._with_advanced_config()
        assert self.job_config.default_resource_group == "default"
        assert self.job_config.resource_groups["memoryonly"] == ["memory"]


class AdvancedJobConfYamlParserTestCase(AdvancedJobConfXmlParserTestCase):
    extension = "yml"


def test_yaml_advanced_validation():
    schema = GALAXY_SCHEMAS_PATH / "job_config_schema.yml"
    integration_tests_dir = os.path.join(galaxy_directory(), "test", "integration")
    valid_files = [
        ADVANCED_JOB_CONF_YAML,
        os.path.join(integration_tests_dir, "delay_job_conf.yml"),
        os.path.join(integration_tests_dir, "embedded_pulsar_metadata_job_conf.yml"),
        os.path.join(integration_tests_dir, "io_injection_job_conf.yml"),
        os.path.join(integration_tests_dir, "resubmission_job_conf.yml"),
        os.path.join(integration_tests_dir, "resubmission_default_job_conf.yml"),
    ]
    for valid_file in valid_files:
        c = Core(
            source_file=valid_file,
            schema_files=[str(schema)],
        )
        c.validate()
