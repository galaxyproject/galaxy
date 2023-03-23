"""Integration tests for running tools in Docker containers."""

import json
import logging
import os
import re
import unittest
from tempfile import mkdtemp
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
)
from typing_extensions import (
    Literal,
    Protocol,
)

from galaxy.tool_util.deps.container_resolvers.mulled import list_docker_cached_mulled_images
from galaxy.util.commands import (
    shell,
    which,
)
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

if TYPE_CHECKING:
    from requests import Response

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

# local_docker
# local_docker_inline_container_resolvers (using only fallback resolver)_
DOCKERIZED_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "dockerized_job_conf.yml")
DOCKERIZED_JOB_CONFIG = {
    'runners': {'local': {'load': 'galaxy.jobs.runners.local:LocalJobRunner', 'workers': 1}},
    'execution': {
        'default': 'local_docker',
        'environments': {
            'local_docker': {'runner': 'local', 'docker_enabled': True},
        }
    },
    'tools': [
        {'id': 'upload1', 'environment': 'local_upload'},
    ]
}

SINGULARITY_JOB_CONFIG = {
    'runners': {'local': {'load': 'galaxy.jobs.runners.local:LocalJobRunner', 'workers': 1}},
    'execution': {
        'default': 'local_singularity', 
        'environments': {
            'local_singularity': {'runner': 'local', 'singularity_enabled': True, 'singularity_run_extra_arguments': '--no-mount tmp'},
            'local_upload': {'runner': 'local'}
        }
    },
    'tools': [{'id': 'upload1', 'environment': 'local_upload'}]}

# define an environment (local_singularity) for local execution with singularity enabled
SINGULARITY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "singularity_job_conf.yml")

JOB_CONFIG_FOR_CONTAINER_TYPE = {
    "docker": DOCKERIZED_JOB_CONFIG,
    "singularity": SINGULARITY_JOB_CONFIG,
}

JOB_CONFIG_FILE_FOR_CONTAINER_TYPE = {
    "docker": DOCKERIZED_JOB_CONFIG_FILE,
    "singularity": SINGULARITY_JOB_CONFIG_FILE,
}

EXTENDED_TIMEOUT = 120


class MulledJobTestCases:
    """
    test cases for mulled containers
    """

    dataset_populator: DatasetPopulator

    def test_explicit(self, history_id: str) -> None:
        """
        tool having one package + one explicit container requirement
        """
        self.dataset_populator.run_tool("mulled_example_explicit", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True, timeout=EXTENDED_TIMEOUT)
        output = self.dataset_populator.get_history_dataset_content(history_id)
        assert "0.7.15-r1140" in output

    def test_mulled_simple(self, history_id: str) -> None:
        """
        tool having one package requirement
        """
        self.dataset_populator.run_tool("mulled_example_simple", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True, timeout=EXTENDED_TIMEOUT)
        output = self.dataset_populator.get_history_dataset_content(history_id)
        assert "0.7.15-r1140" in output

    def test_mulled_explicit_invalid_case(self, history_id: str) -> None:
        """
        tool having one package + one (invalid? due to capitalization) explicit container requirement
        """
        self.dataset_populator.run_tool("mulled_example_invalid_case", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True, timeout=EXTENDED_TIMEOUT)
        output = self.dataset_populator.get_history_dataset_content(history_id)
        assert "0.7.15-r1140" in output


