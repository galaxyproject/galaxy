"""
Manager and Serializer for HDAs.

HistoryDatasetAssociations (HDAs) are datasets contained or created in a
history.
"""

import gettext

from galaxy import model
from galaxy import exceptions

import base
import histories
import datasets

import galaxy.web
import galaxy.datatypes.metadata
from galaxy import objectstore


# =============================================================================
class HDAManager( datasets.DatasetAssociationManager, base.OwnableModelInterface ):
    #TODO: move what makes sense into DatasetManager
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

    def is_accessible( self, trans, hda, user ):
        """
        """
        if self.is_owner( trans, hda, user ):
            return True
        return super( HDAManager, self ).is_accessible( trans, hda, user )

    def is_owner( self, trans, hda, user ):
        """
        Use history to see if current user owns HDA.
        """
        #TODO: this may be slow due to HistoryManager instantiation and possible 2nd transaction to get the hda.history
        return histories.HistoryManager( self.app ).is_owner( trans, hda.history, user )

    def create( self, trans, history=None, dataset=None, flush=True, **kwargs ):
        """
        Create a new hda optionally passing in it's history and dataset.

        ..note: to explicitly set hid to `None` you must pass in `hid=None`, otherwise
        it will be automatically set.
        """
        if not dataset:
            kwargs[ 'create_dataset' ] = True
        hda = super( HDAManager, self ).create( trans, flush=flush,
            history=history, dataset=dataset, sa_session=trans.sa_session, **kwargs )

        if history:
            set_hid = not ( 'hid' in kwargs )
            history.add_dataset( hda )
        #TODO:?? some internal sanity check here (or maybe in add_dataset) to make sure hids are not duped?

        trans.sa_session.add( hda )
        if flush:
            trans.sa_session.flush()
        return hda

    def copy( self, trans, hda, history=None, **kwargs ):
        """
        Copy and return the given HDA.
        """
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

        #TODO: update from kwargs?

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
        """
        """
        return ldda.to_history_dataset_association( history, add_to_history=True )

#    def by_history_id( self, trans, history_id, filters=None, **kwargs ):
#        history_id_filter = self.model_class.history_id == history_id
#        filters = self._munge_filters( history_id_filter, filters )
#        return self.list( trans, filters=filters, **kwargs )

#    #def by_history( self, trans, history, filters=None, **kwargs ):
#    #    return history.datasets

    #def by_user( self, trans, user ):
    #    pass

    def purge( self, trans, hda ):
        """
        """
        # error here if disallowed - before jobs are stopped
        #TODO: poss. move to DatasetAssociationManager
        self.dataset_mgr.error_unless_dataset_purge_allowed( trans, hda )
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
                    'text'  : gettext.gettext( link_app.name )
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
                        'text'  : gettext.gettext( display_name )
                    })
                if app_links:
                    display_apps.append( dict( label=display_label, links=app_links ) )

        return display_apps

    def get_visualizations( self, trans, hda ):
        """
        """
        # use older system if registry is off in the config
        if not trans.app.visualizations_registry:
           return hda.get_visualizations()
        return trans.app.visualizations_registry.get_visualizations( trans, hda )

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


    #def get_hda_job( self, hda ):
    #    # Get dataset's job.
    #    job = None
    #    for job_output_assoc in hda.creating_job_associations:
    #        job = job_output_assoc.job
    #        break
    #    return job

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

