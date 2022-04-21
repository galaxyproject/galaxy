"""Integration tests for GalaxyInteractor."""

from packaging.version import Version

from galaxy_test.driver import integration_util


class GalaxyInteractorTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def test_local_test_data_download(self):
        self.galaxy_interactor._target_galaxy_version = Version("18.09")
        assert self.galaxy_interactor.supports_test_data_download is False
        assert self.galaxy_interactor.test_data_download(tool_id="cat1", filename="1.bed").startswith(
            b"chr1\t147962192\t147962580"
        )

    def test_run_test_select_version(self):
        self._run_tool_test(tool_id="multiple_versions", tool_version="0.1")

    def test_get_tool_tests(self):
        # test that get_tool_tests will return the right tests when the tool_version has a '+' in it
        test_data = self.galaxy_interactor.get_tool_tests(tool_id="multiple_versions", tool_version="0.1+galaxy6")
        print(test_data)
        assert isinstance(test_data, list)
        assert len(test_data) > 0
        assert isinstance(test_data[0], dict)
        assert test_data[0].get("tool_version") == "0.1+galaxy6"

        test_data = self.galaxy_interactor.get_tool_tests(
            tool_id="multiple_versions"
        )  # test that tool_version=None does not break it
        assert isinstance(test_data, list)
        assert len(test_data) > 0
        assert isinstance(test_data[0], dict)
