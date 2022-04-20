"""Integration tests for dependency resolution."""
import os
from tempfile import mkdtemp
from typing import ClassVar

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

GNUPLOT = {"version": "4.6", "type": "package", "name": "gnuplot"}


class CondaResolutionIntegrationTestCase(integration_util.IntegrationTestCase):

    """Test conda dependency resolution through API."""

    framework_tool_and_types = True
    conda_tmp_prefix: ClassVar[str]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.conda_tmp_prefix = mkdtemp()
        cls._test_driver.temp_directories.append(cls.conda_tmp_prefix)
        config["use_cached_dependency_manager"] = True
        config["conda_auto_init"] = True
        config["conda_prefix"] = os.path.join(cls.conda_tmp_prefix, "conda")

    def test_dependency_before_install(self):
        """
        Test that dependency is not installed (response['dependency_type'] == 'null').
        """
        data = GNUPLOT
        create_response = self._get("dependency_resolvers/dependency", data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert response["dependency_type"] is None and response["exact"]

    def test_dependency_install(self):
        """
        Test installation of GNUPLOT dependency.
        """
        data = GNUPLOT
        create_response = self._post("dependency_resolvers/dependency", data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        self._assert_dependency_type(response)
        # Verify GET request
        create_response = self._get("dependency_resolvers/dependency", data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        self._assert_dependency_type(response)

    def test_dependency_install_not_exact(self):
        """
        Test installation of gnuplot with a version that does not exist.
        """
        data = GNUPLOT.copy()
        data["version"] = "4.9999"
        create_response = self._post("dependency_resolvers/dependency", data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        self._assert_dependency_type(response, exact=False)
        # Verify GET request
        create_response = self._get("dependency_resolvers/dependency", data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        self._assert_dependency_type(response, exact=False)

    def test_legacy_r_mapping(self):
        """ """
        tool_id = "legacy_R"
        dataset_populator = DatasetPopulator(self.galaxy_interactor)
        history_id = dataset_populator.new_history()
        endpoint = "tools/%s/install_dependencies" % tool_id
        data = {"id": tool_id}
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        payload = dataset_populator.run_tool_payload(
            tool_id=tool_id,
            inputs={},
            history_id=history_id,
        )
        create_response = self._post("tools", data=payload)
        self._assert_status_code_is(create_response, 200)
        dataset_populator.wait_for_history(history_id, assert_ok=True)

    def test_conda_install_through_tools_api(self):
        tool_id = "mulled_example_multi_1"
        endpoint = "tools/%s/install_dependencies" % tool_id
        data = {"id": tool_id}
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert any(True for d in response if d["dependency_type"] == "conda")
        endpoint = "tools/%s/build_dependency_cache" % tool_id
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)

    def test_uninstall_through_tools_api(self):
        tool_id = "mulled_example_multi_1"
        endpoint = "tools/%s/dependencies" % tool_id
        data = {"id": tool_id}
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert any(True for d in response if d["dependency_type"] == "conda")
        endpoint = "tools/%s/dependencies" % tool_id
        create_response = self._delete(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert not [True for d in response if d["dependency_type"] == "conda"]

    def _uninstall_mulled_example_multi_1(self, resolver_type=None):
        tool_id = "mulled_example_multi_1"
        endpoint = "tools/%s/dependencies" % tool_id
        data = {"id": tool_id, "resolver_type": resolver_type}
        create_response = self._delete(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert not [True for d in response if d["dependency_type"] == "conda"]

    def test_conda_install_with_resolver_type_via_tools_api(self):
        # Makes sure dependency is not already installed
        self._uninstall_mulled_example_multi_1(resolver_type="conda")
        # Now do the actual test
        tool_id = "mulled_example_multi_1"
        endpoint = "tools/%s/dependencies" % tool_id
        data = {"id": tool_id, "resolver_type": "conda"}
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert any(True for d in response if d["dependency_type"] == "conda")
        # Now that we know install was successfullt we can also doube check that the uninstall works
        self._uninstall_mulled_example_multi_1(resolver_type="conda")

    def test_conda_clean(self):
        endpoint = "dependency_resolvers/clean"
        create_response = self._post(endpoint, data={}, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert response == "OK"

    def _assert_dependency_type(self, response, type="conda", exact=True):
        if "dependency_type" not in response:
            raise Exception("Response [%s] did not contain key 'dependency_type'" % response)
        dependency_type = response["dependency_type"]
        assert dependency_type == type, f"Dependency type [{dependency_type}] not the expected value [{type}]"
        if "exact" not in response:
            raise Exception("Response [%s] did not contain key 'exact'" % response)
        assert response["exact"] is exact
