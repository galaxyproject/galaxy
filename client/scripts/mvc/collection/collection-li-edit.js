define([
    "mvc/collection/collection-li",
    "utils/localization"
], function( DC_LI, _l ){
//==============================================================================
/*

NOTE: not much going on here. Until we find out what operations a user will need
    to perform on their own DC's, we'll leave this empty.

*/
//==============================================================================
var _super = DC_LI.DCListItemView;
/** @class Editing view for DatasetCollectionElement.
 */
var DCEListItemEdit = _super.extend(
/** @lends DCEListItemEdit.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    // ......................................................................... misc
    /** string rep */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCEListItemEdit(' + modelString + ')';
    }
});

//==============================================================================
    return {
        DCEListItemEdit : DCEListItemEdit
    };
});
