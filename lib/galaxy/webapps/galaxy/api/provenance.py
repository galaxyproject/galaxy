"""
API operations provenance
"""
import logging
from galaxy import web
from galaxy.web.base.controller import BaseAPIController
from paste.httpexceptions import HTTPNotImplemented, HTTPBadRequest

log = logging.getLogger( __name__ )


class BaseProvenanceController( BaseAPIController ):
    """
    """
    @web.expose_api
    def index( self, trans, **kwd ):
        follow = kwd.get('follow', False)
        value = self._get_provenance( trans, self.provenance_item_class, kwd[self.provenance_item_id], follow )
        return value

    @web.expose_api
    def show( self, trans, elem_name, **kwd ):
        follow = kwd.get('follow', False)
        value = self._get_provenance( trans, self.provenance_item_class, kwd[self.provenance_item_id], follow )
        return value

    @web.expose_api
    def create( self, trans, tag_name, payload={}, **kwd ):
        raise HTTPNotImplemented()

    @web.expose_api
    def delete( self, trans, tag_name, **kwd ):
        raise HTTPBadRequest("Cannot Delete Provenance")

    def _get_provenance(self, trans, item_class_name, item_id, follow=True):
        provenance_item = self.get_object( trans, item_id, item_class_name, check_ownership=False, check_accessible=True )
        out = self._get_record(trans, provenance_item, follow)
        return out

    def _get_record(self, trans, item, follow):
        if item is not None:
            if follow:
                if item.copied_from_library_dataset_dataset_association:
                    item = item.copied_from_library_dataset_dataset_association
                return {
                    "id" : trans.security.encode_id(item.id),
                    "uuid" : item.dataset.uuid,
                    "tool_id" : item.creating_job.tool_id,
                    "parameters" : self._get_job_record(trans, item.creating_job, follow)
                }
            else:
                return {
                    "id" : trans.security.encode_id(item.id),
                    "uuid" : item.dataset.uuid
                }
        return None

    def _get_job_record(self, trans, job, follow):
        out = {}
        for p in job.parameters:
            out[p.name] = p.value
        for in_d in job.input_datasets:
            if follow:
                out[in_d.name] = self._get_record(trans, in_d.dataset, follow)
        return out


class HDAProvenanceController( BaseProvenanceController ):
    controller_name = "history_content_provenance"
    provenance_item_class = "HistoryDatasetAssociation"
    provenance_item_id = "history_content_id"


class LDDAProvenanceController( BaseProvenanceController ):
    controller_name = "ldda_provenance"
    provenance_item_class = "LibraryDatasetDatasetAssociation"
    provenance_item_id = "library_content_id"


