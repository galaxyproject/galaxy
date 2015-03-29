"""
Manager and Serializer for Datasets.
"""
import json

from galaxy import model
from galaxy import exceptions
import galaxy.datatypes.metadata

from galaxy.managers import base
from galaxy.managers import secured
from galaxy.managers import deletable
from galaxy.managers import rbac_secured
from galaxy.managers import users

import logging
log = logging.getLogger( __name__ )


class DatasetManager( base.ModelManager, secured.AccessibleManagerMixin, deletable.PurgableManagerMixin ):
    """
    Manipulate datasets: the components contained in DatasetAssociations/DatasetInstances/HDAs/LDDAs
    """
    model_class = model.Dataset
    foreign_key_name = 'dataset'

    # TODO:?? get + error_if_uploading is common pattern, should upload check be worked into access/owed?

    def __init__( self, app ):
        super( DatasetManager, self ).__init__( app )
        self.permissions = DatasetRBACPermissions( app )
        # need for admin test
        self.user_manager = users.UserManager( app )

    def create( self, trans, manage_roles=None, access_roles=None, flush=True, **kwargs ):
        """
        Create and return a new Dataset object.
        """
        # default to NEW state on new datasets
        kwargs.update( dict( state=( kwargs.get( 'state', model.Dataset.states.NEW ) ) ) )
        dataset = model.Dataset( **kwargs )
        self.session().add( dataset )

        self.permissions.set( dataset, manage_roles, access_roles, flush=False )

        if flush:
            self.session().flush()
        return dataset

    def copy( self, dataset, **kwargs ):
        raise galaxy.exceptions.NotImplemented( 'Datasets cannot be copied' )

    def purge( self, trans, dataset, flush=True ):
        """
        Remove the object_store/file for this dataset from storage and mark
        as purged.

        :raises exceptions.ConfigDoesNotAllowException: if the instance doesn't allow
        """
        self.error_unless_dataset_purge_allowed( trans, dataset )

        # the following also marks dataset as purged and deleted
        dataset.full_delete()
        self.session().add( dataset )
        if flush:
            self.session().flush()
        return dataset

    # TODO: this may be more conv. somewhere else
    # TODO: how to allow admin bypass?
    def error_unless_dataset_purge_allowed( self, trans, item, msg=None ):
        if not self.app.config.allow_user_dataset_purge:
            msg = msg or 'This instance does not allow user dataset purging'
            raise exceptions.ConfigDoesNotAllowException( msg )
        return item

    # .... accessibility
    # datasets can implement the accessible interface, but accessibility is checked in an entirely different way
    #   than those resources that have a user attribute (histories, pages, etc.)
    def is_accessible( self, trans, dataset, user ):
        """
        Is this dataset readable/viewable to user?
        """
        if self.user_manager.is_admin( trans, user ):
            return True
        if self.has_access_permission( dataset, user ):
            return True
        return False

    def has_access_permission( self, dataset, user ):
        """
        Return T/F if the user has role-based access to the dataset.
        """
        roles = user.all_roles() if user else []
        return self.app.security_agent.can_access_dataset( roles, dataset )

    # TODO: implement above for groups
    # TODO: datatypes?
    # .... data, object_store


class DatasetRBACPermissions( object ):

    def __init__( self, app ):
        self.app = app
        self.access = rbac_secured.AccessDatasetRBACPermission( app )
        self.manage = rbac_secured.ManageDatasetRBACPermission( app )

    # TODO: temporary facade over security_agent
    def available_roles( self, trans, dataset, controller='root' ):
        return self.app.security_agent.get_legitimate_roles( trans, dataset, controller )

    def get( self, dataset, flush=True ):
        manage = self.manage.by_dataset( dataset )
        access = self.access.by_dataset( dataset )
        return ( manage, access )

    def set( self, dataset, manage_roles, access_roles, flush=True ):
        manage = self.manage.set( dataset, manage_roles or [], flush=False )
        access = self.access.set( dataset, access_roles or [], flush=flush )
        return ( manage, access )

    def set_public_with_single_manager( self, dataset, user, flush=True ):
        manage = self.manage.grant( dataset, user, flush=flush )
        access = self.access.clear( dataset, flush=False )
        return ( [ manage ], [] )

    def set_private_to_one_user( self, dataset, user, flush=True ):
        manage = self.manage.grant( user, flush=False )
        access = self.access.set_private( dataset, user, flush=flush )
        return ( [ manage ], access )