class ContainerizedIntegrationTestCase(IntegrationTestCase):
    """
    class for containerized (docker) tests
    provides methods for clearing and checking the container cache
    cache is cleared before each test
    """

    container_type: str = "docker"
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    jobs_directory: str
    allow_conda_fallback: bool = False

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self._clear_container_cache()

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config"] = JOB_CONFIG_FOR_CONTAINER_TYPE[cls.container_type]
        # for almost all containerized tests we want to disable
        # default (conda) resolution
        # if conda fallback is allowed the conda env is auto installed on tool
        # execution
        if not cls.allow_conda_fallback:
            disable_dependency_resolution(config)
        else:
            cls.conda_tmp_prefix = mkdtemp()
            cls._test_driver.temp_directories.append(cls.conda_tmp_prefix)
            config["use_cached_dependency_manager"] = True
            config["conda_auto_init"] = True
            config["conda_auto_install"] = True
            config["conda_prefix"] = os.path.join(cls.conda_tmp_prefix, "conda")

    def _clear_container_cache(self):
        """
        clear the cached images

        should be overwritten in test classes for singularity
        """
        logging.debug("TestMulledContainerResolver.clear_cache")
        cmd = ["docker", "system", "prune", "--all", "--force", "--volumes"]
        shell(cmd)

    def _assert_container_in_cache(
        self, cached: bool, container_name: str, namespace: Optional[str] = None, hash_func: Literal["v1", "v2"] = "v2"
    ) -> None:
        """
        function to check if the container is cached

        should be overwritten in test classes for singularity

        - determines list of cached images using `docker images`
        - and checks the given name is in the image identifiers of the cached images

        The boolean `cached` sets the assumption in the caching state.
        `namespace` and `hash_func` are used to filter cached images.
        """
        cache_list = list_docker_cached_mulled_images(namespace, hash_func)
        imageid_list = [_.image_identifier for _ in cache_list]
        assert cached == (container_name in imageid_list)


class SingularityIntegrationTestCase(ContainerizedIntegrationTestCase):
    """
    analogous to ContainerizedIntegrationTestCase, just for singularity
    provides adapted methods for clearing and checking the container cache
    """
    container_type: str = "singularity"

    def _clear_container_cache(self):
        """
        see TestMulledContainerResolver
        """
        cache_directory = os.path.join(self._app.config.container_image_cache_path, "singularity", "mulled")
        logging.debug(f"TestMulledSingularityContainerResolver.clear_cache {cache_directory}")
        for filename in os.listdir(cache_directory):
            file_path = os.path.join(cache_directory, filename)
            os.unlink(file_path)

    def _assert_container_in_cache(
        self, cached: bool, container_name: str, namespace: Optional[str] = None, hash_func: Literal["v1", "v2"] = "v2"
    ) -> None:
        """
        see TestMulledContainerResolver
        """
        cache_directory = os.path.join(self._app.config.container_image_cache_path, "singularity", "mulled")
        imageid_list = os.listdir(path=cache_directory)
        assert cached == (container_name in imageid_list)


def disable_dependency_resolution(config: Dict[str, Any]) -> None:
    # Disable tool dependency resolution.
    config["tool_dependency_dir"] = "none"
    config["conda_auto_init"] = False
    config["conda_auto_install"] = False


def skip_if_container_type_unavailable(cls) -> None:
    if not which(cls.container_type):
        raise unittest.SkipTest(f"Executable '{cls.container_type}' not found on PATH")


class TestDockerizedJobsIntegration(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):
    dataset_populator: DatasetPopulator
    jobs_directory: str
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE
    build_mulled_resolver = "build_mulled"
    container_type = "docker"

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()

    def test_container_job_environment(self) -> None:
        """
        test job environment for non-legacy tools
        """
        job_env = self._run_and_get_environment_properties("job_environment_default")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home.startswith(self.jobs_directory)
        assert job_env.home.endswith("/home")

    def test_container_job_environment_legacy(self) -> None:
        """
        test that legacy tools use the user's home (/home/...)
        use the current user's home and do not use a dir in the JWD as home
        """
        job_env = self._run_and_get_environment_properties("job_environment_default_legacy")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert not job_env.home.startswith(self.jobs_directory)
        assert not job_env.home.endswith("/home")

    def test_container_job_environment_explicit_shared_home(self) -> None:
        """
        test that non-legacy tools that explicitly specify
        <command use_shared_home="true"> use the current user's home
        """
        job_env = self._run_and_get_environment_properties("job_environment_explicit_shared_home")

        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert not job_env.home.startswith(self.jobs_directory)
        assert not job_env.home.endswith("/home"), job_env.home

    def test_container_job_environment_explicit_isolated_home(self) -> None:
        """
        test that non-legacy tools that explicitly specify
        <command use_shared_home="false"> (the default) use a separate dir in the JWD as home
        """
        job_env = self._run_and_get_environment_properties("job_environment_explicit_isolated_home")

        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home.startswith(self.jobs_directory)
        assert job_env.home.endswith("/home"), job_env.home

    def test_build_mulled(self) -> None:
        """
        test building of a mulled container using the build_mulled container resolver
        triggered via API dependency_resolvers/toolbox/install
        """
        resolver_type = self.build_mulled_resolver
        tool_ids = ["mulled_example_multi_1"]
        endpoint = "dependency_resolvers/toolbox/install"
        data = {
            "tool_ids": json.dumps(tool_ids),
            "resolver_type": resolver_type,
            "container_type": self.container_type,
            "include_containers": True,
        }
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        create_response = self._get(
            "dependency_resolvers/toolbox",
            data={
                "tool_ids": tool_ids,
                "container_type": self.container_type,
                "include_containers": True,
                "index_by": "tools",
            },
            admin=True,
        )
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        assert status[0]["model_class"] == "ContainerDependency"
        assert status[0]["dependency_type"] == self.container_type
        self._assert_container_description_identifier(
            status[0]["container_description"]["identifier"],
            "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
        )

    def _assert_container_description_identifier(self, identifier: str, expected_hash: str):
        """
        function to check the identifier of container against a mulled hash
        here we assert that locally built containers are cached in the "local"
        namespace as if they were from quay.io

        may need to be overwritten in derived classes.
        """
        assert identifier == f"quay.io/local/{expected_hash}"


