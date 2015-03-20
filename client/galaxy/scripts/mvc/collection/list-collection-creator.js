define([
    "mvc/collection/collection-model",
    "utils/localization"
], function( DC_MODEL, _l ){
/*==============================================================================
==============================================================================*/
function createListCollection( collection ){
    //TODO: filter out non-datasets, non-ready
    //TODO: fail if no valid elements remain
    //return jQuery.Deferred().reject( _l( 'No valid datasets to add' ) );
    var name = 'New Dataset List',
        elementIdentifiers = collection.toJSON().map( function( element ){
            // TODO: Handle duplicate names.
            return {
                id      : element.id,
                name    : element.name,
                src     : ( element.history_content_type === 'dataset'? 'hda' : 'hdca' )
            }
        });
    return collection.createHDCA( elementIdentifiers, 'list', name );
}

//==============================================================================
    return {
        createListCollection : createListCollection
    };
});