# =============================================================================
class HDASerializer( base.ModelSerializer ):
    #TODO: inherit from datasets.DatasetAssociationSerializer
    #TODO: move what makes sense into DatasetSerializer

    def __init__( self, app ):
        super( HDASerializer, self ).__init__( app )
        self.hda_mgr = HDAManager( app )

        # most of these views build/add to the previous view
        summary_view = [
            'id', 'name',
            'history_id', 'hid', 'history_content_type',
            #'dataset_id',
            'state', 'extension',
            'deleted', 'purged', 'visible', 'resubmitted',
            'type', 'url'
        ]
        inaccessible = [
            'id', 'name', 'history_id', 'hid', 'history_content_type',
            'state', 'deleted', 'visible'
        ]
        detailed_view = [
            'id', 'name', 'model_class',
            'history_id', 'hid',
            # why include if model_class is there?
            'hda_ldda', 'history_content_type',
            'state',
            #TODO: accessible needs to go away
            'accessible',
            'deleted', 'purged', 'visible', 'resubmitted',

            # remapped
            'genome_build', 'misc_info', 'misc_blurb',
            'file_ext', 'file_size',

            'create_time', 'update_time',
            'metadata', 'meta_files', 'data_type',
            'peek',

            #TODO: why is this named uuid!? The hda doesn't have a uuid - it's the underlying dataset's uuid!
            'uuid',
            # should be:
            #'dataset_uuid',

            'file_path',
            'display_apps',
            'display_types',
            'visualizations',
            
            #'url',
            'download_url',

            #mixin: annotatable
            'annotation',
            #mixin: taggable
            'tags',

            'api_type'
        ]
        extended_view = detailed_view + [
            #NOTE: sending raw 'peek' (not get_display_peek)
            'tool_version', 'parent_id', 'designation',
        ]

        self.serializable_keys = extended_view + [
        ]
        self.views = {
            'summary'   : summary_view,
            'detailed'  : detailed_view,
            'extended'  : extended_view,
        }
        self.default_view = 'summary'

    def add_serializers( self ):
        self.serializers.update({
            'model_class'   : lambda *a: 'HistoryDatasetAssociation',
            #TODO: accessible needs to go away
            'accessible'    : lambda *a: True,

            'id'            : self.serialize_id,
            'history_id'    : self.serialize_id,
            'history_content_type': lambda *a: 'dataset',
            'dataset_id'    : self.serialize_id,
            'hda_ldda'      : lambda *a: 'hda',

            # remapped
            'info'          : lambda t, i, k: i.info.strip() if isinstance( i.info, basestring ) else i.info,
            'misc_info'     : lambda t, i, k: self.serializers[ 'info' ]( t, i, k ),
            'misc_blurb'    : lambda t, i, k: i.blurb,
            'genome_build'  : lambda t, i, k: i.dbkey,
            'file_ext'      : lambda t, i, k: i.extension,
            'file_size'     : lambda t, i, k: self.serializers[ 'size' ]( t, i, k ),

            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
            'copied_from_history_dataset_association_id'        : self.serialize_id,
            'copied_from_library_dataset_dataset_association_id': self.serialize_id,

            'resubmitted'   : lambda t, i, k: i._state == t.app.model.Dataset.states.RESUBMITTED,

            'meta_files'    : self.serialize_meta_files,
            'file_path'     : self.serialize_file_path,

            'size'          : lambda t, i, k: int( i.get_size() ),
            'nice_size'     : lambda t, i, k: i.get_size( nice_size=True ),
            'data_type'     : lambda t, i, k: i.datatype.__class__.__module__ + '.' + i.datatype.__class__.__name__,
            'peek'          : lambda t, i, k: i.display_peek() if i.peek and i.peek != 'no peek' else None,

            # currently we send this sub-obj flattened (see serialize and add_flattened_metadata below)
            #'metadata'      : self.serialize_metadata,
            #   make it available here under a different key
            'metadata_dict' : self.serialize_metadata,

            'parent_id'     : self.serialize_id,
            'annotation'    : self.serialize_annotation,
            'tags'          : self.serialize_tags,

            'display_apps'  : lambda t, i, k: self.hda_mgr.get_display_apps( t, i ),
            'display_types' : lambda t, i, k: self.hda_mgr.get_old_display_applications( t, i ),
            'visualizations': lambda t, i, k: self.hda_mgr.get_visualizations( t, i ),

            'dataset_uuid'  : lambda t, i, k: str( i.dataset.uuid ) if i.dataset.uuid else None,
            'uuid'          : lambda t, i, k: self.serializers[ 'dataset_uuid' ]( t, i, k ),

            #'url'   : url_for( 'history_content_typed', history_id=encoded_history_id, id=encoded_id, type="dataset" ),
            #TODO: this intermittently causes a routes.GenerationException - temp use the legacy route to prevent this
            #   see also: https://trello.com/c/5d6j4X5y
            #   see also: https://sentry.galaxyproject.org/galaxy/galaxy-main/group/20769/events/9352883/
            'url'           : lambda t, i, k: galaxy.web.url_for( 'history_content',
                history_id=t.security.encode_id( i.history_id ), id=t.security.encode_id( i.id ) ),

            'urls'          : self.serialize_urls,
            'download_url'  : lambda t, i, k: galaxy.web.url_for( 'history_contents_display',
                history_id=t.security.encode_id( i.history.id ),
                history_content_id=t.security.encode_id( i.id ) ),

            'api_type'      : lambda *a: 'file',
            'type'          : lambda *a: 'file'
        })

    def serialize( self, trans, hda, keys ):
        """
        """
        # if 'metadata' isn't removed from keys here serialize will retrieve the un-serializable MetadataCollection
        #TODO: remove these when metadata is sub-object
        KEYS_HANDLED_SEPARATELY = ( 'metadata', )
        left_to_handle = self.pluck_from_list( keys, KEYS_HANDLED_SEPARATELY )
        serialized = super( HDASerializer, self ).serialize( trans, hda, keys )

        if 'metadata' in left_to_handle:
            # we currently add metadata directly to the dict instead of as a sub-object
            serialized.update( self.prefixed_metadata( trans, hda ) )
        return serialized

    #TODO: this is more util/gen. use
    def pluck_from_list( self, l, elems ):
        """
        Removes found elems from list l and returns list of found elems if found.
        """
        found = []
        for elem in elems:
            try:
                index = l.index( elem )
                found.append( l.pop( index ) )
            except ValueError, val_err:
                pass
        return found

    def prefixed_metadata( self, trans, hda ):
        """
        Adds (a prefixed version of) the hda metadata to the dict, prefixing each key
        with 'metadata_'.
        """
        metadata = self.serialize_metadata( trans, hda, 'metadata' )
        #TODO: this is factored out for removal - metadata should be a sub-object instead:
        #   i.e.  'metadata' : self.serialize_metadata,
        prefixed = {}
        for key, val in metadata.items():
            prefixed_key = 'metadata_' + key
            prefixed[ prefixed_key ] = val
        return prefixed

    def serialize_metadata( self, trans, hda, key, excluded=None ):
        """
        """
        # dbkey is a repeat actually (metadata_dbkey == genome_build)
        #excluded = [ 'dbkey' ] if excluded is None else excluded
        excluded = [] if excluded is None else excluded

        metadata = {}
        for name, spec in hda.metadata.spec.items():
            if name in excluded:
                continue
            val = hda.metadata.get( name )
            #NOTE: no files
            if isinstance( val, model.MetadataFile ):
                # only when explicitly set: fetching filepaths can be expensive
                if not trans.app.config.expose_dataset_path:
                    continue
                val = val.file_name
            #TODO:? possibly split this off?
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr( hda.datatype, name ):
                val = getattr( hda.datatype, name )
            metadata[ name ] = val

        return metadata

    # add to serialize_metadata above
    def serialize_meta_files( self, trans, hda, key ):
        """
        """
        meta_files = []
        for meta_type in hda.metadata.spec.keys():
            if isinstance( hda.metadata.spec[ meta_type ].param, galaxy.datatypes.metadata.FileParameter ):
                meta_files.append( dict( file_type=meta_type ) )
        return meta_files

    #def file_info #TODO
    #TODO: and to dataset instead (passing through object store)
    def serialize_file_path( self, trans, hda, key ):
        """
        """
