"""
API operations on the contents of a history.
"""
import logging
import urllib
from gettext import gettext

from galaxy import web
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy.web.base.controller import UsesHistoryDatasetAssociationMixin, UsesHistoryMixin
from galaxy.web.base.controller import UsesLibraryMixin, UsesLibraryMixinItems

from galaxy.web.framework.helpers import to_unicode
from galaxy.datatypes.display_applications import util
from galaxy.datatypes.metadata import FileParameter

from galaxy.datatypes.display_applications.link_generator import get_display_app_link_generator

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

class HistoryContentsController( BaseAPIController, UsesHistoryDatasetAssociationMixin, UsesHistoryMixin,
                                 UsesLibraryMixin, UsesLibraryMixinItems ):
    @web.expose_api
    def index( self, trans, history_id, ids=None, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents
        Displays a collection (list) of history contents (HDAs)

        :param history_id: an encoded id string of the `History` to search
        :param ids: (optional) a comma separated list of encoded `HDA` ids

        If Ids is not given, index returns a list of *summary* json objects for
        every `HDA` associated with the given `history_id`.
        See _summary_hda_dict.

        If ids is given, index returns a *more complete* json object for each
        HDA in the ids list.

        Note: Anonymous users are allowed to get their current history contents
        (generally useful for browser UI access of the api)
        """
        rval = []
        try:
            # get the history, if anon user and requesting current history - allow it
            if( ( trans.user == None )
            and ( history_id == trans.security.encode_id( trans.history.id ) ) ):
                #TODO:?? is secure?
                history = trans.history

            # otherwise, check permissions for the history first
            else:
                history = self.get_history( trans, history_id, check_ownership=True, check_accessible=True )

            # build the return hda data list
            if ids:
                # if ids, return _FULL_ data (as show) for each id passed
                #NOTE: this might not be the best form (passing all info),
                #   but we(I?) need an hda collection with full data somewhere
                ids = ids.split( ',' )
                for hda in history.datasets:
                    #TODO: curr. ordered by history, change to order from ids list
                    encoded_hda_id = trans.security.encode_id( hda.id )
                    if encoded_hda_id in ids:
                        #TODO: share code with show
                        try:
                            rval.append( get_hda_dict( trans, history, hda, for_editing=True ) )

                        except Exception, exc:
                            # don't fail entire list if hda err's, record and move on
                            # (making sure http recvr knows it's err'd)
                            trans.response.status = 500
                            log.error( "Error in history API at listing contents " +
                                "with history %s, hda %s: %s", history_id, encoded_hda_id, str( exc ) )
                            rval.append( self._exception_as_hda_dict( trans, encoded_hda_id, exc ) )

            else:
                # if no ids passed, return a _SUMMARY_ of _all_ datasets in the history
                for hda in history.datasets:
                    rval.append( self._summary_hda_dict( trans, history_id, hda ) )

        except Exception, e:
            # for errors that are not specific to one hda (history lookup or summary list)
            rval = "Error in history API at listing contents: " + str( e )
            log.error( rval + ": %s, %s" % ( type( e ), str( e ) ) )
            trans.response.status = 500

        return rval

    #TODO: move to model or Mixin
    def _summary_hda_dict( self, trans, history_id, hda ):
        """
        Returns a dictionary based on the HDA in .. _summary form::
        {
            'id'    : < the encoded dataset id >,
            'name'  : < currently only returns 'file' >,
            'type'  : < name of the dataset >,
            'url'   : < api url to retrieve this datasets full data >,
        }
        """
        api_type = "file"
        encoded_id = trans.security.encode_id( hda.id )
        return {
            'id'    : encoded_id,
            'name'  : hda.name,
            'type'  : api_type,
            'url'   : url_for( 'history_content', history_id=history_id, id=encoded_id, ),
        }

    #TODO: move to model or Mixin
    def _exception_as_hda_dict( self, trans, hda_id, exception ):
        """
        Returns a dictionary for an HDA that raised an exception when it's
        dictionary was being built.
        """
        return {
            'id'        : hda_id,
            'state'     : trans.app.model.Dataset.states.ERROR,
            'visible'   : True,
            'misc_info' : str( exception ),
            'misc_blurb': 'Failed to retrieve dataset information.',
            'error'     : str( exception )
        }

    @web.expose_api
    def show( self, trans, id, history_id, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}
        Displays information about a history content (dataset).
        """
        hda_dict = {}
        try:
            # for anon users:
            #TODO: check login_required?
            #TODO: this isn't actually most_recently_used (as defined in histories)
            if( ( trans.user == None )
            and ( history_id == trans.security.encode_id( trans.history.id ) ) ):
                history = trans.history
                #TODO: dataset/hda by id (from history) OR check_ownership for anon user
                hda = self.get_history_dataset_association( trans, history, id,
                    check_ownership=False, check_accessible=True )

            else:
                history = self.get_history( trans, history_id,
                    check_ownership=True, check_accessible=True, deleted=False )
                hda = self.get_history_dataset_association( trans, history, id,
                    check_ownership=True, check_accessible=True )

            hda_dict = get_hda_dict( trans, history, hda, for_editing=True )

        except Exception, e:
            msg = "Error in history API at listing dataset: %s" % ( str(e) )
            log.error( msg, exc_info=True )
            trans.response.status = 500
            return msg

        return hda_dict

    @web.expose_api
    def create( self, trans, history_id, payload, **kwd ):
        """
        POST /api/histories/{encoded_history_id}/contents
        Creates a new history content item (file, aka HistoryDatasetAssociation).
        """
        from_ld_id = payload.get( 'from_ld_id', None )

        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False )
        except Exception, e:
            return str( e )

        if from_ld_id:
            try:
                ld = self.get_library_dataset( trans, from_ld_id, check_ownership=False, check_accessible=False )
                assert type( ld ) is trans.app.model.LibraryDataset, "Library content id ( %s ) is not a dataset" % from_ld_id
            except AssertionError, e:
                trans.response.status = 400
                return str( e )
            except Exception, e:
                return str( e )
            hda = ld.library_dataset_dataset_association.to_history_dataset_association( history, add_to_history=True )
            trans.sa_session.flush()
            return hda.get_api_value()
        else:
            # TODO: implement other "upload" methods here.
            trans.response.status = 403
            return "Not implemented."


