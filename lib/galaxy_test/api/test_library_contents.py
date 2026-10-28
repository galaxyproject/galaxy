from galaxy import model
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
)
from ._framework import ApiTestCase


class TestLibraryContentsApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

        self.library = self.library_populator.new_private_library("TestLibrary")
        self.history = self.dataset_populator.new_history()

    def test_create_folder(self):
        folder_list = self._create_library_content(type="folder")
        assert isinstance(folder_list, list), "Expected response to be a list"
        for folder in folder_list:
            self._assert_has_keys(folder, "id", "name")

    def test_create_file_from_hda(self):
        file_item = self._create_library_content(type="from_hda")
        self._assert_has_keys(file_item, "id", "name")

    def test_create_file_from_hdca(self):
        files = self._create_library_content(type="from_hdca")
        assert isinstance(files, list), "Response should be a list of files"
        for file_item in files:
            self._assert_has_keys(file_item, "id", "name")

    def test_create_invalid(self):
        library_id = self.library["id"]
        folder_id = self.library["root_folder_id"]

        payload = {"folder_id": folder_id, "create_type": "invalid_type"}
        response = self._post(f"/api/libraries/{library_id}/contents", data=payload, json=True)
        self._assert_status_code_is(response, 400)

    def test_index(self):
        library_id = self.library["id"]
        response = self._get(f"/api/libraries/{library_id}/contents")
        self._assert_status_code_is(response, 200)

        contents = response.json()
        assert isinstance(contents, list), "Expected response to be a list"

        for item in contents:
            self._assert_has_keys(item, "id", "name", "type", "url")

    def test_get_library_contents_invalid_id(self):
        invalid_library_id = "invalid_id"
        response = self._get(f"/api/libraries/{invalid_library_id}/contents")
        self._assert_status_code_is(response, 400)

    def test_get_library_folder(self):
        library_id = self.library["id"]
        folder_id = self._create_library_content(type="folder")[0]["id"]
        response = self._get(f"/api/libraries/{library_id}/contents/{folder_id}")
        self._assert_status_code_is(response, 200)

        folder_info = response.json()
        self._assert_has_keys(
            folder_info,
            "model_class",
            "id",
            "parent_id",
            "name",
            "description",
            "item_count",
            "genome_build",
            "update_time",
            "deleted",
            "library_path",
            "parent_library_id",
        )

    def test_get_library_file_from_hda(self):
        library_id = self.library["id"]
        file_id = self._create_library_content(type="from_hda")["id"]
        response = self._get(f"/api/libraries/{library_id}/contents/{file_id}")
        self._assert_status_code_is(response, 200)

        file_info = response.json()
        self._assert_has_keys(
            file_info,
            "id",
            "ldda_id",
            "parent_library_id",
            "folder_id",
            "model_class",
            "state",
            "name",
            "file_name",
            "created_from_basename",
            "uploaded_by",
            "message",
            "date_uploaded",
            "update_time",
            "file_size",
            "file_ext",
            "data_type",
            "genome_build",
            "misc_info",
            "misc_blurb",
            "peek",
            "uuid",
            "metadata_dbkey",
            "metadata_data_lines",
            "tags",
        )

    def test_get_library_file_from_hdca(self):
        library_id = self.library["id"]
        file_id = self._create_library_content(type="from_hdca")[0]["id"]
        response = self._get(f"/api/libraries/{library_id}/contents/{file_id}")
        self._assert_status_code_is(response, 200)

        file_info = response.json()
        self._assert_has_keys(
            file_info,
            "id",
            "ldda_id",
            "parent_library_id",
            "folder_id",
            "model_class",
            "state",
            "name",
            "file_name",
            "created_from_basename",
            "uploaded_by",
            "message",
            "date_uploaded",
            "update_time",
            "file_size",
            "file_ext",
            "data_type",
            "genome_build",
            "misc_info",
            "misc_blurb",
            "peek",
            "uuid",
            "metadata_dbkey",
            "metadata_data_lines",
            "tags",
        )

    def test_get_invalid_library_item(self):
        library_id = self.library["id"]
        invalid_item_id = "invalid_id"
        response = self._get(f"/api/libraries/{library_id}/contents/{invalid_item_id}")
        self._assert_status_code_is(response, 400)

    def test_delete_library_item_from_hda(self):
        library_id = self.library["id"]
        file_id = self._create_library_content(type="from_hda")["id"]
        ldda_id = self.library_populator.show_ld(library_id, file_id)["ldda_id"]

        response = self._delete(f"/api/libraries/{library_id}/contents/{file_id}")
        self._assert_status_code_is(response, 200)
        # deleting is reversible, so the current version stays live
        assert self.library_populator.show_ldda(ldda_id)["deleted"] is False

    def test_delete_library_item_from_hdca(self):
        library_id = self.library["id"]
        file_id = self._create_library_content(type="from_hdca")[0]["id"]

        response = self._delete(f"/api/libraries/{library_id}/contents/{file_id}")
        self._assert_status_code_is(response, 200)

    def test_delete_library_item_from_hda_purged(self):
        library_id = self.library["id"]
        file_id = self._create_library_content(type="from_hda")["id"]
        ldda_id = self.library_populator.show_ld(library_id, file_id)["ldda_id"]
        payload = {"purge": True}
        response = self._delete(f"/api/libraries/{library_id}/contents/{file_id}", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        assert self.library_populator.show_ldda(ldda_id)["deleted"] is True

    def test_delete_library_item_from_hdca_purged(self):
        library_id = self.library["id"]
        file_id = self._create_library_content(type="from_hdca")[0]["id"]
        ldda_id = self.library_populator.show_ld(library_id, file_id)["ldda_id"]
        payload = {"purge": True}
        response = self._delete(f"/api/libraries/{library_id}/contents/{file_id}", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        assert self.library_populator.show_ldda(ldda_id)["deleted"] is True

    def test_purge_library_item_retires_all_versions(self):
        library_id = self.library["id"]
        file_id = self._create_library_content(type="from_hda")["id"]
        expired_ldda_id = self._add_version(file_id)
        response = self._delete(f"/api/libraries/{library_id}/contents/{file_id}", data={"purge": True}, json=True)
        self._assert_status_code_is(response, 200)
        library_dataset = self._db_get_library_dataset(file_id)
        assert library_dataset.deleted is True
        assert library_dataset.purged is True
        assert library_dataset.library_dataset_dataset_association.deleted is True
        expired_ldda = self._db_session().get(model.LibraryDatasetDatasetAssociation, expired_ldda_id)
        assert expired_ldda.deleted is True

    def test_delete_invalid_library_item(self):
        library_id = self.library["id"]
        invalid_item_id = "invalid_id"
        response_invalid = self._delete(f"/api/libraries/{library_id}/contents/{invalid_item_id}")
        self._assert_status_code_is(response_invalid, 400)

    def _galaxy_app(self):
        app = self.driver_or_skip_test_if_remote().app
        assert app is not None
        return app

    def _db_session(self):
        session = self._galaxy_app().model.session
        session.rollback()
        return session

    def _decode_id(self, encoded_id):
        return self._galaxy_app().security.decode_id(encoded_id)

    def _db_get_library_dataset(self, encoded_id):
        return self._db_session().get(model.LibraryDataset, self._decode_id(encoded_id))

    def _add_version(self, encoded_id):
        """Add a version and make it current, demoting the existing one to an expired version."""
        session = self._db_session()
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

    def _create_library_content(self, type):
        folder_id = self.library["root_folder_id"]
        library_id = self.library["id"]

        if type == "folder":
            folder_name = "NewFolder"
            payload = {
                "folder_id": folder_id,
                "create_type": "folder",
                "name": folder_name,
                "description": "Test",
            }

        elif type == "from_hda":
            dataset_id = self.dataset_populator.new_dataset(self.history)["id"]
            payload = {
                "folder_id": folder_id,
                "create_type": "file",
                "from_hda_id": dataset_id,
                "ldda_message": "Test",
            }

        elif type == "from_hdca":
            hdca_id = self.dataset_collection_populator.create_list_in_history(
                self.history, contents=["dataset01", "dataset02"], direct_upload=True, wait=True
            ).json()["outputs"][0]["id"]
            payload = {
                "folder_id": folder_id,
                "create_type": "file",
                "from_hdca_id": hdca_id,
                "ldda_message": "Test",
            }

        response = self._post(f"/api/libraries/{library_id}/contents", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()
