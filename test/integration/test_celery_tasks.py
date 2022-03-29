from celery import shared_task

from galaxy.celery import galaxy_task
from galaxy.celery.tasks import purge_hda
from galaxy.model import HistoryDatasetAssociation
from galaxy.schema.schema import CreatePagePayload
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


@shared_task
def mul(x, y):
    return x * y


@galaxy_task
def process_page(request: CreatePagePayload):
    # an example task that consumes a pydantic model
    return f"content_format is {request.content_format} with annotation {request.annotation}"


class CeleryTasksIntegrationTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_random_simple_task_to_verify_framework_for_testing(self):
        assert mul.delay(4, 4).get(timeout=10) == 16

    def test_task_with_pydantic_argument(self):
        request = CreatePagePayload(
            content_format="markdown",
            title="my cool title",
            slug="my-cool-title",
            annotation="my cool annotation",
        )
        assert (
            process_page.delay(request).get(timeout=10)
            == "content_format is markdown with annotation my cool annotation"
        )

    def test_galaxy_task(self):
        history_id = self.dataset_populator.new_history()
        dataset = self.dataset_populator.new_dataset(history_id, wait=True)
        hda = self._latest_hda
        assert hda

        def hda_purged():
            latest_details = self.dataset_populator.get_history_dataset_details(
                history_id, dataset=dataset, assert_ok=False, wait=False
            )
            return True if latest_details["purged"] else None

        assert not hda_purged()

        purge_hda.delay(hda_id=hda.id).get(timeout=10)

        wait_on(hda_purged, "dataset to become purged")
        assert hda_purged()

    @property
    def _latest_hda(self):
        latest_hda = (
            self._app.model.session.query(HistoryDatasetAssociation)
            .order_by(HistoryDatasetAssociation.table.c.id.desc())
            .first()
        )
        return latest_hda
