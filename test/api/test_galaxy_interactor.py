# Test galaxy interactor

from packaging.version import Version

from base import api   # noqa: I100,I202


class GalaxyInteractorBackwardCompatTestCase(api.ApiTestCase):

    def test_local_test_data_download(self):
        self.galaxy_interactor._target_galaxy_version = Version("18.09")
        assert self.galaxy_interactor.supports_test_data_download is False
        assert self.galaxy_interactor.test_data_download(tool_id='cat1', filename='1.bed').readline().startswith(b'chr1\t147962192\t147962580')
