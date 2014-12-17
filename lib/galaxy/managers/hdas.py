"""
Manager and Serializer for HDAs.

HistoryDatasetAssociations (HDAs) are datasets contained or created in a
history.
"""
from galaxy import model
from galaxy import exceptions

import base
import histories
import datasets

import galaxy.web
import galaxy.datatypes.metadata
from galaxy import objectstore


# =============================================================================
class HDAManager( datasets.DatasetAssociationManager ):
    """
    Interface/service object for interacting with HDAs.
    """
    model_class = model.HistoryDatasetAssociation
    default_order_by = ( model.HistoryDatasetAssociation.create_time, )

    def __init__( self, app ):
        """
        Set up and initialize other managers needed by hdas.
        """
        super( HDAManager, self ).__init__( app )

    def create( self, trans, history=None, dataset=None, flush=True, **kwargs ):
        if not dataset:
            kwargs[ 'create_dataset' ] = True
        hda = super( HDAManager, self ).create( trans, flush=flush,
            history=history, dataset=dataset, sa_session=trans.sa_session, **kwargs )
        trans.sa_session.add( hda )
        if flush:
            trans.sa_session.flush()
        return hda

    def copy_hda( self, trans, hda, history=None, **kwargs ):
        #TODO:?? not using the following as this fn does not set history and COPIES hid (this doesn't seem correct)
        #return hda.copy()
        copy = model.HistoryDatasetAssociation(
            name        = hda.name,
            info        = hda.info,
            blurb       = hda.blurb,
            peek        = hda.peek,
            tool_version= hda.tool_version,
            extension   = hda.extension,
            dbkey       = hda.dbkey,
            dataset     = hda.dataset,
            visible     = hda.visible,
            deleted     = hda.deleted,
            parent_id   = kwargs.get( 'parent_id', None ),
        )
        # add_dataset will update the hid to the next avail. in history
        if history:
            history.add_dataset( copy )

        copy.copied_from_history_dataset_association = hda
        copy.set_size()

        # Need to set after flushed, as MetadataFiles require dataset.id
        trans.sa_session.add( copy )
        trans.sa_session.flush()
        copy.metadata = hda.metadata

        # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        if not hda.datatype.copy_safe_peek:
            copy.set_peek()

        trans.sa_session.flush()
        return copy

    def copy_ldda( self, trans, history, ldda, **kwargs ):
        return ldda.to_history_dataset_association( history, add_to_history=True )

