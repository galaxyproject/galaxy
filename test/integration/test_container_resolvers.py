import json
import os
import re
from tempfile import mkdtemp
from typing import (
    Any,
    ClassVar,
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
from galaxy.util.commands import shell
from galaxy.util.path import safe_walk
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase
from .test_containerized_jobs import (
    disable_dependency_resolution,
    skip_if_container_type_unavailable,
)

if TYPE_CHECKING:
    from requests import Response

EXTENDED_TIMEOUT = 120


DOCKERIZED_JOB_CONFIG = {
    "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
    "execution": {
        "default": "local_docker",
        "environments": {
            "local_docker": {"runner": "local", "docker_enabled": True},
        },
    },
    "tools": [
        {"id": "upload1", "environment": "local_upload"},
    ],
}
SINGULARITY_JOB_CONFIG = {
    "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
    "execution": {
        "default": "local_singularity",
        "environments": {
            "local_singularity": {
                "runner": "local",
                "singularity_enabled": True,
                "singularity_run_extra_arguments": "--no-mount tmp",
            },
            "local_upload": {"runner": "local"},
        },
    },
    "tools": [{"id": "upload1", "environment": "local_upload"}],
}
JOB_CONFIG_FOR_CONTAINER_TYPE = {
    "docker": DOCKERIZED_JOB_CONFIG,
    "singularity": SINGULARITY_JOB_CONFIG,
}


def _assert_container_in_cache_docker(
    cached: bool, container_name: str, namespace: Optional[str] = None, hash_func: Literal["v1", "v2"] = "v2"
):
    cache_list = list_docker_cached_mulled_images(namespace, hash_func)
    imageid_list = [_.image_identifier for _ in cache_list]
    assert cached == (container_name in imageid_list)


def _assert_container_in_cache_singularity(
    cache_directory: str,
    cached: bool,
    container_name: str,
    namespace: Optional[str] = None,
    hash_func: Literal["v1", "v2"] = "v2",
):
    cache_dir_contents = []
    for dirpath, _, files in safe_walk(cache_directory):
        for f in files:
            cache_dir_contents.append(os.path.join(dirpath, f))
    # explicit containers are stored in subdirs that are included in the container_name
    container_path, container_name = os.path.split(container_name)
    cache_directory = os.path.join(cache_directory, container_path)

    # it's fine if the path does not exist if not-cached is the assumption
    if not os.path.exists(cache_directory) and not cached:
        return

    imageid_list = os.listdir(path=cache_directory)
    assert cached == (
        container_name in imageid_list
    ), f"did not find container {container_name} in {cache_directory} which contains {imageid_list}. [{cache_dir_contents}]"


class DockerContainerResolverTestCase(IntegrationTestCase):
    """
    class for containerized (docker) tests
    provides methods for clearing and checking the container cache
    cache is cleared before each test
    """

    container_type: str = "docker"
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    conda_tmp_prefix: ClassVar[str]
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
        clear all possibe container caches (ie docker and singularity)
        """
        cmd = ["docker", "system", "prune", "--all", "--force", "--volumes"]
        shell(cmd)
        if not os.path.exists(self._app.config.container_image_cache_path):
            return
        for dirpath, _, files in safe_walk(self._app.config.container_image_cache_path):
            for f in files:
                os.unlink(os.path.join(dirpath, f))

    def _assert_container_in_cache(
        self,
        cached: bool,
        container_name: str,
        namespace: Optional[str] = None,
        hash_func: Literal["v1", "v2"] = "v2",
        **kwargs,
    ) -> None:
        """
        function to check if the container is cached

        should be overwritten in test classes for singularity

        - determines list of cached images using `docker images`
        - and checks the given name is in the image identifiers of the cached images

        The boolean `cached` sets the assumption in the caching state.
        `namespace` and `hash_func` are used to filter cached images.
        """
        _assert_container_in_cache_docker(cached, container_name, namespace, hash_func)

    def _assert_container_in_cache_api_calls(
        self,
        cached: bool,
        container_name: str,
        namespace: Optional[str] = None,
        hash_func: Literal["v1", "v2"] = "v2",
        **kwargs,
    ):
        """
        function that is used to check if a container is cached after tests of the API calls

        by default this is just calls _assert_container_in_cache
        but can be overwritten (as in TestDefaultSingularityContainerResolver)
        """
        self._assert_container_in_cache(cached, container_name, namespace, hash_func, **kwargs)


class SingularityContainerResolverTestCase(DockerContainerResolverTestCase):
    """
    analogous to DockerContainerResolverTestCase, just for singularity
    provides adapted methods for clearing and checking the container cache
    """

    container_type: str = "singularity"

    def _assert_container_in_cache(
        self,
        cached: bool,
        container_name: str,
        namespace: Optional[str] = None,
        hash_func: Literal["v1", "v2"] = "v2",
        **kwargs,
    ) -> None:
        """
        see TestMulledContainerResolver

        checks if the image is in the container_image_cache_path/container_type/resolver_type/
        where
        - container_type is singularity/docker and
        - resolver_type the used resolver, will use only "mulled"/"explicit"
        """
        cache_directory = os.path.join(self._app.config.container_image_cache_path, self.container_type)
        if "resolver_type" in kwargs:
            resolver_type = kwargs["resolver_type"]
            if "mulled" in resolver_type:
                resolver_type = "mulled"
            elif "explicit" in resolver_type or "mapping" in resolver_type:
                resolver_type = "explicit"
            else:
                raise AssertionError(f"Unknown resolver_type {resolver_type}")
            cache_directory = os.path.join(cache_directory, resolver_type)
        _assert_container_in_cache_singularity(cache_directory, cached, container_name, namespace, hash_func)


class ContainerResolverTestProtocol(Protocol):
    """
    Helper class defining methods and properties needed to
    use ContainerResolverTestCases
    """

    @property
    def tool_id(self) -> str:
        """the id of the tool used in the tests"""
        ...

    @property
    def assumptions(self) -> Dict[str, Any]:
        """a dictionary storing the assumptions of the three tests

        needs to contain 3 keys ("run", "list", "build")

        run: a dict
        - output: a list of output strings expected in the tools output
        - cached: a boolean specifying if the container is cached (container can be computed by the following 3 keys)
        - resolver_type: name of the container resolver (at the moment only used to get the path of singularity images, i.e. checks only for mulled/explicit)
        - cache_name: the name of the container in the cache
        - cache_namespace: only used for testing docker container resolvers (for restricting which containers are considered)
        - expect_failure: optional boolean specifying if the tool is expected to fail

        list/build: list of length two containing dicts, the two dicts represent
        assumptions for the results of the two API calls that are made
        - resolver_type: see run
        - identifier: identifier returned by the resolver
        - cached, cache_name, cache_namespace: see run
        """
        ...

    @property
    def container_type(self) -> Literal["docker", "singularity"]:
        """
        container type
        """
        ...

    def _assert_container_in_cache(
        self,
        cached: bool,
        container_name: str,
        namespace: Optional[str] = None,
        hash_func: Literal["v1", "v2"] = "v2",
        **kwargs,
    ) -> None:
        """
        function to assert if/if not a container is in the cache after the job run test
        """
        ...

    def _assert_container_in_cache_api_calls(
        self,
        cached: bool,
        container_name: str,
        namespace: Optional[str] = None,
        hash_func: Literal["v1", "v2"] = "v2",
        **kwargs,
    ) -> None:
        """
        function to assert if/if not a container is in the cache after the API call test(s)
        """
        ...

    def _check_status(self, status: Dict[str, Any], assumptions: Dict[str, Any]) -> None:
        """
        function to check the status of a API call against assumptions dict
        """
        ...

    # The remaining methods are implemented in IntegrationTestCase
    @property
    def dataset_populator(self) -> DatasetPopulator: ...

    def _assert_status_code_is(self, response: "Response", expected_status_code: int) -> None:
        """
        check status code of the too run
        """
        ...

    def _get(self, route, data=None, headers=None, admin=False) -> "Response":
        """
        do a GET API call
        """
        ...

    def _post(self, route, data=None, files=None, headers=None, admin=False, json: bool = False) -> "Response":
        """
        do a POST API call
        """
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

    Note, the big difference between the run test and the API call tests is that the later
    do not set the container type. For running a job the container type is knows from the destination
    but for listing and building containers the AdminUI does not set a container type.
    """

    def test_tool_run(self: ContainerResolverTestProtocol, history_id: str) -> None:
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
            # check if container is cached also if the tool failed, because the container
            # may be cached prior to job run (ie independent of the job status)
            self._assert_container_in_cache(
                self.assumptions["run"]["cached"],
                container_name=self.assumptions["run"]["cache_name"],
                namespace=self.assumptions["run"]["cache_namespace"],
                resolver_type=self.assumptions["run"]["resolver_type"],
            )
            if not self.assumptions["run"].get("expect_failure", False):
                raise AssertionError("test_tool_run is not expected to fail")
        else:
            # and (of course) check if container is cached when tool was successful
            self._assert_container_in_cache(
                self.assumptions["run"]["cached"],
                container_name=self.assumptions["run"]["cache_name"],
                namespace=self.assumptions["run"]["cache_namespace"],
                resolver_type=self.assumptions["run"]["resolver_type"],
            )
            if self.assumptions["run"].get("expect_failure", False):
                raise AssertionError("test_tool_run is expected to fail")
        if not self.assumptions["run"].get("expect_failure", False):
            output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
            for o in self.assumptions["run"]["output"]:
                assert o in output

    def _check_status(self: ContainerResolverTestProtocol, status: Dict[str, Any], assumptions: Dict[str, Any]) -> None:
        """see ContainerResolverTestProtocol._check_status"""
        if "unresolved" in assumptions:
            assert status["model_class"] == "NullDependency"
            assert status["dependency_type"] is None
            assert "container_resolver" not in status
            assert "container_description" not in status
        else:
            assert status["model_class"] == "ContainerDependency"
            # we could also test here for == self.container_type, but it does not work
            # for DefaultSingularity... and the resolver_type should be sufficient since
            # it implies the container_type
            assert status["dependency_type"] is not None
            assert status["container_resolver"]["resolver_type"] == assumptions["resolver_type"]
            assert re.match(assumptions["identifier"], status["container_description"]["identifier"])
            self._assert_container_in_cache_api_calls(
                assumptions["cached"],
                container_name=assumptions["cache_name"],
                namespace=assumptions["cache_namespace"],
                resolver_type=assumptions["resolver_type"],
            )

    def test_api_container_resolvers_toolbox(self: ContainerResolverTestProtocol) -> None:
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
            },
            admin=True,
        )
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        self._check_status(status, self.assumptions["list"][1])

    def test_api_container_resolvers_toolbox_install(self: ContainerResolverTestProtocol) -> None:
        """
        test container resolvers via POST container_resolvers/toolbox/install

        which is what happens when building a container in the admin UI
        Two calls are necessary, because the 1st may cache a container and the
        second call then uses a different resolver.
        """
        create_response = self._post(
            "container_resolvers/toolbox/install",
            data={
                "tool_ids": json.dumps([self.tool_id]),
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
            },
            admin=True,
        )
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        self._check_status(status, self.assumptions["build"][1])


