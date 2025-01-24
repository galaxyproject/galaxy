from ..base.api import ShedApiTestCase


class TestShedConfigurationApi(ShedApiTestCase):
    def test_version(self) -> None:
        version = self.populator.version()
        assert version.version
        assert version.version_major
