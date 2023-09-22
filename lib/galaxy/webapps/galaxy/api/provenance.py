"""
API operations provenance
"""
import logging

from paste.httpexceptions import (
    HTTPBadRequest,
    HTTPNotImplemented,
)

from galaxy import web
from galaxy.managers.hdas import HDAManager
from galaxy.util import string_as_bool
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class BaseProvenanceController(BaseGalaxyAPIController):
    """ """

    @web.legacy_expose_api
    def index(self, trans, **kwd):
        follow = string_as_bool(kwd.get("follow", False))
        value = self._get_provenance(trans, self.provenance_item_class, kwd[self.provenance_item_id], follow)
        return value

    @web.legacy_expose_api
    def show(self, trans, elem_name, **kwd):
        raise HTTPNotImplemented()

    @web.legacy_expose_api
    def create(self, trans, tag_name, payload=None, **kwd):
        raise HTTPNotImplemented()

    @web.legacy_expose_api
    def delete(self, trans, tag_name, **kwd):
        raise HTTPBadRequest("Cannot Delete Provenance")

    def _get_provenance(self, trans, item_class_name, item_id, follow=True):
        provenance_item = self.get_object(
            trans, item_id, item_class_name, check_ownership=False, check_accessible=False
        )
        if item_class_name == "HistoryDatasetAssociation":
            self.hda_manager.error_unless_accessible(provenance_item, trans.user)
        else:
            self.security_check(trans, provenance_item, check_accessible=True)
        out = self._get_record(trans, provenance_item, follow)
        return out

    def _get_record(self, trans, item, follow):
        if item is not None:
            if item.copied_from_library_dataset_dataset_association:
                item = item.copied_from_library_dataset_dataset_association
            job = item.creating_job
            if job is not None:
                return {
                    "id": trans.security.encode_id(item.id),
                    "uuid": (lambda uuid: str(uuid) if uuid else None)(item.dataset.uuid),
                    "job_id": trans.security.encode_id(job.id),
                    "tool_id": job.tool_id,
                    "parameters": self._get_job_record(trans, job, follow),
                    "stderr": job.stderr,
                    "stdout": job.stdout,
                }
            else:
                return {
                    "id": trans.security.encode_id(item.id),
                    "uuid": (lambda uuid: str(uuid) if uuid else None)(item.dataset.uuid),
                }
        return None

    def _get_job_record(self, trans, job, follow):
        out = {}
        for p in job.parameters:
            out[p.name] = p.value
        for in_d in job.input_datasets:
            if not in_d.dataset:
                continue
            if follow:
                out[in_d.name] = self._get_record(trans, in_d.dataset, follow)
            else:
                out[in_d.name] = {
                    "id": trans.security.encode_id(in_d.dataset.id),
                    "uuid": (lambda uuid: str(uuid) if uuid else None)(in_d.dataset.dataset.uuid),
                }
        return out


class HDAProvenanceController(BaseProvenanceController):
    controller_name = "history_content_provenance"
    provenance_item_class = "HistoryDatasetAssociation"
    provenance_item_id = "history_content_id"
    hda_manager: HDAManager = depends(HDAManager)


class LDDAProvenanceController(BaseProvenanceController):
    controller_name = "ldda_provenance"
    provenance_item_class = "LibraryDatasetDatasetAssociation"
    provenance_item_id = "library_content_id"
    hda_manager: HDAManager = depends(HDAManager)
