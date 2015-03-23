define([
    "mvc/dataset/states",
    "mvc/ui/error-modal",
    "utils/localization"
], function( STATES, errorModal, _l ){
/*==============================================================================

==============================================================================*/
function validElements( collection ){
    var elements = collection.toJSON().filter( function( content ){
        return content.history_content_type === 'dataset'
            && content.state === STATES.OK;
    });
    return elements;
}

var noValidElementsMessage = 'No valid datasets were selected';

function noValidElementsErrorModal(){
    errorModal(
        'Use the checkboxes at the left of the dataset names to select them. ' +
        'Selected datasets should be error-free and should have completed running.',
        noValidElementsMessage
    );
}

function createListHDCA( collection ){
    var name = 'New Dataset List',
        elementIdentifiers = validElements( collection ).map( function( element ){
            // TODO: Handle duplicate names.
            return {
                id      : element.id,
                name    : element.name,
                //TODO: this allows for list:list even if the filter above does not - reconcile
                src     : ( element.history_content_type === 'dataset'? 'hda' : 'hdca' )
            }
        });
    if( !elementIdentifiers.length ){
        noValidElementsErrorModal();
        return jQuery.Deferred().reject( noValidElementsMessage );
    }
    return collection.createHDCA( elementIdentifiers, 'list', name );
}

//==============================================================================
    return {
        validElements               : validElements,
        noValidElementsMessage      : noValidElementsMessage,
        noValidElementsErrorModal   : noValidElementsErrorModal,
        createListHDCA              : createListHDCA
    };
});
