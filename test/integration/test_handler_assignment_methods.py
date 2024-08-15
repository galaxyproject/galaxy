"""Integration tests for configurable job handler assignment methods."""

import os

from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
HANDLER_TEMPLATE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "handler_template_job_conf.xml")


class WritesConfig:
    def _with_handlers_config(self, assign_with=None, default=None, handlers=None):
        handlers = handlers or []
        template = {
            "assign_with": f' assign_with="{assign_with}"' if assign_with is not None else "",
            "default": f' default="{default}"' if default is not None else "",
            "handlers": "\n".join(
                '<handler id="{id}"{tags}/>'.format(
                    id=x["id"], tags=' tags="{}"'.format(x["tags"]) if "tags" in x else ""
                )
                for x in handlers
            ),
        }
        self.__write_config_from(HANDLER_TEMPLATE_JOB_CONFIG_FILE, template=template)

    def __write_config_from(self, path, template=None):
        template = template or {}
        self.__write_config(open(path).read().format(**template))

    def __write_config(self, contents):
        with open(self._app.config.job_config_file, "w") as f:
            f.write(contents)


class BaseHandlerAssignmentMethodIntegrationTestCase(integration_util.IntegrationTestCase, WritesConfig):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = os.path.join(cls.jobs_directory, "job_conf.xml")
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"


class TestDBPreassignHandlerAssignmentMethodIntegration(BaseHandlerAssignmentMethodIntegrationTestCase):
    def setUp(self):
        self._with_handlers_config(assign_with="db-preassign", handlers=[{"id": "main"}])
        super().setUp()

    def test_handler_assignment(self):
        tool_id = "config_vars"
        self._run_tool_test(tool_id)


class TestDBTransactionIsolationHandlerAssignmentMethodIntegration(BaseHandlerAssignmentMethodIntegrationTestCase):
    def setUp(self):
        self._with_handlers_config(assign_with="db-transaction-isolation", handlers=[{"id": "main"}])
        super().setUp()

    def test_handler_assignment(self):
        self._skip_unless_postgres()
        tool_id = "config_vars"
        self._run_tool_test(tool_id)


class TestDBSkipLockedHandlerAssignmentMethodIntegration(BaseHandlerAssignmentMethodIntegrationTestCase):
    def setUp(self):
        self._with_handlers_config(assign_with="db-skip-locked", handlers=[{"id": "main"}])
        super().setUp()

    def test_handler_assignment(self):
        self._skip_unless_postgres()
        tool_id = "config_vars"
        self._run_tool_test(tool_id)