class DatasetSerializer( base.ModelSerializer, deletable.PurgableSerializerMixin ):

    def __init__( self, app ):
        super( DatasetSerializer, self ).__init__( app )
        self.dataset_manager = DatasetManager( app )

        self.default_view = 'summary'
        self.add_view( 'summary', [
            'id',
            'create_time',
            'update_time',
            'state',
            'deleted',
            'purged',
            'purgable',
            # 'object_store_id',
            # 'external_filename',
            # 'extra_files_path',
            'file_size',
            'total_size',
            'uuid',
        ])
        # could do visualizations and/or display_apps

    def add_serializers( self ):
        super( DatasetSerializer, self ).add_serializers()
        deletable.PurgableSerializerMixin.add_serializers( self )

        self.serializers.update({
            'id'            : self.serialize_id,
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,

            'uuid'          : lambda t, i, k: str( i.uuid ) if i.uuid else None,
            'file_name'     : self.serialize_file_name,
            'extra_files_path' : self.serialize_extra_files_path,
            'permissions'   : self.serialize_permissions,

            'total_size'    : lambda t, i, k: int( i.get_total_size() ),
            'file_size'     : lambda t, i, k: int( i.get_size() )
        })

    def serialize_file_name( self, trans, dataset, key ):
        """
        If the config allows or the user is admin, return the file name
        of the file that contains this dataset's data.
        """
        # TODO: allow admin
        # conifg due to cost of operation
        if not self.app.config.expose_dataset_path:
            self.skip()
        return dataset.file_name

    def serialize_extra_files_path( self, trans, dataset, key ):
        """
        If the config allows or the user is admin, return the file path.
        """
        # TODO: allow admin
        # conifg due to cost of operation
        if not self.app.config.expose_dataset_path:
            self.skip()
        return dataset.extra_files_path

    def serialize_permissions( self, trans, dataset, key ):
        """
        """
        permissions = {}
# TODO: use rbac permissions?
        return permissions


class DatasetDeserializer( base.ModelDeserializer, deletable.PurgableDeserializerMixin ):
    model_manager_class = DatasetManager

    def add_deserializers( self ):
        super( DatasetDeserializer, self ).add_deserializers()
        # not much to set here besides permissions and purged/deleted
        deletable.PurgableDeserializerMixin.add_deserializers( self )

        self.deserializers.update({
            'permissions' : self.deserialize_permissions,
        })

    def deserialize_permissions( self, trans, dataset, key, value ):
        """
        """
        permissions = {}
# TODO: test if different - it's an expensive op
# TODO: validation will be tricky
# TODO: use rbac permissions?
        return permissions


