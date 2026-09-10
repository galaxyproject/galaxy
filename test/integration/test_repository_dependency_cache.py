"""Integration tests for dependency caching during Tool Shed installation."""

from pathlib import Path

from galaxy.tool_util.deps.resolvers import (
    Dependency,
    DependencyException,
    DependencyResolver,
)
from galaxy_test.base.uses_shed_api import DEFAULT_TOOL_SHED_URL
from galaxy_test.driver import integration_util
from galaxy_test.driver.uses_shed import UsesShed


class FailingCacheDependency(Dependency):
    dependency_type = "test"
    cacheable = True

    def __init__(self, requirement, resolver):
        self.name = requirement.name
        self.version = requirement.version
        self.resolver = resolver

    @property
    def exact(self):
        return True

    def build_cache(self, cache_path):
        self.resolver.cache_build_attempts += 1
        raise DependencyException("Controlled cache construction failure")

    def shell_commands(self):
        return ""


class FailingCacheDependencyResolver(DependencyResolver):
    resolver_type = "test"

    def __init__(self):
        self.cache_build_attempts = 0

    def resolve(self, requirement, **kwds):
        return FailingCacheDependency(requirement, self)


class TestRepositoryDependencyCacheFailure(integration_util.IntegrationTestCase, UsesShed):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed(config)
        config["use_cached_dependency_manager"] = True
        config["conda_auto_init"] = False

    def setUp(self):
        super().setUp()
        self.setup_shed_config()

    def tearDown(self):
        self.reset_shed_tools()
        return super().tearDown()

    def test_cache_failure_does_not_remove_installed_repository(self):
        dependency_manager = self._app.toolbox.dependency_manager
        assert dependency_manager.cached
        resolver = FailingCacheDependencyResolver()
        original_resolvers = dependency_manager.dependency_resolvers
        dependency_manager.dependency_resolvers = [resolver]
        try:
            response = self.install_repo_request(
                {
                    "tool_shed_url": DEFAULT_TOOL_SHED_URL,
                    "name": "fastqc",
                    "owner": "devteam",
                    "changeset_revision": "e7b2202befea",
                    "install_resolver_dependencies": True,
                }
            )
        finally:
            dependency_manager.dependency_resolvers = original_resolvers

        self._assert_status_code_is(response, 200)
        repositories = response.json()
        assert len(repositories) == 1
        assert repositories[0]["status"] == "Installed"
        assert resolver.cache_build_attempts == 1
        repository_path = (
            Path(self._app.config.shed_tools_dir)
            / "toolshed.g2.bx.psu.edu"
            / "repos"
            / "devteam"
            / "fastqc"
            / "e7b2202befea"
        )
        assert repository_path.is_dir()
        installed_repository = self.get_installed_repository_for("devteam", "fastqc", "e7b2202befea")
        assert installed_repository
        assert installed_repository["status"] == "Installed"
