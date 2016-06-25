"""
API for searching Galaxy Datasets
"""
import logging
from galaxy import web
from galaxy.web.base.controller import SharableItemSecurityMixin, BaseAPIController
from galaxy.model.search import GalaxySearchEngine
from galaxy.exceptions import ItemAccessibilityException

log = logging.getLogger( __name__ )


class SearchController( BaseAPIController, SharableItemSecurityMixin ):

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/search
        Do a search of the various elements of Galaxy.
        """
        query_txt = payload.get("query", None)
        out = []
        if query_txt is not None:
            se = GalaxySearchEngine()
            try:
                query = se.query(query_txt)
            except Exception as e:
                return {'error': str(e)}
            if query is not None:
                query.decode_query_ids(trans)
                current_user_roles = trans.get_current_user_roles()
                try:
                    results = query.process(trans)
                except Exception as e:
                    return {'error': str(e)}
                for item in results:
                    append = False
                    if trans.user_is_admin():
                        append = True
                    if not append:
                        if type( item ) in [ trans.app.model.LibraryFolder, trans.app.model.LibraryDatasetDatasetAssociation, trans.app.model.LibraryDataset ]:
                            if (trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), item, trans.user ) ):
                                append = True
                        elif type( item ) in [ trans.app.model.Job ]:
                            if item.used_id == trans.user or trans.user_is_admin():
                                append = True
                        elif type( item ) in [ trans.app.model.Page, trans.app.model.StoredWorkflow ]:
                            try:
                                if self.security_check( trans, item, False, True):
                                    append = True
                            except ItemAccessibilityException:
                                append = False
                        elif type( item ) in [ trans.app.model.PageRevision ]:
                            try:
                                if self.security_check( trans, item.page, False, True):
                                    append = True
                            except ItemAccessibilityException:
                                append = False
                        elif hasattr(item, 'dataset'):
                            if trans.app.security_agent.can_access_dataset( current_user_roles, item.dataset ):
                                append = True

                    if append:
                        row = query.item_to_api_value(item)
                        out.append( self.encode_all_ids( trans, row, True) )
        return { 'results': out }
