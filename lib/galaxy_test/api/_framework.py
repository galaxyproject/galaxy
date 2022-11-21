from typing import (
    Iterator,
    Optional,
)

import pytest

from galaxy_test.base.api import (
    UsesApiTestCaseMixin,
    UsesCeleryTasks,
)
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.base.testcase import GalaxyFunctionalTestCase


class ApiTestCase(GalaxyFunctionalTestCase, UsesApiTestCaseMixin, UsesCeleryTasks):
    dataset_populator: Optional[DatasetPopulator]

    def setUp(self):
        super().setUp()
        self._setup_interactor()

    @pytest.fixture
    def history_id(self) -> Iterator[str]:
        assert self.dataset_populator
        with self.dataset_populator.test_history() as history_id:
            yield history_id


__all__ = ("ApiTestCase",)
