"""
API operations on annotations.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import  BaseAPIController, UsesHistoryMixin, UsesLibraryMixinItems, UsesHistoryDatasetAssociationMixin, UsesStoredWorkflowMixin
from galaxy.model.item_attrs import UsesExtendedMetadata
from galaxy.util.sanitize_html import sanitize_html
import galaxy.datatypes
from galaxy.util.bunch import Bunch

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

class BaseExtendedMetadataController( BaseAPIController, UsesExtendedMetadata, UsesHistoryMixin, UsesLibraryMixinItems, UsesHistoryDatasetAssociationMixin, UsesStoredWorkflowMixin ):

    @web.expose_api
    def index( self, trans, **kwd ):
        idnum = kwd[self.exmeta_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            ex_meta = self.get_item_extended_metadata_obj( trans.sa_session, trans.get_user(), item )
            if ex_meta is not None:
                return ex_meta.data

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        idnum = kwd[self.exmeta_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            ex_obj = self.get_item_extended_metadata_obj(trans.sa_session, trans.get_user(), item)
            if ex_obj is not None:
                self.unlink_item_extended_metadata_obj(trans.sa_session, trans.get_user(), item)
                self.delete_extended_metadata(trans.sa_session, trans.get_user(), ex_obj)
            ex_obj = self.create_extended_metadata(trans.sa_session, trans.get_user(), payload)
            self.set_item_extended_metadata_obj(trans.sa_session, trans.get_user(), item, ex_obj)

    @web.expose_api
    def delete( self, trans, **kwd ):
        idnum = kwd[self.tagged_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            ex_obj = self.get_item_extended_metadata_obj(trans.sa_session, trans.get_user(), item)
            if ex_obj is not None:
                self.unlink_item_extended_metadata_obj(trans.sa_session, trans.get_user(), item)
                self.delete_extended_metadata(trans.sa_session, trans.get_user(), ex_obj)

    @web.expose_api
    def undelete( self, trans, **kwd ):
        raise HTTPNotImplemented()

class LibraryDatasetExtendMetadataController(BaseExtendedMetadataController):
    controller_name = "library_dataset_extended_metadata"
    exmeta_item_id = "library_content_id"
    def _get_item_from_id(self, trans, idstr):
        hist = self.get_library_dataset_dataset_association( trans, idstr )
        return hist

