define([
    "mvc/dataset/dataset-model",
    "mvc/history/history-content-model",
    "mvc/base-mvc",
    "utils/localization"
], function( DATASET, HISTORY_CONTENT, BASE_MVC, _l ){
//==============================================================================
var _super = DATASET.DatasetAssociation,
    hcontentMixin = HISTORY_CONTENT.HistoryContentMixin;
/** @class (HDA) model for a Galaxy dataset contained in and related to a history.
 */
var HistoryDatasetAssociation = _super.extend( BASE_MVC.mixin( hcontentMixin,
/** @lends HistoryDatasetAssociation.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    // because all objects have constructors (as this hashmap would even if this next line wasn't present)
    //  the constructor in hcontentMixin won't be attached by BASE_MVC.mixin to this model
    //  - re-apply manually it now
    /** call the mixin constructor */
    constructor : function( attrs, options ){
        hcontentMixin.constructor.call( this, attrs, options );
    },
    
    /** default attributes for a model */
    defaults : _.extend( {}, _super.prototype.defaults, hcontentMixin.defaults, {
        model_class         : 'HistoryDatasetAssociation'
    }),

    /** Set up the model, determine if accessible, bind listeners
     */
    initialize : function( attributes, options ){
        _super.prototype.initialize.call( this, attributes, options );
        hcontentMixin.initialize.call( this, attributes, options );
    },

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId = this.get( 'hid' ) + ' :"' + this.get( 'name' ) + '",' + nameAndId;
        }
        return 'HDA(' + nameAndId + ')';
    }
}));

//==============================================================================
    return {
        HistoryDatasetAssociation   : HistoryDatasetAssociation
    };
});
