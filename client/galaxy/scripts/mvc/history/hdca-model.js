define([
    "mvc/collection/collection-model",
    "mvc/history/history-content-model",
    "utils/localization"
], function( DC_MODEL, HISTORY_CONTENT, _l ){

'use strict';

/*==============================================================================

Models for DatasetCollections contained within a history.

TODO:
    these might be compactable to one class if some duplication with
    collection-model is used.

==============================================================================*/
var hcontentMixin = HISTORY_CONTENT.HistoryContentMixin,
    ListDC = DC_MODEL.ListDatasetCollection,
    PairDC = DC_MODEL.PairDatasetCollection,
    ListPairedDC = DC_MODEL.ListPairedDatasetCollection;

//==============================================================================
/** Override to post to contents route w/o id. */
function buildHDCASave( _super ){
    return function _save( attributes, options ){
        if( this.isNew() ){
            options = options || {};
            options.url = this.urlRoot + this.get( 'history_id' ) + '/contents';
            attributes = attributes || {};
            attributes.type = 'dataset_collection';
        }
        return _super.call( this, attributes, options );
    };
}


//==============================================================================
/** @class Backbone model for List Dataset Collection within a History.
 */
var HistoryListDatasetCollection = ListDC.extend( hcontentMixin ).extend(
/** @lends HistoryListDatasetCollection.prototype */{

    defaults : _.extend( _.clone( ListDC.prototype.defaults ), {
        history_content_type: 'dataset_collection',
        collection_type     : 'list',
        model_class         : 'HistoryDatasetCollectionAssociation'
    }),

    initialize : function( model, options ){
        ListDC.prototype.initialize.call( this, model, options );
        hcontentMixin.initialize.call( this, model, options );
    },

    /** Override to post to contents route w/o id. */
    save : buildHDCASave( ListDC.prototype.save ),

    /** String representation. */
    toString : function(){
         return ([ 'HistoryListDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
/** @class Backbone model for Pair Dataset Collection within a History.
 *  @constructs
 */
var HistoryPairDatasetCollection = PairDC.extend( hcontentMixin ).extend(
/** @lends HistoryPairDatasetCollection.prototype */{

    defaults : _.extend( _.clone( PairDC.prototype.defaults ), {
        history_content_type: 'dataset_collection',
        collection_type     : 'paired',
        model_class         : 'HistoryDatasetCollectionAssociation'
    }),

    initialize : function( model, options ){
        PairDC.prototype.initialize.call( this, model, options );
        hcontentMixin.initialize.call( this, model, options );
    },

    /** Override to post to contents route w/o id. */
    save : buildHDCASave( PairDC.prototype.save ),

    /** String representation. */
    toString : function(){
         return ([ 'HistoryPairDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
/** @class Backbone model for List of Pairs Dataset Collection within a History.
 *  @constructs
 */
var HistoryListPairedDatasetCollection = ListPairedDC.extend( hcontentMixin ).extend(
/** @lends HistoryListPairedDatasetCollection.prototype */{

    defaults : _.extend( _.clone( ListPairedDC.prototype.defaults ), {
        history_content_type: 'dataset_collection',
        collection_type     : 'list:paired',
        model_class         : 'HistoryDatasetCollectionAssociation'
    }),

    initialize : function( model, options ){
        ListPairedDC.prototype.initialize.call( this, model, options );
        hcontentMixin.initialize.call( this, model, options );
    },

    /** Override to post to contents route w/o id. */
    save : buildHDCASave( ListPairedDC.prototype.save ),

    /** String representation. */
    toString : function(){
         return ([ 'HistoryListPairedDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
    return {
        HistoryListDatasetCollection        : HistoryListDatasetCollection,
        HistoryPairDatasetCollection        : HistoryPairDatasetCollection,
        HistoryListPairedDatasetCollection  : HistoryListPairedDatasetCollection
    };
});
