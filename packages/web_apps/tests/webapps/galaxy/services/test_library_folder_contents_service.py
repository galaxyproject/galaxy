from typing import cast

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.libraries import LibraryManager
from galaxy.model import (
    LibraryDataset,
    LibraryDatasetDatasetAssociation,
)
from galaxy.schema.fields import Security
from galaxy.schema.schema import LibraryFolderContentsIndexQueryPayload
from galaxy.webapps.galaxy.services.library_folder_contents import LibraryFolderContentsService


class TestLibraryFolderContentsService:
    def setup_method(self):
        mock_trans = galaxy_mock.MockTrans()
        self.trans = cast(ProvidesUserContext, mock_trans)
        self.app = self.trans.app
        Security.security = self.app.security
        mock_trans.init_user_in_database()
        self.service = self.app[LibraryFolderContentsService]

    def test_index_skips_library_dataset_without_ldda(self):
        folder = self.app[LibraryManager].create(self.trans, "library").root_folder
        assert folder
        sa_session = self.trans.sa_session
        ld = LibraryDataset(folder=folder, name="ok.bed")
        ldda = LibraryDatasetDatasetAssociation(
            name="ok.bed",
            extension="bed",
            library_dataset=ld,
            user=self.trans.user,
            create_dataset=True,
            sa_session=sa_session,
        )
        ld.library_dataset_dataset_association = ldda
        # the legacy library upload commits the LD before linking its LDDA
        pending_ld = LibraryDataset(folder=folder, name="pending.bed")
        sa_session.add_all((ld, ldda, pending_ld))
        sa_session.commit()
        assert pending_ld.library_dataset_dataset_association is None

        result = self.service.index(self.trans, folder.id, LibraryFolderContentsIndexQueryPayload())

        assert [item.name for item in result.folder_contents] == ["ok.bed"]
        assert result.metadata.total_rows == 1