class TestMappingContainerResolver(IntegrationTestCase):
    """
    - test mapping resolver
    - test global container resolvers given in extra yaml file referenced via
      `container_resolvers_config_file` in galaxy.yml
    - container resolvers defined per destination in the job config
      should be ignored
      (TODO this is not tested since a fallback resolver pointing to the same container
       would be used)
    """

    dataset_populator: DatasetPopulator
    jobs_directory: str
    framework_tool_and_types = True
    container_type = "docker"
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)
        container_resolvers_config_path = os.path.join(cls.jobs_directory, "container_resolvers.yml")
        with open(container_resolvers_config_path, "w") as f:
            f.write(
                """
- type: mapping
  mappings:
    - container_type: docker
      tool_id: mulled_example_broken_no_requirements
      identifier: 'quay.io/biocontainers/bwa:0.7.15--0'
"""
            )
        config["container_resolvers_config_file"] = container_resolvers_config_path

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_explicit_mapping(self, history_id: str) -> None:
        self.dataset_populator.run_tool("mulled_example_broken_no_requirements", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


class TestInlineContainerConfiguration(TestMappingContainerResolver):
    """
    Same as TestMappingContainerResolver, but defining container resolvers
    via `container_resolvers` (not testing the YAML parsing of inline container
    resolvers from galaxy.yml)
    """

    jobs_directory: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)
        config.pop("container_resolvers_config_file")
        container_resolvers_config = [
            {
                "type": "mapping",
                "mappings": [
                    {
                        "container_type": "docker",
                        "tool_id": "mulled_example_broken_no_requirements",
                        "identifier": "quay.io/biocontainers/bwa:0.7.15--0",
                    }
                ],
            }
        ]
        config["container_resolvers"] = container_resolvers_config


class TestPerDestinationContainerConfiguration(TestMappingContainerResolver):
    """
    This tests:
    - that container_resolvers_config_file works when specified in a destination
    - and it does so also in presence of a global container_resolvers_config
    """

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # make sure that job_config_file is unset and set job_config
        # its the same content as dockerized_job_conf.yml + the per
        # destination container_resolver_config_file
        try:
            config.pop("job_config_file")
        except KeyError:
            pass
        config["job_config"] = {
            "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
            "execution": {
                "default": "local_docker",
                "environments": {
                    "local_docker": {"runner": "local", "docker_enabled": True},
                    "local_docker_inline_container_resolvers": {
                        "runner": "local",
                        "docker_enabled": True,
                        "container_resolvers_config_file": os.path.join(
                            SCRIPT_DIRECTORY, "fallback_container_resolver.yml"
                        ),
                    },
                },
            },
            "tools": [
                {"id": "upload1", "environment": "local_upload"},
                {
                    "id": "mulled_example_broken_no_requirements",
                    "environment": "local_docker_inline_container_resolvers",
                },
            ],
        }
        # define a global container_resolvers (that can not work .. thereby
        # showing that the per destination config is used) and make sure that
        # container_resolvers_config_file is not set
        try:
            config.pop("container_resolvers_config_file")
        except KeyError:
            pass
        container_resolvers_config = [
            {
                "type": "mapping",
                "mappings": [
                    {
                        "container_type": "docker",
                        "tool_id": "some_bogus_too_id",
                        "identifier": "quay.io/biocontainers/bwa:0.7.15--0",
                    }
                ],
            }
        ]
        config["container_resolvers"] = container_resolvers_config


