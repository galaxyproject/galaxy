define([
    "mvc/collection/list-collection-creator",
    "mvc/ui/error-modal",
    "utils/localization"
], function( LIST_COLLECTION_CREATOR, errorModal, _l ){

    function createPairHDCA( collection ){
        // currently: datasets in the ok state
        var elementsJSON = LIST_COLLECTION_CREATOR.validElements( collection );
        if( !elementsJSON.length ){
            LIST_COLLECTION_CREATOR.noValidElementsErrorModal();
            return jQuery.Deferred().reject( LIST_COLLECTION_CREATOR.noValidElementsMessage );
        }
        if( elementsJSON.length !== 2 ){
            errorModal(
                'When pairing datasets, select only two datasets: one forward and one reverse.',
                'Not a valid pair'
            );
            return jQuery.Deferred().reject( LIST_COLLECTION_CREATOR.noValidElementsMessage );
        }

        var name = 'New Dataset Pair',
            elementIdentifiers = [
                { name: "forward", src: "hda", id: elementsJSON[0].id },
                { name: "reverse", src: "hda", id: elementsJSON[1].id }
            ];
        return collection.createHDCA( elementIdentifiers, 'paired', name );
    }

    return {
        createPairHDCA : createPairHDCA
    };
});