# ============================================================================= AKA DatasetInstanceManager
class DatasetAssociationManager( base.ModelManager,
                                 secured.AccessibleManagerMixin,
                                 deletable.PurgableManagerMixin ):
    """
    DatasetAssociation/DatasetInstances are intended to be working
    proxies to a Dataset, associated with either a library or a
    user/history (HistoryDatasetAssociation).
    """
    # DA's were meant to be proxies - but were never fully implemented as them
    # Instead, a dataset association HAS a dataset but contains metadata specific to a library (lda) or user (hda)
    model_class = model.DatasetInstance

    def __init__( self, app ):
        super( DatasetAssociationManager, self ).__init__( app )
        self.dataset_manager = DatasetManager( app )

    def is_accessible( self, trans, dataset_assoc, user ):
        """
        Is this DA accessible to `user`?
        """
        # defer to the dataset
        return self.dataset_manager.is_accessible( trans, dataset_assoc.dataset, user )

    def purge( self, trans, dataset_assoc, flush=True ):
        """
        Purge this DatasetInstance and the dataset underlying it.
        """
        # error here if disallowed - before jobs are stopped
        # TODO: this check may belong in the controller
        self.dataset_manager.error_unless_dataset_purge_allowed( trans, dataset_assoc )
        super( DatasetAssociationManager, self ).purge( trans, dataset_assoc, flush=flush )

        # stop any jobs outputing the dataset_assoc
        if dataset_assoc.creating_job_associations:
            job = dataset_assoc.creating_job_associations[0].job
            if not job.finished:
                # signal to stop the creating job
                job.mark_deleted( self.app.config.track_jobs_in_database )
                self.app.job_manager.job_stop_queue.put( job.id )

        # more importantly, purge underlying dataset as well
        if dataset_assoc.dataset.user_can_purge:
            self.dataset_manager.purge( trans, dataset_assoc.dataset )
        return dataset_assoc

    def by_user( self, trans, user ):
        """
        """
        raise galaxy.exceptions.NotImplemented( 'Abstract Method' )

    # def creating_job( self, trans, dataset_assoc ):
    #     # TODO: this would be even better if outputs and inputs were the underlying datasets
    #     # TODO: is this needed? Can't you use the dataset_assoc.creating_job attribute? When is this None?
    #     job = None
    #     for job_output_assoc in dataset_assoc.creating_job_associations:
    #         job = job_output_assoc.job
    #         break
    #     return job

    # def stop_creating_job( self, dataset_assoc ):
    #     """
    #     Stops an dataset_assoc's creating job if all the job's other outputs are deleted.
    #     """
    #     RUNNING_STATES = (
    #         self.app.model.Job.states.QUEUED,
    #         self.app.model.Job.states.RUNNING,
    #         self.app.model.Job.states.NEW
    #     )
    #     if dataset_assoc.parent_id is None and len( dataset_assoc.creating_job_associations ) > 0:
    #         # Mark associated job for deletion
    #         job = dataset_assoc.creating_job_associations[0].job
    #         if job.state in RUNNING_STATES:
    #             # Are *all* of the job's other output datasets deleted?
    #             if job.check_if_output_datasets_deleted():
    #                 job.mark_deleted( self.app.config.track_jobs_in_database )
    #                 self.app.job_manager.job_stop_queue.put( job.id )
    #                 return True
    #     return False