class TestInlineJobEnvironmentContainerResolver(IntegrationTestCase):
    """
    Test
    - container resolvers config given inline in job configuration (DOCKERIZED_JOB_CONFIG_FILE)
    - job config maps the tool to a destination (local_docker_inline_container_resolvers)
      which only runs the fallback container resolver (which uses bwa 0.7.15)
    - tool defines no requirements (irrelevant for this test)
    """

    dataset_populator: DatasetPopulator
    jobs_directory: str
    framework_tool_and_types = True
    container_type = "docker"
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_inline_environment_container_resolver_configuration(self, history_id: str) -> None:
        self.dataset_populator.run_tool("mulled_example_broken_no_requirements_fallback", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


class TestSingularityJobsIntegration(TestDockerizedJobsIntegration):
    job_config_file = SINGULARITY_JOB_CONFIG_FILE
    build_mulled_resolver = "build_mulled_singularity"
    container_type = "singularity"

    def _assert_container_description_identifier(self, identifier, expected_hash):
        assert os.path.exists(identifier)
        assert identifier.endswith(f"singularity/mulled/{expected_hash}")


class ResolverTestProtocol(Protocol):
    """
    Helper class defining methods and properties needed to
    use ContainerResolverTestCases
    """

    @property
    def dataset_populator(self) -> DatasetPopulator:
        ...

    @property
    def tool_id(self) -> str:
        ...

    @property
    def assumptions(self) -> Dict[str, Any]:
        ...

    @property
    def container_type(self) -> Literal["docker", "singularity"]:
        ...

    def _assert_container_in_cache(
        self, cached: bool, container_name: str, namespace: Optional[str] = None, hash_func: Literal["v1", "v2"] = "v2"
    ) -> None:
        ...

    def _assert_status_code_is(self, response: "Response", expected_status_code: int) -> None:
        ...

    def _get(self, route, data=None, headers=None, admin=False) -> "Response":
        ...

    def _post(self, route, data=None, files=None, headers=None, admin=False, json: bool = False) -> "Response":
        ...


class ContainerResolverTestCases:
    """
    Test cases for (the?) 3 possibilities where Galaxy calls the (container) resolve function

    1. when preparing a job (test_tool_run)
       - check tool output
       - check if container has been cached
    2. when listing container dependencies in the admin UI (test_api_container_resolvers_toolbox)
       - test consist of 2 calls to the route in order to check if a 2nd round picks
         up a potentially cached container
       - after each call check container_type, used resolver and if container has been cached
    3. when "building" a container in the admin UI (test_api_container_resolvers_toolbox_install)
       - test consist of 2 calls to the route in order to check if a 2nd round picks
         up a potentially cached container
       - after each call check container_type, used resolver and if container has been cached
    """

    def test_tool_run(self: ResolverTestProtocol, history_id: str) -> None:
        """
        test running a tool

        - runs the tool with tool_id (allowed to fail: assumptions["run"]["expect_failure"])
        - checks outputs (assumptions["run"]["output"])
        - check is the container has been cached (assumptions["run"]["cache..."])
        """
        try:
            self.dataset_populator.run_tool(self.tool_id, {}, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True, timeout=240)
        except AssertionError:
            if not self.assumptions["run"].get("expect_failure", False):
                raise
        else:
            if self.assumptions["run"].get("expect_failure", False):
                raise AssertionError("test_tool_run is expected to fail")
        if not self.assumptions["run"].get("expect_failure", False):
            output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
            for o in self.assumptions["run"]["output"]:
                assert o in output
        self._assert_container_in_cache(
            self.assumptions["run"]["cached"],
            container_name=self.assumptions["run"]["cache_name"],
            namespace=self.assumptions["run"]["cache_namespace"],
        )

    def _check_status(self: ResolverTestProtocol, status: Dict[str, Any], assumptions:Dict[str, Any]):
        if "unresolved" in assumptions:
            assert status["model_class"] == "NullDependency"
            assert status["dependency_type"] is None
            assert 'container_resolver' not in status
            assert 'container_description' not in status
        else:
            assert status["model_class"] == "ContainerDependency"
            assert status["dependency_type"] == self.container_type
            assert status["container_resolver"]["resolver_type"] == assumptions["resolver_type"]
            assert re.match(assumptions["identifier"], status["container_description"]["identifier"])
            self._assert_container_in_cache(
                assumptions["cached"],
                container_name=assumptions["cache_name"],
                namespace=assumptions["cache_namespace"],
            )

    def test_api_container_resolvers_toolbox(self: ResolverTestProtocol):
        """
        test container resolvers via GET container_resolvers/toolbox

        which is what happens when listing containers in the admin UI
        both calls should resolve with mulled and container is not cached

        test checks assumptions on
        - resolver type
        - identifier (a regexp). note for docker the same when cached/uncached
        - caching (cached, cache_name, cache_namespace)
        """
        create_response = self._get(
            "container_resolvers/toolbox",
            data={
                "tool_ids": [self.tool_id],
# TODO                "container_type": self.container_type,
            },
            admin=True,
        )
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        self._check_status(status, self.assumptions["list"][0])

        create_response = self._get(
            "container_resolvers/toolbox",
            data={
                "tool_ids": [self.tool_id],
# TODO                "container_type": self.container_type,
            },
            admin=True,
        )
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        self._check_status(status, self.assumptions["list"][1])

    def test_api_container_resolvers_toolbox_install(self: ResolverTestProtocol):
        """
        test container resolvers via POST container_resolvers/toolbox/install

        which is what happens when building a container in the admin UI

        1st call resolves with mulled and container is cached (but the cached
            URI is returned .. but for docker this makes no difference)
        2nd call should resolve with cached_mulled (container is still cached)
        """
        create_response = self._post(
            "container_resolvers/toolbox/install",
            data={
                "tool_ids": json.dumps([self.tool_id]),
# TODO                "container_type": self.container_type,
                "include_containers": True,
            },
            admin=True,
        )
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        self._check_status(status, self.assumptions["build"][0])

        create_response = self._post(
            "container_resolvers/toolbox/install",
            data={
                "tool_ids": json.dumps([self.tool_id]),
# TODO                "container_type": self.container_type,
                "include_containers": True,
            },
            admin=True,
        )
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        self._check_status(status, self.assumptions["build"][1])


class TestMulledContainerResolver(ContainerizedIntegrationTestCase, ContainerResolverTestCases):
    """
    test cached_mulled + mulled container resolvers in default config

    besides the properties of the returned container description the main points are
    - running a tool creates an entry in the container cache (the test **can't** show if this is due to
      1. the `docker inspect .. && docker pull ..` statement in the job script or
      2. the resolve function
      it should be both .. see also the corresponding test in TestMulledSingularityContainerResolver where
      it is definitely the resolve function -- since for singularity there is no additional commands in the
      job script)
    - listing containers does not create a cache entry (cached=False and in both calls to resolve mulled is successful)
    - building the container creates a cache entry (cached=True, 1st call resolves with mulled and 2nd with cached_mulled)
    """

    tool_id = "mulled_example_multi_1"
    mulled_hash = "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0"
    container_resolvers_config: List[Dict[str, Any]] = [
        {
            "type": "cached_mulled",
        },
        {"type": "mulled"},
    ]
    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "bedtools v2.26.0",
                "samtools: error while loading shared libraries: libcrypto.so.1.0.0",
            ],
            "cached": True,
            "cache_name": f"quay.io/biocontainers/{mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled",
                "identifier": "quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled",
                "identifier": "quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled",
                "identifier": "quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled",
                "identifier": "quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestMulledSingularityContainerResolver(SingularityIntegrationTestCase, ContainerResolverTestCases):
    """
    test cached_mulled_singularity + mulled_singularity container resolvers in default config

    assumptions:
    1. tool run
       - container should still be cached during job preparation (even if the cached image
         won't be used for the 1st run .. see assumption for building .. would change with auto_install=False)
    2. listing container
       - container is not cached
       - URI is resolved via mulled_singularity (note the `docker://` prefix)
    3. building container
       - container is cached in 1st round (via mulled_singularity), but **despite caching the URI is returned**
       - 2nd round resolves cached image, uses the cached container
    """

    tool_id = "mulled_example_multi_1"
    mulled_hash = "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0"
    container_resolvers_config: List[Dict[str, Any]] = [
        {
            "type": "cached_mulled_singularity",
        },
        {
            "type": "mulled_singularity",
        },
    ]

    assumptions = {
        "run": {
            "expect_failure": False,
            "output": [
                "bedtools v2.26.0",
                "samtools: error while loading shared libraries: libcrypto.so.1.0.0",
            ],
            "cached": True,
            "cache_name": mulled_hash,
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": "docker://quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": False,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled_singularity",
                "identifier": "docker://quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": False,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": "docker://quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": True,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled_singularity",
                "identifier": "/tmp/.*/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": True,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestMulledContainerResolverNoAutoInstall(TestMulledContainerResolver):
    """
    Use the mulled (docker) container resolver with auto_install: False

    No difference (since the cached name is identical to the URI)
    """
    pass


class TestMulledSingularityContainerResolverNoAutoInstall(TestMulledSingularityContainerResolver):
    """
    Use the mulled singularity container resolver with auto_install: False

    The only difference is that the first call to resolve also returns the path
    to the cached image (see assumptions["build"]["identifier"]). This is also used
    in the run, but I have no idea how to test this (in the generated job script
    the path is used instead of the URI)
    """
    container_resolvers_config: List[Dict[str, Any]] = [
        {
            "type": "cached_mulled_singularity",
        },
        {
            "type": "mulled_singularity",
            "auto_install": False,
        },
    ]

    mulled_hash = "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0"
    assumptions = {
        "run": {
            "expect_failure": False,
            "output": [
                "bedtools v2.26.0",
                "samtools: error while loading shared libraries: libcrypto.so.1.0.0",
            ],
            "cached": True,
            "cache_name": mulled_hash,
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": "docker://quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": False,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled_singularity",
                "identifier": "docker://quay.io/biocontainers/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": False,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": "/tmp/.*/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": True,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled_singularity",
                "identifier": "/tmp/.*/mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
                "cached": True,
                "cache_name": mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
    }


class TestCondaFallBack(ContainerizedIntegrationTestCase, ContainerResolverTestCases):
    """
    test that Galaxy falls back to default dependency resolvers (i.e. conda) if no
    container can be resolved

    here we force container resolution to fail because only singularity resolvers
    are configured on a docker destination.

    - assumptions that need to be met is that tool is executed successfully (via conda)
    - and listing and building containers does not work
    """

    allow_conda_fallback: bool = True
    tool_id = "mulled_example_multi_1"
    mulled_hash = "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0"
    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "cached_mulled_singularity"},
        {"type": "mulled_singularity"},
    ]

    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "bedtools v2.26.0",
                # conda env does not suffer from broken library -> so different output
                "samtools (Tools for alignments in the SAM format)",
                "Version: 1.3.1",
            ],
            "cached": False,
            "cache_name": f"quay.io/biocontainers/{mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {"unresolved": True},
            {"unresolved": True},
        ],
        "build": [
            {"unresolved": True},
            {"unresolved": True},
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestCondaFallBackAndRequireContainer(ContainerizedIntegrationTestCase, ContainerResolverTestCases):
    """
    test that we can disable fallback to the default resolvers (conda)
    by setting the destination property require_container

    same as TestCondaFallBack but tool needs to fail
    """

    allow_conda_fallback: bool = True
    tool_id = "mulled_example_multi_1"
    mulled_hash = "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0"
    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "cached_mulled_singularity"},
        {"type": "mulled_singularity"},
    ]

    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "bedtools v2.26.0",
                # conda env does not suffer from broken library -> so different output
                "samtools (Tools for alignments in the SAM format)",
                "Version: 1.3.1",
            ],
            "cached": False,
            "cache_name": f"quay.io/biocontainers/{mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {"unresolved": True},
            {"unresolved": True},
        ],
        "build": [
            {"unresolved": True},
            {"unresolved": True},
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config"]["execution"]["environments"]["local_docker"]["require_container"] = True
        config["container_resolvers"] = cls.container_resolvers_config