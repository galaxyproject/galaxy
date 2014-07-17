define([
    "mvc/history/history-content-base",
    "utils/localization"
], function( historyContent, _l ){
//==============================================================================
var HistoryDatasetCollectionAssociation = historyContent.HistoryContent.extend(
/** @lends HistoryDatasetCollectionAssociation.prototype */{
    /** default attributes for a model */
    defaults : {
        // parent (containing) history
        history_id          : null,
        // often used with tagging
        model_class         : 'HistoryDatasetCollectionAssociation',
        history_content_type : 'dataset_collection',
        hid                 : 0,

        id                  : null,
        name                : '(unnamed dataset collection)',
        // one of HistoryDatasetAssociation.STATES, calling them all 'ok' for now.
        state               : 'ok',

        accessible          : true,
        deleted             : false,
        visible             : true,

        purged              : false, // Purged doesn't make sense for collections - at least right now.

        tags                : [],
        annotation          : ''
    },
    urls : function(){
    },

    inReadyState : function(){
        return true; // TODO
    },

    // ........................................................................ search
    /** what attributes of an collection will be used in a text search */
    searchAttributes : [
        'name'
    ],

    /** our attr keys don't often match the labels we display to the user - so, when using
     *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
     *      following attr keys.
     */
    searchAliases : {
        title       : 'name'
        // TODO: Add tag...
    },

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId = this.get( 'hid' ) + ' :"' + this.get( 'name' ) + '",' + nameAndId;
        }
        return 'HDCA-' + this.get( 'collection_type' ) + '(' + nameAndId + ')';
    }
});


//==============================================================================
    return {
        HistoryDatasetCollectionAssociation : HistoryDatasetCollectionAssociation
    };
});