#    def by_history_id( self, trans, history_id, filters=None, **kwargs ):
#        history_id_filter = self.model_class.history_id == history_id
#        filters = self._munge_filters( history_id_filter, filters )
#        return self.list( trans, filters=filters, **kwargs )
#
#    #def by_history( self, trans, history, filters=None, **kwargs ):
#    #    return history.datasets

    def purge( self, trans, hda ):
        self.error_unless_dataset_purge_allowed( trans, hda )
        super( HDAManager, self ).purge( trans, hda, flush=True )

        # signal to stop the creating job?
        if hda.creating_job_associations:
            job = hda.creating_job_associations[0].job
            job.mark_deleted( self.app.config.track_jobs_in_database )
            self.app.job_manager.job_stop_queue.put( job.id )

        # more importantly, purge dataset as well
        if hda.dataset.user_can_purge:
            self.dataset_mgr.purge( trans, hda.dataset )
        return hda

    def error_if_uploading( self, trans, hda ):
        """
        Raise error if HDA is still uploading.
        """
        if hda.state == trans.model.Dataset.states.UPLOAD:
            raise exceptions.Conflict( "Please wait until this dataset finishes uploading" )
        return hda

    # ......................................................................... serialization
    #TODO: move into serializer below
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

    #def get_dataset( self, trans, dataset_id, check_ownership=True, check_accessible=False, check_state=True ):
    #    """
    #    Get an HDA object by id performing security checks using
    #    the current transaction.
    #    """
    #    try:
    #        dataset_id = trans.security.decode_id( dataset_id )
    #    except ( AttributeError, TypeError ):
    #        # DEPRECATION: We still support unencoded ids for backward compatibility
    #        try:
    #            dataset_id = int( dataset_id )
    #        except ValueError:
    #            raise HTTPBadRequest( "Invalid dataset id: %s." % str( dataset_id ) )
    #
    #    try:
    #        data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( int( dataset_id ) )
    #    except:
    #        raise HTTPRequestRangeNotSatisfiable( "Invalid dataset id: %s." % str( dataset_id ) )
    #
    #    if check_ownership:
    #        # Verify ownership.
    #        user = trans.get_user()
    #        if not user:
    #            error( "Must be logged in to manage Galaxy items" )
    #        if data.history.user != user:
    #            error( "%s is not owned by current user" % data.__class__.__name__ )
    #
    #    if check_accessible:
    #        current_user_roles = trans.get_current_user_roles()
    #
    #        if not trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
    #            error( "You are not allowed to access this dataset" )
    #
    #        if check_state and data.state == trans.model.Dataset.states.UPLOAD:
    #            return trans.show_error_message( "Please wait until this dataset finishes uploading "
    #                                               + "before attempting to view it." )
    #    return data
    #
    #def get_history_dataset_association( self, trans, history, dataset_id,
    #                                     check_ownership=True, check_accessible=False, check_state=False ):
    #    """
    #    Get a HistoryDatasetAssociation from the database by id, verifying ownership.
    #    """
    #    #TODO: duplicate of above? alias to above (or vis-versa)
    #    self.security_check( trans, history, check_ownership=check_ownership, check_accessible=check_accessible )
    #    hda = self.get_object( trans, dataset_id, 'HistoryDatasetAssociation',
    #                           check_ownership=False, check_accessible=False )
    #
    #    if check_accessible:
    #        if( not trans.user_is_admin()
    #        and not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset ) ):
    #            error( "You are not allowed to access this dataset" )
    #
    #        if check_state and hda.state == trans.model.Dataset.states.UPLOAD:
    #            error( "Please wait until this dataset finishes uploading before attempting to view it." )
    #    return hda
    #
    #def get_history_dataset_association_from_ids( self, trans, id, history_id ):
    #    # Just to echo other TODOs, there seems to be some overlap here, still
    #    # this block appears multiple places (dataset show, history_contents
    #    # show, upcoming history job show) so I am consolodating it here.
    #    # Someone smarter than me should determine if there is some redundancy here.
    #
    #    # for anon users:
    #    #TODO: check login_required?
    #    #TODO: this isn't actually most_recently_used (as defined in histories)
    #    if( ( trans.user == None )
    #    and ( history_id == trans.security.encode_id( trans.history.id ) ) ):
    #        history = trans.history
    #        #TODO: dataset/hda by id (from history) OR check_ownership for anon user
    #        hda = self.get_history_dataset_association( trans, history, id,
    #            check_ownership=False, check_accessible=True )
    #    else:
    #        #TODO: do we really need the history?
    #        history = self.get_history( trans, history_id,
    #            check_ownership=False, check_accessible=True, deleted=False )
    #        hda = self.get_history_dataset_association( trans, history, id,
    #            check_ownership=False, check_accessible=True )
    #    return hda
    #
    #def get_hda_list( self, trans, hda_ids, check_ownership=True, check_accessible=False, check_state=True ):
    #    """
    #    Returns one or more datasets in a list.
    #
    #    If a dataset is not found or is inaccessible to trans.user,
    #    add None in its place in the list.
    #    """
    #    # precondtion: dataset_ids is a list of encoded id strings
    #    hdas = []
    #    for id in hda_ids:
    #        hda = None
    #        try:
    #            hda = self.get_dataset( trans, id,
    #                check_ownership=check_ownership,
    #                check_accessible=check_accessible,
    #                check_state=check_state )
    #        except Exception:
    #            pass
    #        hdas.append( hda )
    #    return hdas
    #
    #def get_data( self, dataset, preview=True ):
    #    """
    #    Gets a dataset's data.
    #    """
    #    # Get data from file, truncating if necessary.
    #    truncated = False
    #    dataset_data = None
    #    if os.path.exists( dataset.file_name ):
    #        if isinstance( dataset.datatype, Text ):
    #            max_peek_size = 1000000 # 1 MB
    #            if preview and os.stat( dataset.file_name ).st_size > max_peek_size:
    #                dataset_data = open( dataset.file_name ).read(max_peek_size)
    #                truncated = True
    #            else:
    #                dataset_data = open( dataset.file_name ).read(max_peek_size)
    #                truncated = False
    #        else:
    #            # For now, cannot get data from non-text datasets.
    #            dataset_data = None
    #    return truncated, dataset_data
    #
    #def check_dataset_state( self, trans, dataset ):
    #    """
    #    Returns a message if dataset is not ready to be used in visualization.
    #    """
    #    if not dataset:
    #        return dataset.conversion_messages.NO_DATA
    #    if dataset.state == trans.app.model.Job.states.ERROR:
    #        return dataset.conversion_messages.ERROR
    #    if dataset.state != trans.app.model.Job.states.OK:
    #        return dataset.conversion_messages.PENDING
    #    return None
    #
    #def get_hda_dict( self, trans, hda ):
    #    """Return full details of this HDA in dictionary form.
    #    """
    #    #precondition: the user's access to this hda has already been checked
    #    #TODO:?? postcondition: all ids are encoded (is this really what we want at this level?)
    #    expose_dataset_path = trans.user_is_admin() or trans.app.config.expose_dataset_path
    #    hda_dict = hda.to_dict( view='element', expose_dataset_path=expose_dataset_path )
    #    hda_dict[ 'api_type' ] = "file"
    #
    #    # Add additional attributes that depend on trans can hence must be added here rather than at the model level.
    #    can_access_hda = trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
    #    can_access_hda = ( trans.user_is_admin() or can_access_hda )
    #    if not can_access_hda:
    #        return self.get_inaccessible_hda_dict( trans, hda )
    #    hda_dict[ 'accessible' ] = True
    #
    #    #TODO: I'm unclear as to which access pattern is right
    #    hda_dict[ 'annotation' ] = hda.get_item_annotation_str( trans.sa_session, trans.user, hda )
    #    #annotation = getattr( hda, 'annotation', hda.get_item_annotation_str( trans.sa_session, trans.user, hda ) )
    #
    #    # ---- return here if deleted AND purged OR can't access
    #    purged = ( hda.purged or hda.dataset.purged )
    #    if hda.deleted and purged:
    #        #TODO: to_dict should really go AFTER this - only summary data
    #        return trans.security.encode_dict_ids( hda_dict )
    #
    #    if expose_dataset_path:
    #        try:
    #            hda_dict[ 'file_name' ] = hda.file_name
    #        except objectstore.ObjectNotFound:
    #            log.exception( 'objectstore.ObjectNotFound, HDA %s.', hda.id )
    #
    #    hda_dict[ 'download_url' ] = url_for( 'history_contents_display',
    #        history_id = trans.security.encode_id( hda.history.id ),
    #        history_content_id = trans.security.encode_id( hda.id ) )
    #
    #    # resubmitted is not a real state
    #    hda_dict[ 'resubmitted' ] = False
    #    if hda.state == trans.app.model.Dataset.states.RESUBMITTED:
    #        hda_dict[ 'state' ] = hda.dataset.state
    #        hda_dict[ 'resubmitted' ] = True
    #
    #    # indeces, assoc. metadata files, etc.
    #    meta_files = []
    #    for meta_type in hda.metadata.spec.keys():
    #        if isinstance( hda.metadata.spec[ meta_type ].param, FileParameter ):
    #            meta_files.append( dict( file_type=meta_type ) )
    #    if meta_files:
    #        hda_dict[ 'meta_files' ] = meta_files
    #
    #    # currently, the viz reg is optional - handle on/off
    #    if trans.app.visualizations_registry:
    #        hda_dict[ 'visualizations' ] = trans.app.visualizations_registry.get_visualizations( trans, hda )
    #    else:
    #        hda_dict[ 'visualizations' ] = hda.get_visualizations()
    #    #TODO: it may also be wiser to remove from here and add as API call that loads the visualizations
    #    #           when the visualizations button is clicked (instead of preloading/pre-checking)
    #
    #    return trans.security.encode_dict_ids( hda_dict )
    #
    #def get_inaccessible_hda_dict( self, trans, hda ):
    #    return trans.security.encode_dict_ids({
    #        'id'        : hda.id,
    #        'history_id': hda.history.id,
    #        'hid'       : hda.hid,
    #        'name'      : hda.name,
    #        'state'     : hda.state,
    #        'deleted'   : hda.deleted,
    #        'visible'   : hda.visible,
    #        'accessible': False
    #    })
    #
    #def get_hda_dict_with_error( self, trans, hda=None, history_id=None, id=None, error_msg='Error' ):
    #    return trans.security.encode_dict_ids({
    #        'id'        : hda.id if hda else id,
    #        'history_id': hda.history.id if hda else history_id,
    #        'hid'       : hda.hid if hda else '(unknown)',
    #        'name'      : hda.name if hda else '(unknown)',
    #        'error'     : error_msg,
    #        'state'     : trans.model.Dataset.states.NEW
    #    })
    #
    #def get_display_apps( self, trans, hda ):
    #    display_apps = []
    #    for display_app in hda.get_display_applications( trans ).itervalues():
    #
    #        app_links = []
    #        for link_app in display_app.links.itervalues():
    #            app_links.append({
    #                'target': link_app.url.get( 'target_frame', '_blank' ),
    #                'href'  : link_app.get_display_url( hda, trans ),
    #                'text'  : gettext( link_app.name )
    #            })
    #        if app_links:
    #            display_apps.append( dict( label=display_app.name, links=app_links ) )
    #
    #    return display_apps
    #
    #def get_old_display_applications( self, trans, hda ):
    #    display_apps = []
    #    if not trans.app.config.enable_old_display_applications:
    #        return display_apps
    #
    #    for display_app in hda.datatype.get_display_types():
    #        target_frame, display_links = hda.datatype.get_display_links( hda,
    #            display_app, trans.app, trans.request.base )
    #
    #        if len( display_links ) > 0:
    #            display_label = hda.datatype.get_display_label( display_app )
    #
    #            app_links = []
    #            for display_name, display_link in display_links:
    #                app_links.append({
    #                    'target': target_frame,
    #                    'href'  : display_link,
    #                    'text'  : gettext( display_name )
    #                })
    #            if app_links:
    #                display_apps.append( dict( label=display_label, links=app_links ) )
    #
    #    return display_apps
    #
    #def set_hda_from_dict( self, trans, hda, new_data ):
    #    """
    #    Changes HDA data using the given dictionary new_data.
    #    """
    #    # precondition: access of the hda has already been checked
    #
    #    # send what we can down into the model
    #    changed = hda.set_from_dict( new_data )
    #    # the rest (often involving the trans) - do here
    #    if 'annotation' in new_data.keys() and trans.get_user():
    #        hda.add_item_annotation( trans.sa_session, trans.get_user(), hda, new_data[ 'annotation' ] )
    #        changed[ 'annotation' ] = new_data[ 'annotation' ]
    #    if 'tags' in new_data.keys() and trans.get_user():
    #        self.set_tags_from_list( trans, hda, new_data[ 'tags' ], user=trans.user )
    #    # sharing/permissions?
    #    # purged
    #
    #    if changed.keys():
    #        trans.sa_session.flush()
    #
    #    return changed
    #
    #def get_hda_job( self, hda ):
    #    # Get dataset's job.
    #    job = None
    #    for job_output_assoc in hda.creating_job_associations:
    #        job = job_output_assoc.job
    #        break
    #    return job
    #
    #def stop_hda_creating_job( self, hda ):
    #    """
    #    Stops an HDA's creating job if all the job's other outputs are deleted.
    #    """
    #    if hda.parent_id is None and len( hda.creating_job_associations ) > 0:
    #        # Mark associated job for deletion
    #        job = hda.creating_job_associations[0].job
    #        if job.state in [ self.app.model.Job.states.QUEUED, self.app.model.Job.states.RUNNING, self.app.model.Job.states.NEW ]:
    #            # Are *all* of the job's other output datasets deleted?
    #            if job.check_if_output_datasets_deleted():
    #                job.mark_deleted( self.app.config.track_jobs_in_database )
    #                self.app.job_manager.job_stop_queue.put( job.id )
    #
    #

