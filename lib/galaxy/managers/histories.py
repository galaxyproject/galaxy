"""
Manager and Serializer for histories.

Histories are containers for datasets or dataset collections
created (or copied) by users over the course of an analysis.
"""

from galaxy import exceptions
from galaxy import model
from galaxy.model import orm

import base
import sharable
import hdas
import galaxy.managers.collections_util

import galaxy.web

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class HistoryManager( sharable.SharableModelManager, base.PurgableModelInterface ):
    """
    """
    model_class = model.History
    default_order_by = ( model.History.create_time, )
    foreign_key_name = 'history'
    user_share_model = model.HistoryUserShareAssociation

    def __init__( self, app, *args, **kwargs ):
        """
        """
        super( HistoryManager, self ).__init__( app, *args, **kwargs )
        self.hda_mgr = hdas.HDAManager( app )

    # ......................................................................... crud
    def copy( self, trans, history, user, **kwargs ):
        """
        """
        return history.copy( target_user=user, **kwargs )

    def get_current( self, trans ):
        """
        """
        return trans.get_history()

    def set_current( self, trans, history ):
        """
        """
        trans.set_history( history )
        return history

    def set_current_by_id( self, trans, history_id ):
        """
        """
        return self.set_current( trans, self.by_id( trans, history_id ) )

    def most_recent( self, trans, user, **kwargs ):
        """
        """
        if not user:
            return None if trans.history.deleted else trans.history
        desc_update_time = self.model_class.table.c.update_time
        return self.by_user( trans, user, order_by=desc_update_time, limit=1, **kwargs )

    # ......................................................................... sharable
    # overriding to handle anonymous users' current histories in both cases
    def by_user( self, trans, user, **kwargs ):
        """
        Get all the histories for a given user (allowing anon users' theirs)
        ordered by update time.
        """
        # handle default and/or anonymous user (which still may not have a history yet)
        if self.user_mgr.is_anonymous( user ):
            current_history = trans.get_history()
            return [ current_history ] if current_history else []

        return super( HistoryManager, self ).by_user( trans, user, **kwargs )

    def is_owner( self, trans, history, user ):
        """
        True if the current user is the owner of the given history.
        """
        # anon users are only allowed to view their current history
        if self.user_mgr.is_anonymous( user ) and history == trans.get_history():
            return True
        return super( HistoryManager, self ).is_owner( trans, history, user )

    # ......................................................................... purgable
    def purge( self, trans, history, flush=True, **kwargs ):
        """
        """
        self.hda_mgr.dataset_mgr.error_unless_dataset_purge_allowed( trans, history )

        # First purge all the datasets
        for hda in history.datasets:
            if not hda.purged:
                self.hda_mgr.purge( trans, hda, flush=True )

        # Now mark the history as purged
        super( HistoryManager, self ).purge( trans, history, flush=flush, **kwargs )

    # ......................................................................... contents
    

    # ......................................................................... serialization
    #TODO: move to serializer (i.e. history with contents attr)
    def _get_history_data( self, trans, history ):
        """
        Returns a dictionary containing ``history`` and ``contents``, serialized
        history and an array of serialized history contents respectively.
        """
        #TODO: instantiate here? really?
        history_serializer = HistorySerializer( self.app )
        hda_serializer = hdas.HDASerializer( self.app )
        collection_dictifier = galaxy.managers.collections_util.dictify_dataset_collection_instance

        history_dictionary = {}
        contents_dictionaries = []
        try:
            history_dictionary = history_serializer.serialize_to_view( trans, history, view='detailed' )

            #for content in history.contents_iter( **contents_kwds ):
            for content in history.contents_iter( types=[ 'dataset', 'dataset_collection' ] ):
                contents_dict = {}

                if isinstance( content, trans.app.model.HistoryDatasetAssociation ):
                    contents_dict = hda_serializer.serialize_to_view( trans, content, view='detailed' )

                elif isinstance( content, trans.app.model.HistoryDatasetCollectionAssociation ):
                    try:
                        service = trans.app.dataset_collections_service
                        dataset_collection_instance = service.get_dataset_collection_instance(
                            trans=trans,
                            instance_type='history',
                            id=trans.security.encode_id( content.id ),
                        )
                        contents_dict = collection_dictifier( dataset_collection_instance,
                            security=trans.security, parent=dataset_collection_instance.history, view="element" )

                    except Exception, exc:
                        log.exception( "Error in history API at listing dataset collection: %s", exc )
                        #TODO: return some dict with the error

                contents_dictionaries.append( contents_dict )

        except Exception, exc:
            user_id = str( trans.user.id ) if trans.user else '(anonymous)'
            log.exception( 'Error bootstrapping history for user %s: %s', user_id, str( exc ) )
            message = ( 'An error occurred getting the history data from the server. '
                      + 'Please contact a Galaxy administrator if the problem persists.' )
            history_dictionary[ 'error' ] = message

        return {
            'history'   : history_dictionary,
            'contents'  : contents_dictionaries
        }

    # remove this
    def get_state_counts( self, trans, history, exclude_deleted=True, exclude_hidden=False ):
        """
        """
        #TODO: the default flags above may not make a lot of sense (T,T?)
        state_counts = {}
        for state in trans.app.model.Dataset.states.values():
            state_counts[ state ] = 0

        #TODO:?? collections and coll. states?
        for hda in history.datasets:
            if exclude_deleted and hda.deleted:
                continue
            if exclude_hidden and not hda.visible:
                continue
            state_counts[ hda.state ] = state_counts[ hda.state ] + 1
        return state_counts

    # remove this
    def get_state_ids( self, trans, history ):
        """
        """
        state_ids = {}
        for state in trans.app.model.Dataset.states.values():
            state_ids[ state ] = []

        #TODO:?? collections and coll. states?
        for hda in history.datasets:
            #TODO: do not encode ids at this layer
            encoded_id = trans.security.encode_id( hda.id )
            state_ids[ hda.state ].append( encoded_id )
        return state_ids

    #TODO: remove this (is state used/useful?)
    def get_history_state( self, trans, history ):
        """Returns the history state based on the states of the HDAs it contains.
        """
        states = trans.app.model.Dataset.states

        # (default to ERROR)
        state = states.ERROR

        #TODO: history_state and state_counts are classically calc'd at the same time
        #   so this is rel. ineff. - if we keep this...
        hda_state_counts = self.get_state_counts( trans, history, exclude_deleted=False )
        num_hdas = sum( hda_state_counts.values() )
        if num_hdas == 0:
            state = states.NEW

        else:
            if( ( hda_state_counts[ states.RUNNING ] > 0 )
            or  ( hda_state_counts[ states.SETTING_METADATA ] > 0 )
            or  ( hda_state_counts[ states.UPLOAD ] > 0 ) ):
                state = states.RUNNING
            #TODO: this method may be more useful if we *also* polled the histories jobs here too

            elif hda_state_counts[ states.QUEUED ] > 0:
                state = states.QUEUED

            elif( ( hda_state_counts[ states.ERROR ] > 0 )
            or    ( hda_state_counts[ states.FAILED_METADATA ] > 0 ) ):
                state = states.ERROR

            elif hda_state_counts[ states.OK ] == num_hdas:
                state = states.OK

        return state