class MulledTestCase:
    tool_id = "mulled_example_multi_1"
    mulled_hash = "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0"


class MulledTestCaseWithBuildInfo:
    tool_id = "mulled_example_multi_2"
    mulled_hash = "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0"


class TestDefaultContainerResolvers(DockerContainerResolverTestCase, ContainerResolverTestCases, MulledTestCase):
    """
    Test default container resolvers

    - container is cached on tool run and when building
    - listing containers does not cache them
    """

    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "bedtools v2.26.0",
                "samtools: error while loading shared libraries: libcrypto.so.1.0.0",
            ],
            "cached": True,
            "resolver_type": "mulled",  # only used to check mulled / explicit
            "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }


class TestDefaultContainerResolversWithBuildInfo(
    DockerContainerResolverTestCase, ContainerResolverTestCases, MulledTestCaseWithBuildInfo
):
    """
    Same as TestDefaultContainerResolvers but with a tool using build info
    serves to check if the mulled hashes are cumputed correctly
    """

    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "bedtools v2.26.0",
                "samtools: error while loading shared libraries: libcrypto.so.1.0.0",
            ],
            "cached": True,
            "resolver_type": "mulled",  # only used to check mulled / explicit
            "cache_name": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCaseWithBuildInfo.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }


class TestDefaultSingularityContainerResolvers(
    SingularityContainerResolverTestCase, ContainerResolverTestCases, MulledTestCase
):
    """
    Test default resolvers on a instance with a singularity destination

    - for the run test the singularity resolvers are used and the singularity container is cached
      this is because the destination restricts the enabled container types (to singularity in this case)
    - BUT the API calls for listing and building use the docker resolvers (which are included in the list
      of default container resolvers) because all container types are enabled.
      therefore the docker container resolvers are used, because they are listed before singularity container resolvers
      (note that in addition to the difference in the assumptions [list and build are as in TestDefaultContainerResolvers]
      also _assert_container_in_cache_api_calls is overwritten
    """

    assumptions = {
        "run": {
            "output": [
                "bedtools v2.26.0",
                "samtools: error while loading shared libraries: libcrypto.so.1.0.0",
            ],
            "cached": True,
            "resolver_type": "mulled_singularity",  # only used to check mulled / explicit
            "cache_name": MulledTestCase.mulled_hash,
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }

    def _assert_container_in_cache_api_calls(
        self,
        cached: bool,
        container_name: str,
        namespace: Optional[str] = None,
        hash_func: Literal["v1", "v2"] = "v2",
        **kwargs,
    ) -> None:
        _assert_container_in_cache_docker(cached, container_name, namespace, hash_func)


class TestMulledContainerResolvers(DockerContainerResolverTestCase, ContainerResolverTestCases, MulledTestCase):
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
            "resolver_type": "mulled",
            "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled",
                "identifier": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestMulledSingularityContainerResolvers(
    SingularityContainerResolverTestCase, ContainerResolverTestCases, MulledTestCase
):
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
            "resolver_type": "mulled_singularity",
            "cache_name": MulledTestCase.mulled_hash,
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": f"docker://quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled_singularity",
                "identifier": f"docker://quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": f"docker://quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled_singularity",
                "identifier": f"/tmp/.*/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestMulledContainerResolversNoAutoInstall(TestMulledContainerResolvers):
    """
    Use the mulled (docker) container resolver with auto_install: False

    No difference (since the cached name is identical to the URI)
    """

    container_resolvers_config: List[Dict[str, Any]] = [
        {
            "type": "cached_mulled",
        },
        {"type": "mulled", "auto_install": False},
    ]

    pass


class TestMulledSingularityContainersResolversNoAutoInstall(TestMulledSingularityContainerResolvers):
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

    assumptions = {
        "run": {
            "expect_failure": False,
            "output": [
                "bedtools v2.26.0",
                "samtools: error while loading shared libraries: libcrypto.so.1.0.0",
            ],
            "cached": True,
            "resolver_type": "mulled_singularity",
            "cache_name": MulledTestCase.mulled_hash,
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": f"docker://quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "mulled_singularity",
                "identifier": f"docker://quay.io/biocontainers/{MulledTestCase.mulled_hash}",
                "cached": False,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "mulled_singularity",
                "identifier": f"/tmp/.*/database/container_cache/singularity/mulled/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_mulled_singularity",
                "identifier": f"/tmp/.*/database/container_cache/singularity/mulled/{MulledTestCase.mulled_hash}",
                "cached": True,
                "cache_name": MulledTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
    }


class TestCondaFallBack(DockerContainerResolverTestCase, ContainerResolverTestCases, MulledTestCase):
    """
    test that Galaxy falls back to default dependency resolvers (i.e. conda) if no
    container can be resolved

    here we force container resolution to fail because only singularity resolvers
    are configured on a docker destination.

    - assumptions that need to be met is that tool is executed successfully (via conda)
    - and listing and building containers does not work
    """

    allow_conda_fallback: bool = True
    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "null"},
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
            "resolver_type": "bogus",
            "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
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


class TestCondaFallBackAndRequireContainer(DockerContainerResolverTestCase, ContainerResolverTestCases, MulledTestCase):
    """
    test that we can disable fallback to the default resolvers (conda)
    by setting the destination property `require_container`

    same as TestCondaFallBack but tool needs to fail
    """

    allow_conda_fallback: bool = True
    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "null"},
    ]

    assumptions: Dict[str, Any] = {
        "run": {
            "expect_failure": True,
            "cached": False,
            "resolver_type": "bogus",
            "cache_name": f"quay.io/biocontainers/{MulledTestCase.mulled_hash}",
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
        config["job_config"] = {
            "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
            "execution": {
                "default": "local_docker",
                "environments": {
                    "local_docker": {"runner": "local", "docker_enabled": True, "require_container": True},
                },
            },
            "tools": [
                {"id": "upload1", "environment": "local_upload"},
            ],
        }
        config["container_resolvers"] = cls.container_resolvers_config


class ExplicitTestCase:
    tool_id = "explicit_container"
    mulled_hash = "quay.io/biocontainers/bwa:0.7.17--h7132678_9"


class ExplicitSingularityTestCase:
    tool_id = "explicit_singularity_container"
    mulled_hash = "shub://GodloveD/lolcow-installer:latest"


class TestExplicitContainerResolver(DockerContainerResolverTestCase, ContainerResolverTestCases, ExplicitTestCase):
    """
    test explict container resolver

    - run caches the container (even though ist by name uncached the `docker pull`
      in the job script will lead to a cache entry)
    - list and build resolve the URI and do not cache the container
    """

    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "explicit"},
    ]
    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "Program: bwa (alignment via Burrows-Wheeler transformation)",
                "Version: 0.7.17-r1188",
            ],
            "cached": True,
            "resolver_type": "explicit",
            "cache_name": f"{ExplicitTestCase.mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "explicit",
                "identifier": f"{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "explicit",
                "identifier": f"{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "explicit",
                "identifier": f"{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "explicit",
                "identifier": f"{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestExplicitSingularityContainerResolver(
    SingularityContainerResolverTestCase, ContainerResolverTestCases, ExplicitTestCase
):
    """
    test explict_singularity container resolver

    - in contrast to explicit run does not cache the container (so it behaves uncached as the may name suggest
      .. but in contrast to mulled which caches :( ). reason is that for singularity no pull
      command is in the job script
    - list and build resolve the URI and do not cache the container
    """

    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "explicit_singularity"},
    ]
    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "Program: bwa (alignment via Burrows-Wheeler transformation)",
                "Version: 0.7.17-r1188",
            ],
            "cached": False,
            "resolver_type": "explicit_singularity",
            "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "explicit_singularity",
                "identifier": f"docker://{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "explicit_singularity",
                "identifier": f"docker://{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "explicit_singularity",
                "identifier": f"docker://{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "explicit_singularity",
                "identifier": f"docker://{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestCachedExplicitSingularityContainerResolver(
    SingularityContainerResolverTestCase, ContainerResolverTestCases, ExplicitTestCase
):
    """
    test cached_explict_singularity container resolver

    - list resolves to the path irrespective if the path is existent (TODO bug?)
    """

    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "cached_explicit_singularity"},
    ]
    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "Program: bwa (alignment via Burrows-Wheeler transformation)",
                "Version: 0.7.17-r1188",
            ],
            "cached": True,
            "resolver_type": "cached_explicit_singularity",
            "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/singularity/explicit/docker:/{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/singularity/explicit/docker:/{ExplicitTestCase.mulled_hash}",
                "cached": False,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/{ExplicitTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/{ExplicitTestCase.mulled_hash}",
                "cached": True,
                "cache_name": f"docker:/{ExplicitTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config


class TestCachedExplicitSingularityContainerResolverWithSingularityRequirement(
    SingularityContainerResolverTestCase, ContainerResolverTestCases, ExplicitSingularityTestCase
):
    """
    test cached_explict_singularity container resolver for a tool with singularity container requirement

    same as for tools with docker requirement, but the shub:// will be
    represented by `shub:/` in the cached path therefore we need to call replace
    here
    """

    container_resolvers_config: List[Dict[str, Any]] = [
        {"type": "cached_explicit_singularity"},
    ]
    assumptions: Dict[str, Any] = {
        "run": {
            "output": [
                "cowsay works LOL",
            ],
            "cached": False,
            "resolver_type": "cached_explicit_singularity",
            "cache_name": f"quay.io/biocontainers/{ExplicitSingularityTestCase.mulled_hash}",
            "cache_namespace": "biocontainers",
        },
        "list": [
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/database/container_cache/singularity/explicit/{ExplicitSingularityTestCase.mulled_hash}".replace(
                    "//", "/"
                ),
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{ExplicitSingularityTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/database/container_cache/singularity/explicit/{ExplicitSingularityTestCase.mulled_hash}".replace(
                    "//", "/"
                ),
                "cached": False,
                "cache_name": f"quay.io/biocontainers/{ExplicitSingularityTestCase.mulled_hash}",
                "cache_namespace": "biocontainers",
            },
        ],
        "build": [
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/database/container_cache/singularity/explicit/{ExplicitSingularityTestCase.mulled_hash}".replace(
                    "//", "/"
                ),
                "cached": True,
                "cache_name": ExplicitSingularityTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
            {
                "resolver_type": "cached_explicit_singularity",
                "identifier": f"/tmp/.*/database/container_cache/singularity/explicit/{ExplicitSingularityTestCase.mulled_hash}".replace(
                    "//", "/"
                ),
                "cached": True,
                "cache_name": ExplicitSingularityTestCase.mulled_hash,
                "cache_namespace": "biocontainers",
            },
        ],
    }

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["container_resolvers"] = cls.container_resolvers_config