class _UnflattenedMetadataDatasetAssociationSerializer( base.ModelSerializer,
                                                        deletable.PurgableSerializerMixin ):

    def __init__( self, app ):
        self.dataset_serializer = DatasetSerializer( app )
        super( _UnflattenedMetadataDatasetAssociationSerializer, self ).__init__( app )

    def add_serializers( self ):
        super( _UnflattenedMetadataDatasetAssociationSerializer, self ).add_serializers()
        deletable.PurgableSerializerMixin.add_serializers( self )

        self.serializers.update({
            'id'            : self.serialize_id,
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,

            # underlying dataset
            'dataset'       : lambda t, i, k: self.dataset_serializer.serialize_to_view( t, i.dataset, view='summary' ),
            'dataset_id'    : self._proxy_to_dataset( key='id' ),
            #TODO: why is this named uuid!? The da doesn't have a uuid - it's the underlying dataset's uuid!
            'uuid'          : self._proxy_to_dataset( key='uuid' ),
            # 'dataset_uuid'  : self._proxy_to_dataset( key='uuid' ),
            'file_name'     : self._proxy_to_dataset( serializer=self.dataset_serializer.serialize_file_name ),
            'extra_files_path' : self._proxy_to_dataset( serializer=self.dataset_serializer.serialize_extra_files_path ),
            'permissions'   : self._proxy_to_dataset( serializer=self.dataset_serializer.serialize_permissions),
            # TODO: do the sizes proxy accurately/in the same way?
            'size'          : lambda t, i, k: int( i.get_size() ),
            'file_size'     : lambda t, i, k: self.serializers[ 'size' ]( t, i, k ),
            'nice_size'     : lambda t, i, k: i.get_size( nice_size=True ),

            # common to lddas and hdas - from mapping.py
            'copied_from_history_dataset_association_id'        : self.serialize_id,
            'copied_from_library_dataset_dataset_association_id': self.serialize_id,
            'info'          : lambda t, i, k: i.info.strip() if isinstance( i.info, basestring ) else i.info,
            'blurb'         : lambda t, i, k: i.blurb,
            'peek'          : lambda t, i, k: i.display_peek() if i.peek and i.peek != 'no peek' else None,

            'meta_files'    : self.serialize_meta_files,
            'metadata'      : self.serialize_metadata,

            'parent_id'     : self.serialize_id,
            'designation'   : lambda t, i, k: i.designation,

            # 'extended_metadata'     : self.serialize_extended_metadata,
            # 'extended_metadata_id'  : self.serialize_id,

            # remapped
            'genome_build'  : lambda t, i, k: i.dbkey,

            # derived (not mapped) attributes
            'data_type'     : lambda t, i, k: i.datatype.__class__.__module__ + '.' + i.datatype.__class__.__name__,

            # TODO: conversions
            # TODO: metadata/extra files
        })
        # this an abstract superclass, so no views created
        # because of that: we need to add a few keys that will use the default serializer
        self.serializable_keyset.update([ 'name', 'state', 'tool_version', 'extension', 'visible', 'dbkey' ])

    def _proxy_to_dataset( self, serializer=None, key=None ):
        if key:
            serializer = self.dataset_serializer.serializers.get( key )
        if serializer:
            return lambda t, i, k: serializer( t, i.dataset, key or k )
        raise TypeError( 'kwarg serializer or key needed')

    def serialize_meta_files( self, trans, dataset_assoc, key ):
        """
        Cycle through meta files and return them as a list of dictionaries.
        """
        meta_files = []
        for meta_type in dataset_assoc.metadata.spec.keys():
            if isinstance( dataset_assoc.metadata.spec[ meta_type ].param, galaxy.datatypes.metadata.FileParameter ):
                meta_files.append( dict( file_type=meta_type ) )
        return meta_files

    def serialize_metadata( self, trans, dataset_assoc, key, excluded=None ):
        """
        Cycle through metadata and return as dictionary.
        """
        # dbkey is a repeat actually (metadata_dbkey == genome_build)
        # excluded = [ 'dbkey' ] if excluded is None else excluded
        excluded = [] if excluded is None else excluded

        metadata = {}
        for name, spec in dataset_assoc.metadata.spec.items():
            if name in excluded:
                continue
            val = dataset_assoc.metadata.get( name )
            # NOTE: no files
            if isinstance( val, model.MetadataFile ):
                # only when explicitly set: fetching filepaths can be expensive
                if not self.app.config.expose_dataset_path:
                    continue
                val = val.file_name
            # TODO:? possibly split this off?
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr( dataset_assoc.datatype, name ):
                val = getattr( dataset_assoc.datatype, name )
            metadata[ name ] = val

        return metadata