## =============================================================================
class HistorySerializer( sharable.SharableModelSerializer ):
    """
    Interface/service object for serializing histories into dictionaries.
    """

    def __init__( self, app ):
        super( HistorySerializer, self ).__init__( app )
        self.history_mgr = HistoryManager( app )
        self.hda_mgr = hdas.HDAManager( app )
        self.hda_serializer = hdas.HDASerializer( app )

        summary_view = [
            'id',
            'model_class',
            'name',
            'deleted', 'purged',
            'published',
            #'count'
            'annotation',
            'tags',
            'url'
        ]
        # in the Historys' case, each of these views includes the keys from the previous
        detailed_view = summary_view + [
            'contents_url',
            #'hdas',
            'empty',
            'size', 'nice_size',
            'user_id',
            'create_time', 'update_time',
            'importable', 'slug',
            'genome_build',
            #username_and_slug = ( '/' ).join(( 'u', history.user.username, 'h', history_dict[ 'slug' ] ))
            #TODO: remove the next three - instead getting the same info from the 'hdas' list
            'state',
            'state_details',
            'state_ids',
        ]
        extended_view = detailed_view + [
        ]
        self.serializable_keys = extended_view + []
        self.views = {
            'summary'   : summary_view,
            'detailed'  : detailed_view,
            'extended'  : extended_view,
        }
        self.default_view = 'summary'

    #assumes: outgoing to json.dumps and sanitized
    def add_serializers( self ):
        super( HistorySerializer, self ).add_serializers()
        self.serializers.update({
            'model_class'   : lambda *a: 'History',
            'id'            : self.serialize_id,
            'count'         : lambda trans, item, key: len( item.datasets ),
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
            'user_id'       : self.serialize_id,
            'size'          : lambda t, i, k: int( i.get_disk_size() ),
            'nice_size'     : lambda t, i, k: i.get_disk_size( nice_size=True ),

            'annotation'    : self.serialize_annotation,
            'tags'          : self.serialize_tags,
            'url'           : lambda t, i, k: galaxy.web.url_for( 'history', id=t.security.encode_id( i.id ) ),
            'contents_url'  : lambda t, i, k:
                galaxy.web.url_for( 'history_contents', history_id=t.security.encode_id( i.id ) ),
            'empty'         : lambda t, i, k: len( i.datasets ) <= 0,

            'hdas'          : lambda t, i, k: [ t.security.encode_id( hda.id ) for hda in i.datasets ],
            'state'         : lambda t, i, k: self.history_mgr.get_history_state( t, i ),
            'state_details' : lambda t, i, k: self.history_mgr.get_state_counts( t, i ),
            'state_ids'     : lambda t, i, k: self.history_mgr.get_state_ids( t, i ),
            'contents'      : self.serialize_contents
        })

    def serialize_contents( self, trans, history, key ):
        for content in history.contents_iter( types=[ 'dataset', 'dataset_collection' ] ):
            contents_dict = {}
            if isinstance( content, trans.app.model.HistoryDatasetAssociation ):
                contents_dict = self.hda_serializer.serialize_to_view( trans, hda, view='detailed' )
            elif isinstance( content, trans.app.model.HistoryDatasetCollectionAssociation ):
                contents_dict = self.serialize_collection( trans, collection )
            contents_dictionaries.append( contents_dict )

    def serialize_collection( self, trans, collection ):
        service = trans.app.dataset_collections_service
        dataset_collection_instance = service.get_dataset_collection_instance(
            trans=trans,
            instance_type='history',
            id=trans.security.encode_id( collection.id ),
        )
        return collection_dictifier( dataset_collection_instance,
            security=trans.security, parent=dataset_collection_instance.history, view="element" )


# =============================================================================
class HistoryDeserializer( sharable.SharableModelDeserializer ):
    """
    Interface/service object for validating and deserializing dictionaries into histories.
    """

    def __init__( self, app ):
        super( HistoryDeserializer, self ).__init__( app )
        self.history_mgr = HistoryManager( app )

    #assumes: incoming from json.loads and sanitized
    def add_deserializers( self ):
        super( HistoryDeserializer, self ).add_deserializers()
        self.deserializers.update({
            'name'          : self.deserialize_basestring,
            'genome_build'  : self.deserialize_genome_build,
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
