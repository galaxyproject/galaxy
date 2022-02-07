"""
API operations on annotations.
"""
import logging
from typing import (
    Generic,
    Optional,
    TypeVar,
)

from galaxy import (
    managers,
    model,
    web,
)
from galaxy.webapps.base.controller import (
    UsesExtendedMetadataMixin,
    UsesLibraryMixinItems,
    UsesStoredWorkflowMixin,
)
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)

T = TypeVar("T")


class BaseExtendedMetadataController(
    BaseGalaxyAPIController, UsesExtendedMetadataMixin, UsesLibraryMixinItems, UsesStoredWorkflowMixin, Generic[T]
):
    exmeta_item_id: str

    def _get_item_from_id(self, trans, idstr, check_writable=True) -> Optional[T]:
        ...

    @web.expose_api
    def index(self, trans, **kwd):
        idnum = kwd[self.exmeta_item_id]
        item = self._get_item_from_id(trans, idnum, check_writable=False)
        if item is not None:
            ex_meta = self.get_item_extended_metadata_obj(trans, item)
            if ex_meta is not None:
                return ex_meta.data

    @web.expose_api
    def create(self, trans, payload, **kwd):
        idnum = kwd[self.exmeta_item_id]
        item = self._get_item_from_id(trans, idnum, check_writable=True)
        if item is not None:
            ex_obj = self.get_item_extended_metadata_obj(trans, item)
            if ex_obj is not None:
                self.unset_item_extended_metadata_obj(trans, item)
                self.delete_extended_metadata(trans, ex_obj)
            ex_obj = self.create_extended_metadata(trans, payload)
            self.set_item_extended_metadata_obj(trans, item, ex_obj)


class LibraryDatasetExtendMetadataController(BaseExtendedMetadataController[model.LibraryDatasetDatasetAssociation]):
    controller_name = "library_dataset_extended_metadata"
    exmeta_item_id = "library_content_id"

    def _get_item_from_id(self, trans, idstr, check_writable=True) -> Optional[model.LibraryDatasetDatasetAssociation]:
        if check_writable:
            item = self.get_library_dataset_dataset_association(trans, idstr)
            if trans.app.security_agent.can_modify_library_item(trans.get_current_user_roles(), item):
                return item
        else:
            item = self.get_library_dataset_dataset_association(trans, idstr)
            if trans.app.security_agent.can_access_library_item(trans.get_current_user_roles(), item, trans.user):
                return item
        return None


class HistoryDatasetExtendMetadataController(BaseExtendedMetadataController[model.HistoryDatasetAssociation]):
    controller_name = "history_dataset_extended_metadata"
    exmeta_item_id = "history_content_id"
    hda_manager: managers.hdas.HDAManager = depends(managers.hdas.HDAManager)

    def _get_item_from_id(self, trans, idstr, check_writable=True) -> Optional[model.HistoryDatasetAssociation]:
        decoded_idstr = self.decode_id(idstr)
        if check_writable:
            return self.hda_manager.get_owned(decoded_idstr, trans.user, current_history=trans.history)
        else:
            hda = self.hda_manager.get_accessible(decoded_idstr, trans.user)
            return self.hda_manager.error_if_uploading(hda)
