define([
    "mvc/dataset/states",
    "mvc/collection/dataset-collection-base",
    "utils/localization"
], function( STATES, DC_BASE_VIEW, _l ){
//==============================================================================
var _super = DC_BASE_VIEW.DCBaseView;
/** @class Editing view for DatasetCollection.
 *  @name DatasetCollectionEditView
 *
 *  @augments DCBaseView
 *  @constructs
 */
var DCEditView = _super.extend({

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    initialize  : function( attributes ){
        _super.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... misc
    /** string rep */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCEditView(' + modelString + ')';
    }
});

//==============================================================================
    return {
        DCEditView : DCEditView
    };
});
