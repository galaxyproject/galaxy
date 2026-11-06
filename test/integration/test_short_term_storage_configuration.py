from galaxy.short_term_storage import ShortTermStorageAllocator
from galaxy_test.driver import integration_util


class _BaseEffectiveDurationIntegrationTestCase(integration_util.IntegrationTestCase):
    def assert_api_and_new_targets_report(self, expected: int):
        response = self.galaxy_interactor.get("configuration")
        response.raise_for_status()
        assert response.json()["short_term_storage_effective_duration"] == expected
        allocator = self._app[ShortTermStorageAllocator]  # type: ignore[type-abstract]
        assert allocator.new_target("a.txt", "text/plain").duration == expected


class TestEffectiveDurationNoMaximum(_BaseEffectiveDurationIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["short_term_storage_default_duration"] = 172800

    def test_uses_the_default(self):
        self.assert_api_and_new_targets_report(172800)


class TestEffectiveDurationCapped(_BaseEffectiveDurationIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["short_term_storage_default_duration"] = 604800
        config["short_term_storage_maximum_duration"] = 3600

    def test_caps_at_the_maximum(self):
        self.assert_api_and_new_targets_report(3600)
