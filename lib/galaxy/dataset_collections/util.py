from galaxy import exceptions
from galaxy import web
from galaxy import model


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


def dictify_dataset_collection_instance( dataset_colleciton_instance, parent, security, view="element" ):
    dict_value = dataset_colleciton_instance.to_dict( view=view )
    encoded_id = security.encode_id( dataset_colleciton_instance.id )
    if isinstance( parent, model.History ):
        encoded_history_id = security.encode_id( parent.id )
        dict_value[ 'url' ] = web.url_for( 'history_content', history_id=encoded_history_id, id=encoded_id, type="dataset_collection" )
    elif isinstance( parent, model.LibraryFolder ):
        encoded_library_id = security.encode_id( parent.library.id )
        encoded_folder_id = security.encode_id( parent.id )
        # TODO: Work in progress - this end-point is not right yet...
        dict_value[ 'url' ] = web.url_for( 'library_content', library_id=encoded_library_id, id=encoded_id, folder_id=encoded_folder_id )
    if view == "element":
        dict_value[ 'elements' ] = map( dictify_element, dataset_colleciton_instance.collection.elements )
    security.encode_dict_ids( dict_value )  # TODO: Use Kyle's recusrive formulation of this.
    return dict_value


def dictify_element( element ):
    dictified = element.to_dict( view="element" )
    object_detials = element.element_object.to_dict()
    if element.child_collection:
        # Recursively yield elements for each nested collection...
        object_detials[ "elements" ] = map( dictify_element, element.child_collection.elements )

    dictified[ "object" ] = object_detials
    return dictified

__all__ = [ api_payload_to_create_params, dictify_dataset_collection_instance ]
