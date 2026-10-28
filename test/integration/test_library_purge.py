from galaxy import model
from galaxy_test.base.populators import (
    DatasetPopulator,
    LibraryPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestLibraryPurgeIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    library_populator: LibraryPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    def test_delete_library_item_keeps_versions(self):
        library, file_id = self._new_library_item()
        expired_ldda_id = self._add_version(file_id)

        self.library_populator.delete_library_item(library["id"], file_id)

        session = self._session()
        library_dataset = session.get(model.LibraryDataset, self._decode_id(file_id))
        assert library_dataset.deleted is True
        assert library_dataset.purged is False
        assert library_dataset.library_dataset_dataset_association.deleted is False
        assert session.get(model.LibraryDatasetDatasetAssociation, expired_ldda_id).deleted is False

    def test_purge_library_item_retires_all_versions(self):
        library, file_id = self._new_library_item()
        expired_ldda_id = self._add_version(file_id)

        self.library_populator.delete_library_item(library["id"], file_id, purge=True)

        session = self._session()
        library_dataset = session.get(model.LibraryDataset, self._decode_id(file_id))
        assert library_dataset.deleted is True
        assert library_dataset.purged is True
        assert library_dataset.library_dataset_dataset_association.deleted is True
        assert session.get(model.LibraryDatasetDatasetAssociation, expired_ldda_id).deleted is True

    def _new_library_item(self):
        library = self.library_populator.new_private_library("TestLibraryPurge")
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, wait=True)["id"]
        payload = {"folder_id": library["root_folder_id"], "create_type": "file", "from_hda_id": hda_id}
        response = self._post(f"/api/libraries/{library['id']}/contents", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        return library, response.json()["library_dataset_id"]

    def _session(self):
        session = self._app.model.session
        session.rollback()
        return session

    def _add_version(self, encoded_id):
        """Add a version and make it current, returning the id of the now-expired one."""
        session = self._session()
        library_dataset = session.get(model.LibraryDataset, self._decode_id(encoded_id))
        current_ldda = library_dataset.library_dataset_dataset_association
        new_ldda = model.LibraryDatasetDatasetAssociation(
            dataset=current_ldda.dataset, user=current_ldda.user, name="new version"
        )
        new_ldda.library_dataset = library_dataset
        session.add(new_ldda)
        session.flush()
        previous_ldda_id = current_ldda.id
        library_dataset.library_dataset_dataset_association = new_ldda
        session.commit()
        return previous_ldda_id