#TODO: allow admin
        if trans.app.config.expose_dataset_path:
            try:
                return hda.file_name
            except objectstore.ObjectNotFound:
                log.exception( 'objectstore.ObjectNotFound, HDA %s.', hda.id )
        return None

    def serialize_urls( self, trans, hda, key ):
        """
        """
        url_for = galaxy.web.url_for
        encoded_id = trans.security.encode_id( hda.id )
        urls = {
            'purge'         : url_for( controller='dataset', action='purge_async', dataset_id=encoded_id ),
            'display'       : url_for( controller='dataset', action='display', dataset_id=encoded_id, preview=True ),
            'edit'          : url_for( controller='dataset', action='edit', dataset_id=encoded_id ),
            'download'      : url_for( controller='dataset', action='display',
                                       dataset_id=encoded_id, to_ext=hda.extension ),
            'report_error'  : url_for( controller='dataset', action='errors', id=encoded_id ),
            'rerun'         : url_for( controller='tool_runner', action='rerun', id=encoded_id ),
            'show_params'   : url_for( controller='dataset', action='show_params', dataset_id=encoded_id ),
            'visualization' : url_for( controller='visualization', action='index',
                                       id=encoded_id, model='HistoryDatasetAssociation' ),
            'meta_download' : url_for( controller='dataset', action='get_metadata_file',
                                       hda_id=encoded_id, metadata_name='' ),
        }
        return urls


    #TODO: move into serializer below
    #def get_hda_dict( self, trans, hda ):
    #    """
    #    Return full details of this HDA in dictionary form.
    #    """
    #    #precondition: the user's access to this hda has already been checked
    #    #TODO:?? postcondition: all ids are encoded (is this really what we want at this level?)
    #    expose_dataset_path = trans.user_is_admin() or trans.app.config.expose_dataset_path
    #    hda_dict = hda.to_dict( view='element', expose_dataset_path=expose_dataset_path )
    #    hda_dict[ 'api_type' ] = "file"
    #
    #    # Add additional attributes that depend on trans must be added here rather than at the model level.
    #    can_access_hda = trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
    #    can_access_hda = ( trans.user_is_admin() or can_access_hda )
    #    if not can_access_hda:
    #        return self.get_inaccessible_hda_dict( trans, hda )
    #    hda_dict[ 'accessible' ] = True
    #
    #    #TODO: I'm unclear as to which access pattern is right
    #    hda_dict[ 'annotation' ] = hda.get_item_annotation_str( trans.sa_session, hda.history.user, hda )
    #    #annotation = getattr( hda, 'annotation', hda.get_item_annotation_str( trans.sa_session, trans.user, hda ) )
    #
    #    # ---- return here if deleted AND purged OR can't access
    #    purged = ( hda.purged or hda.dataset.purged )
    #    if ( hda.deleted and purged ):
    #        #TODO: to_dict should really go AFTER this - only summary data
    #        return trans.security.encode_dict_ids( hda_dict )
    #
    #    if expose_dataset_path:
    #        try:
    #            hda_dict[ 'file_name' ] = hda.file_name
    #        except objectstore.ObjectNotFound:
    #            log.exception( 'objectstore.ObjectNotFound, HDA %s.', hda.id )
    #
    #    hda_dict[ 'download_url' ] = galaxy.web.url_for( 'history_contents_display',
    #        history_id = trans.security.encode_id( hda.history.id ),
    #        history_content_id = trans.security.encode_id( hda.id ) )
    #
    #    # indeces, assoc. metadata files, etc.
    #    meta_files = []
    #    for meta_type in hda.metadata.spec.keys():
    #        if isinstance( hda.metadata.spec[ meta_type ].param, galaxy.datatypes.metadata.FileParameter ):
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
    #    # ---- return here if deleted
    #    if hda.deleted and not purged:
    #        return trans.security.encode_dict_ids( hda_dict )
    #
    #    return trans.security.encode_dict_ids( hda_dict )

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

    #def get_hda_dict_with_error( self, trans, hda=None, history_id=None, id=None, error_msg='Error' ):
    #    return trans.security.encode_dict_ids({
    #        'id'        : hda.id if hda else id,
    #        'history_id': hda.history.id if hda else history_id,
    #        'hid'       : hda.hid if hda else '(unknown)',
    #        'name'      : hda.name if hda else '(unknown)',
    #        'error'     : error_msg,
    #        'state'     : trans.model.Dataset.states.NEW
    #    })


# =============================================================================
class HDADeserializer( base.ModelDeserializer ):
    """
    Interface/service object for validating and deserializing dictionaries into histories.
    """

    def __init__( self, app ):
        super( HDADeserializer, self ).__init__( app )
        self.hda_mgr = HDAManager( app )

    #assumes: incoming from json.loads and sanitized
    def add_deserializers( self ):
        super( HDADeserializer, self ).add_deserializers()
        self.deserializers.update({
            'name'          : self.deserialize_basestring,
            'visible'       : self.deserialize_bool,

            # remapped
            'genome_build'  : lambda t, i, k, v: self.deserialize_genome_build( t, i, 'dbkey', v ),
            'misc_info'     : lambda t, i, k, v: self.deserialize_basestring( t, i, 'info', v ),

            # mixin: annotatable
            'annotation'    : self.deserialize_annotation,
            # mixin: taggable
            'tags'          : self.deserialize_tags,

            # mixin: deletable
            'deleted'       : self.deserialize_bool,
            # sharable
            'published'     : self.deserialize_bool,
            'importable'    : self.deserialize_bool,

        })
        self.deserializable_keys = self.deserializers.keys()
