"""
Manager and Serializer for HDAs.

HistoryDatasetAssociations (HDAs) are datasets contained or created in a
history.
"""

from galaxy import exceptions

from galaxy.managers import base as manager_base
from galaxy.managers import histories as history_manager

import galaxy.web
import galaxy.datatypes.metadata
from galaxy import objectstore

class HDAManager( manager_base.ModelManager ):
    """
    Interface/service object for interacting with HDAs.
    """

    def __init__( self ):
        """
        Set up and initialize other managers needed by hdas.
        """
        self.histories_mgr = history_manager.HistoryManager()

    def get( self, trans, unencoded_id, check_ownership=True, check_accessible=True ):
        """
        Get an HDA by its unencoded db id, checking ownership (via its history)
        or accessibility (via dataset shares/permissions).
        """
        hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( unencoded_id )
        if hda is None:
            raise exceptions.ObjectNotFound()
        hda = self.secure( trans, hda, check_ownership, check_accessible )
        return hda

    def secure( self, trans, hda, check_ownership=True, check_accessible=True ):
        """
        check ownership (via its history) or accessibility (via dataset
        shares/permissions).
        """
        # all items are accessible to an admin
        if trans.user and trans.user_is_admin():
            return hda
        if check_ownership:
            hda = self.check_ownership( trans, hda )
        if check_accessible:
            hda = self.check_accessible( trans, hda )
        return hda

    def can_access_dataset( self, trans, hda ):
        """
        Use security agent to see if current user has access to dataset.
        """
        current_user_roles = trans.get_current_user_roles()
        return trans.app.security_agent.can_access_dataset( current_user_roles, hda.dataset )

    #TODO: is_owner, is_accessible

    def check_ownership( self, trans, hda ):
        """
        Use history to see if current user owns HDA.
        """
        if not trans.user:
            #if hda.history == trans.history:
            #    return hda
            raise exceptions.AuthenticationRequired( "Must be logged in to manage Galaxy datasets", type='error' )
        if trans.user_is_admin():
            return hda
        # check for ownership of the containing history and accessibility of the underlying dataset
        if( self.histories_mgr.is_owner( trans, hda.history )
                and self.can_access_dataset( trans, hda ) ):
            return hda
        raise exceptions.ItemOwnershipException(
            "HistoryDatasetAssociation is not owned by the current user", type='error' )

    def check_accessible( self, trans, hda ):
        """
        Raise error if HDA is not accessible.
        """
        if trans.user and trans.user_is_admin():
            return hda
        # check for access of the containing history...
        self.histories_mgr.check_accessible( trans, hda.history )
        # ...then the underlying dataset
        if self.can_access_dataset( trans, hda ):
            return hda
        raise exceptions.ItemAccessibilityException(
            "HistoryDatasetAssociation is not accessible to the current user", type='error' )

    def err_if_uploading( self, trans, hda ):
        """
        Raise error if HDA is still uploading.
        """
        if hda.state == trans.model.Dataset.states.UPLOAD:
            raise exceptions.Conflict( "Please wait until this dataset finishes uploading" )
        return hda

    def get_hda_dict( self, trans, hda ):
        """
        Return full details of this HDA in dictionary form.
        """
        #precondition: the user's access to this hda has already been checked
        #TODO:?? postcondition: all ids are encoded (is this really what we want at this level?)
        expose_dataset_path = trans.user_is_admin() or trans.app.config.expose_dataset_path
        hda_dict = hda.to_dict( view='element', expose_dataset_path=expose_dataset_path )
        hda_dict[ 'api_type' ] = "file"

        # Add additional attributes that depend on trans must be added here rather than at the model level.
        can_access_hda = trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
        can_access_hda = ( trans.user_is_admin() or can_access_hda )
        if not can_access_hda:
            return self.get_inaccessible_hda_dict( trans, hda )
        hda_dict[ 'accessible' ] = True

        #TODO: I'm unclear as to which access pattern is right
        hda_dict[ 'annotation' ] = hda.get_item_annotation_str( trans.sa_session, hda.history.user, hda )
        #annotation = getattr( hda, 'annotation', hda.get_item_annotation_str( trans.sa_session, trans.user, hda ) )

        # ---- return here if deleted AND purged OR can't access
        purged = ( hda.purged or hda.dataset.purged )
        if ( hda.deleted and purged ):
            #TODO: to_dict should really go AFTER this - only summary data
            return trans.security.encode_dict_ids( hda_dict )

        if expose_dataset_path:
            try:
                hda_dict[ 'file_name' ] = hda.file_name
            except objectstore.ObjectNotFound:
                log.exception( 'objectstore.ObjectNotFound, HDA %s.', hda.id )

        hda_dict[ 'download_url' ] = galaxy.web.url_for( 'history_contents_display',
            history_id = trans.security.encode_id( hda.history.id ),
            history_content_id = trans.security.encode_id( hda.id ) )

        # indeces, assoc. metadata files, etc.
        meta_files = []
        for meta_type in hda.metadata.spec.keys():
            if isinstance( hda.metadata.spec[ meta_type ].param, galaxy.datatypes.metadata.FileParameter ):
                meta_files.append( dict( file_type=meta_type ) )
        if meta_files:
            hda_dict[ 'meta_files' ] = meta_files

        # currently, the viz reg is optional - handle on/off
        if trans.app.visualizations_registry:
            hda_dict[ 'visualizations' ] = trans.app.visualizations_registry.get_visualizations( trans, hda )
        else:
            hda_dict[ 'visualizations' ] = hda.get_visualizations()
        #TODO: it may also be wiser to remove from here and add as API call that loads the visualizations
        #           when the visualizations button is clicked (instead of preloading/pre-checking)

        # ---- return here if deleted
        if hda.deleted and not purged:
            return trans.security.encode_dict_ids( hda_dict )

        return trans.security.encode_dict_ids( hda_dict )

    def get_inaccessible_hda_dict( self, trans, hda ):
        """
        Return truncated serialization of HDA when inaccessible to user.
        """
        return trans.security.encode_dict_ids({
            'id'        : hda.id,
            'history_id': hda.history.id,
            'hid'       : hda.hid,
            'name'      : hda.name,
            'state'     : hda.state,
            'deleted'   : hda.deleted,
            'visible'   : hda.visible,
            'accessible': False
        })

    def get_hda_dict_with_error( self, trans, hda=None, history_id=None, id=None, error_msg='Error' ):
        """
        Return truncated serialization of HDA when error raised getting
        details.
        """
        return trans.security.encode_dict_ids({
            'id'        : hda.id if hda else id,
            'history_id': hda.history.id if hda else history_id,
            'hid'       : hda.hid if hda else '(unknown)',
            'name'      : hda.name if hda else '(unknown)',
            'error'     : error_msg,
            'state'     : trans.model.Dataset.states.NEW
        })

    def get_display_apps( self, trans, hda ):
        """
        Return dictionary containing new-style display app urls.
        """
        display_apps = []
        for display_app in hda.get_display_applications( trans ).itervalues():

            app_links = []
            for link_app in display_app.links.itervalues():
                app_links.append({
                    'target': link_app.url.get( 'target_frame', '_blank' ),
                    'href'  : link_app.get_display_url( hda, trans ),
                    'text'  : gettext( link_app.name )
                })
            if app_links:
                display_apps.append( dict( label=display_app.name, links=app_links ) )

        return display_apps

    def get_old_display_applications( self, trans, hda ):
        """
        Return dictionary containing old-style display app urls.
        """
        display_apps = []
        if not trans.app.config.enable_old_display_applications:
            return display_apps

        for display_app in hda.datatype.get_display_types():
            target_frame, display_links = hda.datatype.get_display_links( hda,
                display_app, trans.app, trans.request.base )

            if len( display_links ) > 0:
                display_label = hda.datatype.get_display_label( display_app )

                app_links = []
                for display_name, display_link in display_links:
                    app_links.append({
                        'target': target_frame,
                        'href'  : display_link,
                        'text'  : gettext( display_name )
                    })
                if app_links:
                    display_apps.append( dict( label=display_label, links=app_links ) )

        return display_apps


# =============================================================================
class HistorySerializer( manager_base.ModelSerializer ):
    """
    Interface/service object for serializing HDAs into dictionaries.
    """
    pass
