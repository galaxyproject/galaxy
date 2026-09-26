import tarfile

from celery import shared_task
from sqlalchemy import select

from galaxy.celery import galaxy_task
from galaxy.celery.tasks import (
    prepare_pdf_download,
    purge_hda,
)
from galaxy.model import HistoryDatasetAssociation
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema import PdfDocumentType
from galaxy.schema.schema import CreatePagePayload
from galaxy.schema.tasks import GeneratePdfDownload
from galaxy.short_term_storage import ShortTermStorageAllocator
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


@galaxy_task
def invalidate_connection(sa_session: galaxy_scoped_session):
    sa_session().connection().invalidate()


@galaxy_task
def use_session(sa_session: galaxy_scoped_session):
    sa_session().query(HistoryDatasetAssociation).get(1)


class TestCeleryTasksIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_recover_from_invalid_connection(self):
        invalidate_connection.delay().get()
        use_session.delay().get()

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

    def test_pdf_download(self):
        short_term_storage_allocator = self._app[ShortTermStorageAllocator]  # type: ignore[type-abstract]
        short_term_storage_target = short_term_storage_allocator.new_target("moo.pdf", "application/pdf")
        request_id = short_term_storage_target.request_id
        pdf_download_request = GeneratePdfDownload(
            basic_markdown="*Hello World!*",
            document_type=PdfDocumentType.page,
            short_term_storage_request_id=request_id,
        )
        prepare_pdf_download.delay(request=pdf_download_request)
        contents = self.dataset_populator.wait_on_download_request(request_id)
        contents.raise_for_status()
        assert "application/pdf" in contents.headers["content-type"]
        assert contents.content[0:4] == b"%PDF"

    def test_import_export_history_contents(self):
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset(history_id, wait=True)

        contents = hda1
        temp_tar = self.dataset_populator.download_contents_to_store(history_id, contents, "tgz")
        with tarfile.open(name=temp_tar) as tf:
            assert "datasets_attrs.txt" in tf.getnames()

        second_history_id = self.dataset_populator.new_history()
        as_list = self.dataset_populator.create_contents_from_store(
            second_history_id,
            store_path=temp_tar,
        )
        assert len(as_list) == 1
        new_hda = as_list[0]
        assert new_hda["model_class"] == "HistoryDatasetAssociation"
        assert new_hda["state"] == "discarded"
        assert not new_hda["deleted"]

    @property
    def _latest_hda(self):
        stmt = select(HistoryDatasetAssociation).order_by(HistoryDatasetAssociation.table.c.id.desc()).limit(1)
        return self._app.model.session.scalars(stmt).first()