# =============================================================================
class HDASerializer( base.ModelSerializer ):

    def __init__( self ):
        super( HDASerializer, self ).__init__()

        # most of these views build/add to the previous view
        summary_view = [
            'id', 'history_id', 'hid', 'name', 'dataset_id',
            'state', 'deleted', 'purged', 'visible'
        ]
        detailed_view = summary_view + [
            'dbkey', 'info', 'blurb', 'extension', 'create_time', 'update_time',
            'copied_from_history_dataset_association_id', 'copied_from_library_dataset_dataset_association_id',
            'metadata', 'size',
            #mixin: annotatable
            'annotation',
            #mixin: taggable
            'tags',
        ]
        extended_view = detailed_view + [
            #NOTE: sending raw 'peek' (not get_display_peek)
            'peek',
            'tool_version', 'parent_id', 'designation',
        ]

        self.serializable_keys = extended_view + [
            'display_apps',
            'display_types',
            'visualizations'
        ]
        self.views = {
            'summary'   : summary_view,
            'detailed'  : detailed_view,
            'extended'  : extended_view,
        }
        self.default_view = 'summary'

    def add_serializers( self ):
        self.serializers.update({
            'id'            : self.serialize_id,
            'history_id'    : self.serialize_id,
            'dataset_id'    : self.serialize_id,

            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
            'copied_from_history_dataset_association_id'        : self.serialize_id,
            'copied_from_library_dataset_dataset_association_id': self.serialize_id,
            'metadata'      : self.serialize_metadata,
            'size'          : lambda t, i, k: int( i.get_size() ),
            'nice_size'     : lambda t, i, k: i.get_size( nice_size=True ),
            'parent_id'     : self.serialize_id,
            #TODO: to mixin: annotatable
            'annotation'    : lambda t, i, k: i.get_item_annotation_str( t.sa_session, t.user, i ),
            #TODO: to mixin: taggable
            'tags'          : lambda t, i, k: [ tag.user_tname + ( ':' + tag.user_value if tag.user_value else '' )
                                                for tag in i.tags ],
        })

    def serialize_metadata( self, trans, hda, key ):
        not_included = [ 'dbkey' ]
        md = {}
        for name, spec in hda.metadata.spec.items():
            if name in not_included:
                continue
            val = hda.metadata.get( name )
            #NOTE: no files
            if isinstance( val, model.MetadataFile ):
                continue
            #TODO:? possibly split this off?
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr( hda.datatype, name ):
                val = getattr( hda.datatype, name )
            md[ name ] = val

        return md

    def add_deserializers( self ):
        self.deserializers.update({
            'name'          : self.deserialize_basestring,
            'genome_build'  : self.deserialize_genome_build,
            'deleted'       : self.deserialize_bool,
            'published'     : self.deserialize_bool,
            #TODO: to mixin: annotatable
            #'annotation'    : self.deserialize_annotation,
            #TODO: to mixin: taggable
            #'tags'          : lambda t, i, k, v: ,
        })
        self.deserializable_keys = self.deserializers.keys()
