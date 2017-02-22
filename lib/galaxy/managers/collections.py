from galaxy import model
from galaxy.dataset_collections import builder
from galaxy.dataset_collections.matching import MatchingCollections
from galaxy.dataset_collections.registry import DatasetCollectionTypesRegistry
from galaxy.dataset_collections.type_description import CollectionTypeDescriptionFactory
from galaxy.exceptions import ItemAccessibilityException
from galaxy.exceptions import MessageException
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers import hdas  # TODO: Refactor all mixin use into managers.
from galaxy.managers import histories
from galaxy.managers import lddas
from galaxy.managers import tags
from galaxy.managers.collections_util import validate_input_element_identifiers
from galaxy.util import odict
from galaxy.util import validation
import logging
log = logging.getLogger( __name__ )


ERROR_INVALID_ELEMENTS_SPECIFICATION = "Create called with invalid parameters, must specify element identifiers."
ERROR_NO_COLLECTION_TYPE = "Create called without specifing a collection type."


class DatasetCollectionManager( object ):
    """
    Abstraction for interfacing with dataset collections instance - ideally abstarcts
    out model and plugin details.
    """
    ELEMENTS_UNINITIALIZED = object()

    def __init__( self, app ):
        self.type_registry = DatasetCollectionTypesRegistry( app )
        self.collection_type_descriptions = CollectionTypeDescriptionFactory( self.type_registry )
        self.model = app.model
        self.security = app.security

        self.hda_manager = hdas.HDAManager( app )
        self.history_manager = histories.HistoryManager( app )
        self.tag_manager = tags.TagManager( app )
        self.ldda_manager = lddas.LDDAManager( app )

    def create(
        self,
        trans,
        parent,
        # PRECONDITION: security checks on ability to add to parent
        # occurred during load.
        name,
        collection_type,
        element_identifiers=None,
        elements=None,
        implicit_collection_info=None,
        trusted_identifiers=None,  # Trust preloaded element objects
    ):
        """
        """
        # Trust embedded, newly created objects created by tool subsystem.
        if trusted_identifiers is None:
            trusted_identifiers = implicit_collection_info is not None

        if element_identifiers and not trusted_identifiers:
            validate_input_element_identifiers( element_identifiers )

        dataset_collection = self.create_dataset_collection(
            trans=trans,
            collection_type=collection_type,
            element_identifiers=element_identifiers,
            elements=elements,
        )

        if isinstance( parent, model.History ):
            dataset_collection_instance = self.model.HistoryDatasetCollectionAssociation(
                collection=dataset_collection,
                name=name,
            )
            if implicit_collection_info:
                for input_name, input_collection in implicit_collection_info[ "implicit_inputs" ]:
                    dataset_collection_instance.add_implicit_input_collection( input_name, input_collection )
                for output_dataset in implicit_collection_info.get( "outputs" ):
                    if output_dataset not in trans.sa_session:
                        output_dataset = trans.sa_session.query( type( output_dataset ) ).get( output_dataset.id )
                    if isinstance( output_dataset, model.HistoryDatasetAssociation ):
                        output_dataset.hidden_beneath_collection_instance = dataset_collection_instance
                    elif isinstance( output_dataset, model.HistoryDatasetCollectionAssociation ):
                        dataset_collection_instance.add_implicit_input_collection( input_name, input_collection )
                    else:
                        # dataset collection, don't need to do anything...
                        pass
                    trans.sa_session.add( output_dataset )

                dataset_collection_instance.implicit_output_name = implicit_collection_info[ "implicit_output_name" ]

            log.debug("Created collection with %d elements" % ( len( dataset_collection_instance.collection.elements ) ) )
            # Handle setting hid
            parent.add_dataset_collection( dataset_collection_instance )

        elif isinstance( parent, model.LibraryFolder ):
            dataset_collection_instance = self.model.LibraryDatasetCollectionAssociation(
                collection=dataset_collection,
                folder=parent,
                name=name,
            )

        else:
            message = "Internal logic error - create called with unknown parent type %s" % type( parent )
            log.exception( message )
            raise MessageException( message )

        return self.__persist( dataset_collection_instance )

    def create_dataset_collection(
        self,
        trans,
        collection_type,
        element_identifiers=None,
        elements=None,
    ):
        if element_identifiers is None and elements is None:
            raise RequestParameterInvalidException( ERROR_INVALID_ELEMENTS_SPECIFICATION )
        if not collection_type:
            raise RequestParameterInvalidException( ERROR_NO_COLLECTION_TYPE )
        collection_type_description = self.collection_type_descriptions.for_collection_type( collection_type )
        # If we have elements, this is an internal request, don't need to load
        # objects from identifiers.
        if elements is None:
            if collection_type_description.has_subcollections( ):
                # Nested collection - recursively create collections and update identifiers.
                self.__recursively_create_collections( trans, element_identifiers )
            new_collection = False
            for element_identifier in element_identifiers:
                if element_identifier.get("src") == "new_collection" and element_identifier.get('collection_type') == '':
                    new_collection = True
                    elements = self.__load_elements(trans, element_identifier['element_identifiers'])
            if not new_collection:
                elements = self.__load_elements( trans, element_identifiers )
        # else if elements is set, it better be an ordered dict!

        if elements is not self.ELEMENTS_UNINITIALIZED:
            type_plugin = collection_type_description.rank_type_plugin()
            dataset_collection = builder.build_collection( type_plugin, elements )
        else:
            dataset_collection = model.DatasetCollection( populated=False )
        dataset_collection.collection_type = collection_type
        return dataset_collection

    def set_collection_elements( self, dataset_collection, dataset_instances ):
        if dataset_collection.populated:
            raise Exception("Cannot reset elements of an already populated dataset collection.")

        collection_type = dataset_collection.collection_type
        collection_type_description = self.collection_type_descriptions.for_collection_type( collection_type )
        type_plugin = collection_type_description.rank_type_plugin()
        builder.set_collection_elements( dataset_collection, type_plugin, dataset_instances )
        dataset_collection.mark_as_populated()

        return dataset_collection

    def collection_builder_for( self, dataset_collection ):
        collection_type = dataset_collection.collection_type
        collection_type_description = self.collection_type_descriptions.for_collection_type( collection_type )
        return builder.BoundCollectionBuilder( dataset_collection, collection_type_description )

    def delete( self, trans, instance_type, id ):
        dataset_collection_instance = self.get_dataset_collection_instance( trans, instance_type, id, check_ownership=True )
        dataset_collection_instance.deleted = True
        trans.sa_session.add( dataset_collection_instance )
        trans.sa_session.flush( )

    def update( self, trans, instance_type, id, payload ):
        dataset_collection_instance = self.get_dataset_collection_instance( trans, instance_type, id, check_ownership=True )
        if trans.user is None:
            anon_allowed_payload = {}
            if 'deleted' in payload:
                anon_allowed_payload[ 'deleted' ] = payload[ 'deleted' ]
            if 'visible' in payload:
                anon_allowed_payload[ 'visible' ] = payload[ 'visible' ]
            payload = self._validate_and_parse_update_payload( anon_allowed_payload )
        else:
            payload = self._validate_and_parse_update_payload( payload )
        changed = self._set_from_dict( trans, dataset_collection_instance, payload )
        return changed

    def copy(
        self,
        trans,
        parent,
        # PRECONDITION: security checks on ability to add to parent
        # occurred during load.
        source,
        encoded_source_id,
    ):
        assert source == "hdca"  # for now
        source_hdca = self.__get_history_collection_instance( trans, encoded_source_id )
        new_hdca = source_hdca.copy()
        parent.add_dataset_collection( new_hdca )
        trans.sa_session.add( new_hdca )
        trans.sa_session.flush()
        return new_hdca

    def _set_from_dict( self, trans, dataset_collection_instance, new_data ):
        # send what we can down into the model
        changed = dataset_collection_instance.set_from_dict( new_data )
        # the rest (often involving the trans) - do here
        if 'annotation' in new_data.keys() and trans.get_user():
            dataset_collection_instance.add_item_annotation( trans.sa_session, trans.get_user(), dataset_collection_instance, new_data[ 'annotation' ] )
            changed[ 'annotation' ] = new_data[ 'annotation' ]
        if 'tags' in new_data.keys() and trans.get_user():
            self.tag_manager.set_tags_from_list( trans.get_user(), dataset_collection_instance, new_data[ 'tags' ] )

        if changed.keys():
            trans.sa_session.flush()

        return changed

    def _validate_and_parse_update_payload( self, payload ):
        validated_payload = {}
        for key, val in payload.items():
            if val is None:
                continue
            if key in ( 'name' ):
                val = validation.validate_and_sanitize_basestring( key, val )
                validated_payload[ key ] = val
            if key in ( 'deleted', 'visible' ):
                validated_payload[ key ] = validation.validate_boolean( key, val )
            elif key == 'tags':
                validated_payload[ key ] = validation.validate_and_sanitize_basestring_list( key, val )
        return validated_payload

    def history_dataset_collections(self, history, query):
        collections = history.active_dataset_collections
        collections = filter( query.direct_match, collections )
        return collections

    def __persist( self, dataset_collection_instance ):
        context = self.model.context
        context.add( dataset_collection_instance )
        context.flush()
        return dataset_collection_instance

    def __recursively_create_collections( self, trans, element_identifiers ):
        for index, element_identifier in enumerate( element_identifiers ):
            try:
                if not element_identifier[ "src" ] == "new_collection":
                    # not a new collection, keep moving...
                    continue
            except KeyError:
                # Not a dictionary, just an id of an HDA - move along.
                continue

            # element identifier is a dict with src new_collection...
            collection_type = element_identifier.get( "collection_type", None )
            collection = self.create_dataset_collection(
                trans=trans,
                collection_type=collection_type,
                element_identifiers=element_identifier[ "element_identifiers" ],
            )
            element_identifier[ "__object__" ] = collection

        return element_identifiers

    def __load_elements( self, trans, element_identifiers ):
        elements = odict.odict()
        for element_identifier in element_identifiers:
            elements[ element_identifier[ "name" ] ] = self.__load_element( trans, element_identifier )
        return elements

    def __load_element( self, trans, element_identifier ):
        # if not isinstance( element_identifier, dict ):
        #    # Is allowing this to just be the id of an hda too clever? Somewhat
        #    # consistent with other API methods though.
        #    element_identifier = dict( src='hda', id=str( element_identifier ) )

        # Previously created collection already found in request, just pass
        # through as is.
        if "__object__" in element_identifier:
            the_object = element_identifier[ "__object__" ]
            if the_object is not None and the_object.id:
                context = self.model.context
                if the_object not in context:
                    the_object = context.query( type(the_object) ).get(the_object.id)
            return the_object

        # dateset_identifier is dict {src=hda|ldda|hdca|new_collection, id=<encoded_id>}
        try:
            src_type = element_identifier.get( 'src', 'hda' )
        except AttributeError:
            raise MessageException( "Dataset collection element definition (%s) not dictionary-like." % element_identifier )
        encoded_id = element_identifier.get( 'id', None )
        if not src_type or not encoded_id:
            message_template = "Problem decoding element identifier %s - must contain a 'src' and a 'id'."
            message = message_template % element_identifier
            raise RequestParameterInvalidException( message )

        if src_type == 'hda':
            decoded_id = int( trans.app.security.decode_id( encoded_id ) )
            element = self.hda_manager.get_accessible( decoded_id, trans.user )
        elif src_type == 'ldda':
            element = self.ldda_manager.get( trans, encoded_id )
        elif src_type == 'hdca':
            # TODO: Option to copy? Force copy? Copy or allow if not owned?
            element = self.__get_history_collection_instance( trans, encoded_id ).collection
        # TODO: ldca.
        else:
            raise RequestParameterInvalidException( "Unknown src_type parameter supplied '%s'." % src_type )
        return element

    def match_collections( self, collections_to_match ):
        """
        May seem odd to place it here, but planning to grow sophistication and
        get plugin types involved so it will likely make sense in the future.
        """
        return MatchingCollections.for_collections( collections_to_match, self.collection_type_descriptions )

    def get_dataset_collection_instance( self, trans, instance_type, id, **kwds ):
        """
        """
        if instance_type == "history":
            return self.__get_history_collection_instance( trans, id, **kwds )
        elif instance_type == "library":
            return self.__get_library_collection_instance( trans, id, **kwds )

    def get_dataset_collection( self, trans, encoded_id ):
        collection_id = int( trans.app.security.decode_id( encoded_id ) )
        collection = trans.sa_session.query( trans.app.model.DatasetCollection ).get( collection_id )
        return collection

    def __get_history_collection_instance( self, trans, id, check_ownership=False, check_accessible=True ):
        instance_id = int( trans.app.security.decode_id( id ) )
        collection_instance = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( instance_id )
        if check_ownership:
            self.history_manager.error_unless_owner( collection_instance.history, trans.user, current_history=trans.history )
        if check_accessible:
            self.history_manager.error_unless_accessible( collection_instance.history, trans.user, current_history=trans.history )
        return collection_instance

    def __get_library_collection_instance( self, trans, id, check_ownership=False, check_accessible=True ):
        if check_ownership:
            raise NotImplemented( "Functionality (getting library dataset collection with ownership check) unimplemented." )
        instance_id = int( trans.security.decode_id( id ) )
        collection_instance = trans.sa_session.query( trans.app.model.LibraryDatasetCollectionAssociation ).get( instance_id )
        if check_accessible:
            if not trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), collection_instance, trans.user ):
                raise ItemAccessibilityException( "LibraryDatasetCollectionAssociation is not accessible to the current user", type='error' )
        return collection_instance