#TODO: move these into model
def get_hda_dict( trans, history, hda, for_editing ):
    hda_dict = hda.get_api_value( view='element' )

    hda_dict[ 'id' ] = trans.security.encode_id( hda.id )
    hda_dict[ 'history_id' ] = trans.security.encode_id( history.id )
    hda_dict[ 'hid' ] = hda.hid

    hda_dict[ 'file_ext' ] = hda.ext
    if trans.user_is_admin() or trans.app.config.expose_dataset_path:
        hda_dict[ 'file_name' ] = hda.file_name

    if not hda_dict[ 'deleted' ]:
        # Problem: Method url_for cannot use the dataset controller
        # Get the environment from DefaultWebTransaction
        #   and use default webapp mapper instead of webapp API mapper
        web_url_for = routes.URLGenerator( trans.webapp.mapper, trans.environ )
        # http://routes.groovie.org/generating.html
        # url_for is being phased out, so new applications should use url
        hda_dict[ 'download_url' ] = web_url_for( controller='dataset', action='display',
            dataset_id=trans.security.encode_id( hda.id ), to_ext=hda.ext )

    can_access_hda = trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
    hda_dict[ 'accessible' ] = ( trans.user_is_admin() or can_access_hda )
    hda_dict[ 'api_type' ] = "file"

    if not( hda.purged or hda.deleted or hda.dataset.purged ):
        meta_files = []
        for meta_type in hda.metadata.spec.keys():
            if isinstance( hda.metadata.spec[ meta_type ].param, FileParameter ):
                meta_files.append( dict( file_type=meta_type ) )
        if meta_files:
            hda_dict[ 'meta_files' ] = meta_files

    hda_dict[ 'display_apps' ] = get_display_apps( trans, hda )
    hda_dict[ 'display_types' ] = get_old_display_applications( trans, hda )

    hda_dict[ 'visualizations' ] = hda.get_visualizations()
    hda_dict[ 'peek' ] = to_unicode( hda.display_peek() )

    if hda.creating_job and hda.creating_job.tool_id:
        tool_used = trans.app.toolbox.get_tool( hda.creating_job.tool_id )
        if tool_used and tool_used.force_history_refresh:
            hda_dict[ 'force_history_refresh' ] = True

    return hda_dict

def get_display_apps( trans, hda ):
    #TODO: make more straightforward (somehow)
    display_apps = []

    def get_display_app_url( display_app_link, hda, trans ):
        web_url_for = routes.URLGenerator( trans.webapp.mapper, trans.environ )
        dataset_hash, user_hash = util.encode_dataset_user( trans, hda, None )
        return web_url_for( controller='/dataset',
                        action="display_application",
                        dataset_id=dataset_hash,
                        user_id=user_hash,
                        app_name=urllib.quote_plus( display_app_link.display_application.id ),
                        link_name=urllib.quote_plus( display_app_link.id ) )

    for display_app in hda.get_display_applications( trans ).itervalues():
        app_links = []
        for display_app_link in display_app.links.itervalues():
            app_links.append({
                'target' : display_app_link.url.get( 'target_frame', '_blank' ),
                'href' : get_display_app_url( display_app_link, hda, trans ),
                'text' : gettext( display_app_link.name )
            })
        display_apps.append( dict( label=display_app.name, links=app_links ) )

    return display_apps

def get_old_display_applications( trans, hda ):
    display_apps = []
    for display_app_name in hda.datatype.get_display_types():
        link_generator = get_display_app_link_generator( display_app_name )
        display_links = link_generator.generate_links( trans, hda )

        app_links = []
        for display_name, display_link in display_links:
            app_links.append({
                'target' : '_blank',
                'href' : display_link,
                'text' : display_name
            })
        if app_links:
            display_apps.append( dict( label=hda.datatype.get_display_label( display_app_name ), links=app_links ) )

    return display_apps

