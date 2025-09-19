import logging
from typing import (
    Any,
    Optional,
)

from galaxy.managers import base as manager_base
from galaxy.managers.datasets import DatasetAssociationManager
from galaxy.model import (
    LibraryDatasetDatasetAssociation,
    User,
)
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class LDDAManager(DatasetAssociationManager[LibraryDatasetDatasetAssociation]):
    """
    A fairly sparse manager for LDDAs.
    """

    model_class = LibraryDatasetDatasetAssociation

    def __init__(self, app: MinimalManagerApp):
        """
        Set up and initialize other managers needed by lddas.
        """
        super().__init__(app)

    def get(self, trans, id: int, check_accessible=True) -> LibraryDatasetDatasetAssociation:
        return manager_base.get_object(
            trans, id, "LibraryDatasetDatasetAssociation", check_ownership=False, check_accessible=check_accessible
        )

    def is_owner(self, item, user: Optional[User], **kwargs: Any) -> bool:
        """
        Return True if user owns the item.
        """
        assert isinstance(item, LibraryDatasetDatasetAssociation)
        if self.app.config.is_admin_user(user):
            return True
        return item.user == user

    def _set_permissions(self, trans, library_dataset, role_ids_dict):
        # Check Git history for an older broken implementation, but it was broken
        # and security related and had not test coverage so it was deleted.
        raise NotImplementedError()
