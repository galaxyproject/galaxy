define([
    "mvc/history/history-content-base",
    "mvc/collection/collection-model",
    "utils/localization"
], function( HISTORY_CONTENT, DC_MODEL, _l ){
//==============================================================================
var hcontentMixin = HISTORY_CONTENT.HistoryContentMixin,
/** @class Backbone model for (generic) Dataset Collection within a History.
 *  @constructs
 */
    HistoryDatasetCollection = DC_MODEL.DatasetCollection.extend( hcontentMixin );


//NOTE: the following prototypes may not be necessary - but I wanted to specifiy
//  them (for now) and allow for the possibility of unique functionality
//==============================================================================
var ListDC = DC_MODEL.ListDatasetCollection,
/** @class Backbone model for List Dataset Collection within a History.
 *  @constructs
 */
    HistoryListDatasetCollection = ListDC.extend( hcontentMixin ).extend(
/** @lends HistoryListDatasetCollection.prototype */{

    initialize : function( model, options ){
        ListDC.prototype.initialize.call( this, model, options );
        hcontentMixin.initialize.call( this, model, options );
        //TODO: in lieu of any state info for collections, show as 'ok'
        this.set( 'state', 'ok', { silent: true });
    },

    /** String representation. */
    toString : function(){
         return ([ 'HistoryListDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
var PairDC = DC_MODEL.PairDatasetCollection,
/** @class Backbone model for Pair Dataset Collection within a History.
 *  @constructs
 */
    HistoryPairDatasetCollection = PairDC.extend( hcontentMixin ).extend(
/** @lends HistoryPairDatasetCollection.prototype */{

    initialize : function( model, options ){
        PairDC.prototype.initialize.call( this, model, options );
        hcontentMixin.initialize.call( this, model, options );
        //TODO: in lieu of any state info for collections, show as 'ok'
        this.set( 'state', 'ok', { silent: true });
    },

    /** String representation. */
    toString : function(){
         return ([ 'HistoryPairDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
var ListPairedDC = DC_MODEL.ListPairedDatasetCollection,
/** @class Backbone model for List of Pairs Dataset Collection within a History.
 *  @constructs
 */
    HistoryListPairedDatasetCollection = ListPairedDC.extend( hcontentMixin ).extend(
/** @lends HistoryListPairedDatasetCollection.prototype */{

    initialize : function( model, options ){
        ListPairedDC.prototype.initialize.call( this, model, options );
        hcontentMixin.initialize.call( this, model, options );
        //TODO: in lieu of any state info for collections, show as 'ok'
        this.set( 'state', 'ok', { silent: true });
    },

    /** String representation. */
    toString : function(){
         return ([ 'HistoryListPairedDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
    return {
        HistoryDatasetCollection            : HistoryDatasetCollection,
        HistoryListDatasetCollection        : HistoryListDatasetCollection,
        HistoryPairDatasetCollection        : HistoryPairDatasetCollection,
        HistoryListPairedDatasetCollection  : HistoryListPairedDatasetCollection
    };
});