class DatasetAssociationSerializer( _UnflattenedMetadataDatasetAssociationSerializer ):
    # TODO: remove this class - metadata should be a sub-object instead as in the superclass

    def add_serializers( self ):
        super( DatasetAssociationSerializer, self ).add_serializers()
        # remove the single nesting key here
        del self.serializers[ 'metadata' ]

    def serialize( self, trans, dataset_assoc, keys ):
        """
        Override to add metadata as flattened keys on the serialized DatasetInstance.
        """
        # if 'metadata' isn't removed from keys here serialize will retrieve the un-serializable MetadataCollection
        # TODO: remove these when metadata is sub-object
        KEYS_HANDLED_SEPARATELY = ( 'metadata', )
        left_to_handle = self.pluck_from_list( keys, KEYS_HANDLED_SEPARATELY )
        serialized = super( DatasetAssociationSerializer, self ).serialize( trans, dataset_assoc, keys )

        # add metadata directly to the dict instead of as a sub-object
        if 'metadata' in left_to_handle:
            metadata = self.prefixed_metadata( trans, dataset_assoc )
            serialized.update( metadata )
        return serialized

    # TODO: this is more util/gen. use
    def pluck_from_list( self, l, elems ):
        """
        Removes found elems from list l and returns list of found elems if found.
        """
        found = []
        for elem in elems:
            try:
                index = l.index( elem )
                found.append( l.pop( index ) )
            except ValueError:
                pass
        return found

    def prefixed_metadata( self, trans, dataset_assoc ):
        """
        Adds (a prefixed version of) the DatasetInstance metadata to the dict,
        prefixing each key with 'metadata_'.
        """
        # build the original, nested dictionary
        metadata = self.serialize_metadata( trans, dataset_assoc, 'metadata' )

        # prefix each key within and return
        prefixed = {}
        for key, val in metadata.items():
            prefixed_key = 'metadata_' + key
            prefixed[ prefixed_key ] = val
        return prefixed


class DatasetAssociationDeserializer( base.ModelDeserializer, deletable.PurgableDeserializerMixin ):

    def add_deserializers( self ):
        super( DatasetAssociationDeserializer, self ).add_deserializers()
        deletable.PurgableDeserializerMixin.add_deserializers( self )

        self.deserializers.update({
            'name'          : self.deserialize_basestring,
            'info'          : self.deserialize_basestring,
        })
        self.deserializable_keyset.update( self.deserializers.keys() )

    def deserialize_metadata( self, trans, dataset_assoc, metadata_key, metadata_dict ):
        """
        """
        self.validate.type( metadata_key, metadata_dict, dict )
        returned = {}
        for key, val in metadata_dict.items():
            returned[ key ] = self.deserialize_metadatum( trans, dataset_assoc, key, val )
        return returned

    def deserialize_metadatum( self, trans, dataset_assoc, key, val ):
        """
        """
        if key not in dataset_assoc.datatype.metadata_spec:
            return
        metadata_specification = dataset_assoc.datatype.metadata_spec[ key ]
        if metadata_specification.get( 'readonly' ):
            return
        unwrapped_val = metadata_specification.unwrap( val )
        setattr( dataset_assoc.metadata, key, unwrapped_val )
        # ...?
        return unwrapped_val


class DatasetAssociationFilters( base.ModelFilterParser, deletable.PurgableFiltersMixin ):

    def _datatype_from_string( class_str ):
        """
        """
        return self.app.datatypes_registry.get_datatype_class_by_name( class_str )

    def _add_parsers( self ):
        super( DatasetAssociationFilters, self )._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers( self )

        self.orm_filter_parsers.update({
            'name'      : { 'op': ( 'eq', 'contains', 'like' ) },
            'state'     : { 'op': ( 'eq', 'in' ) },
            'visible'   : { 'op': ( 'eq' ), 'val': self.parse_bool },
            'genome_build' : { 'op': ( 'eq', 'contains', 'like' ) },
        })
        self.fn_filter_parsers.update({
            'data_type' : {
                'op': {
                    'eq' : self.eq_datatype,
                    'is' : self.is_datatype
                }
            }
        })

    def eq_datatype( self, dataset_assoc, class_str ):
        """
        """
        comparison_class = self._datatype_from_string( class_str )
        return ( comparison_class
             and dataset_assoc.datatype.__class__ == comparison_class )

    def is_datatype( self, dataset_assoc, class_strs ):
        """
        """
        comparison_classes = []
        for class_str in class_strs.split( ',' ):
            datatype_class = self._datatype_from_string( class_str )
            if datatype_class:
                comparison_classes.append( datatype_class )
        return ( comparison_classes
             and isinstance( dataset_assoc.datatype, comparison_classes ) )
