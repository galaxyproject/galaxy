import logging

from galaxy import exceptions, model, web

log = logging.getLogger( __name__ )

ERROR_MESSAGE_UNKNOWN_SRC = "Unknown dataset source (src) %s."
ERROR_MESSAGE_NO_NESTED_IDENTIFIERS = "Dataset source new_collection requires nested element_identifiers for new collection."
ERROR_MESSAGE_NO_NAME = "Cannot load invalid dataset identifier - missing name - %s"
ERROR_MESSAGE_NO_COLLECTION_TYPE = "No collection_type define for nested collection %s."
ERROR_MESSAGE_INVALID_PARAMETER_FOUND = "Found invalid parameter %s in element identifier description %s."
ERROR_MESSAGE_DUPLICATED_IDENTIFIER_FOUND = "Found duplicated element identifier name %s."


def api_payload_to_create_params( payload ):
    """
    Cleanup API payload to pass into dataset_collections.
    """
    required_parameters = [ "collection_type", "element_identifiers" ]
    missing_parameters = [ p for p in required_parameters if p not in payload ]
    if missing_parameters:
        message = "Missing required parameters %s" % missing_parameters
        raise exceptions.ObjectAttributeMissingException( message )

    params = dict(
        collection_type=payload.get( "collection_type" ),
        element_identifiers=payload.get( "element_identifiers" ),
        name=payload.get( "name", None ),
    )
    return params


def validate_input_element_identifiers( element_identifiers ):
    """ Scan through the list of element identifiers supplied by the API consumer
    and verify the structure is valid.
    """
    log.debug( "Validating %d element identifiers for collection creation." % len( element_identifiers ) )
    identifier_names = set()
    for element_identifier in element_identifiers:
        if "__object__" in element_identifier:
            message = ERROR_MESSAGE_INVALID_PARAMETER_FOUND % ( "__object__", element_identifier )
            raise exceptions.RequestParameterInvalidException( message )
        if "name" not in element_identifier:
            message = ERROR_MESSAGE_NO_NAME % element_identifier
            raise exceptions.RequestParameterInvalidException( message )
        name = element_identifier[ "name" ]
        if name in identifier_names:
            message = ERROR_MESSAGE_DUPLICATED_IDENTIFIER_FOUND % name
            raise exceptions.RequestParameterInvalidException( message )
        else:
            identifier_names.add( name )
        src = element_identifier.get( "src", "hda" )
        if src not in [ "hda", "hdca", "ldda", "new_collection" ]:
            message = ERROR_MESSAGE_UNKNOWN_SRC % src
            raise exceptions.RequestParameterInvalidException( message )
        if src == "new_collection":
            if "element_identifiers" not in element_identifier:
                message = ERROR_MESSAGE_NO_NESTED_IDENTIFIERS
                raise exceptions.RequestParameterInvalidException( ERROR_MESSAGE_NO_NESTED_IDENTIFIERS )
            if "collection_type" not in element_identifier:
                message = ERROR_MESSAGE_NO_COLLECTION_TYPE % element_identifier
                raise exceptions.RequestParameterInvalidException( message )
            validate_input_element_identifiers( element_identifier[ "element_identifiers" ] )


def dictify_dataset_collection_instance( dataset_collection_instance, parent, security, view="element" ):
    dict_value = dataset_collection_instance.to_dict( view=view )
    encoded_id = security.encode_id( dataset_collection_instance.id )
    if isinstance( parent, model.History ):
        encoded_history_id = security.encode_id( parent.id )
        dict_value[ 'url' ] = web.url_for( 'history_content_typed', history_id=encoded_history_id, id=encoded_id, type="dataset_collection" )
    elif isinstance( parent, model.LibraryFolder ):
        encoded_library_id = security.encode_id( parent.library.id )
        encoded_folder_id = security.encode_id( parent.id )
        # TODO: Work in progress - this end-point is not right yet...
        dict_value[ 'url' ] = web.url_for( 'library_content', library_id=encoded_library_id, id=encoded_id, folder_id=encoded_folder_id )
    if view == "element":
        collection = dataset_collection_instance.collection
        dict_value[ 'elements' ] = [ dictify_element(_) for _ in collection.elements ]
        dict_value[ 'populated' ] = collection.populated
    security.encode_all_ids( dict_value, recursive=True )  # TODO: Use Kyle's recursive formulation of this.
    return dict_value


def dictify_element( element ):
    dictified = element.to_dict( view="element" )
    object_detials = element.element_object.to_dict()
    if element.child_collection:
        # Recursively yield elements for each nested collection...
        child_collection = element.child_collection
        object_detials[ "elements" ] = [ dictify_element(_) for _ in child_collection.elements ]
        object_detials[ "populated" ] = child_collection.populated

    dictified[ "object" ] = object_detials
    return dictified


__all__ = ( 'api_payload_to_create_params', 'dictify_dataset_collection_instance' )
