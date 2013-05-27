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
        value = self._get_provenance( trans, self.provenance_item_class, kwd[self.provenance_item_id] )
        return value

    @web.expose_api
    def show( self, trans, elem_name, **kwd ):
        value = self._get_provenance( trans, self.provenance_item_class, kwd[self.provenance_item_id] )
        return value

    @web.expose_api
    def create( self, trans, tag_name, payload={}, **kwd ):
        raise HTTPNotImplemented()

    @web.expose_api
    def delete( self, trans, tag_name, **kwd ):
        raise HTTPBadRequest("Cannot Delete Provenance")

    def _get_provenance(self, trans, item_class_name, item_id, follow=True):
        out = []
        provenance_item = self.get_object( trans, item_id, item_class_name, check_ownership=False, check_accessible=True )
        out.append(
            {
                "dataset" : {
                    "id" : trans.security.encode_id(provenance_item.id),
                    "uuid" : provenance_item.dataset.uuid
                },
                "tool_id" : provenance_item.creating_job.tool_id,
                "parameters" : self._get_job_record(trans, provenance_item.creating_job)
            }
        )
        if follow:
            depends = self._get_dataset_depends(provenance_item)
            recorded = {}
            for rec in depends:
                if rec.id not in recorded:
                    recorded[rec.id] = True
                    out.append( 
                        {
                            "dataset" : {
                                "id" : trans.security.encode_id(rec.id),
                                "uuid" : rec.dataset.uuid
                            },
                            "tool_id" : rec.creating_job.tool_id,
                            "parameters" : self._get_job_record(trans, rec.creating_job)
                        }
                    )
        return out

    def _get_dataset_depends(self, item):
        out = []
        for d in item.creating_job.input_datasets:
            out.append(d.dataset)
            for c in self._get_dataset_depends(d.dataset):
                out.append(c)
        return out

    def _get_job_record(self, trans, job):
        out = {}
        for p in job.parameters:
            out[p.name] = p.value
        for in_d in job.input_datasets:
            out[in_d.name] = { "dataset_id" : trans.security.encode_id(in_d.dataset.id), "uuid" : in_d.dataset.dataset.uuid }
        return out


class HDAProvenanceController( BaseProvenanceController ):
    controller_name = "history_content_provenance"
    provenance_item_class = "HistoryDatasetAssociation"
    provenance_item_id = "history_content_id"


class LDDAProvenanceController( BaseProvenanceController ):
    controller_name = "ldda_provenance"
    provenance_item_class = "LibraryDatasetDatasetAssociation"
    provenance_item_id = "library_content_id"


