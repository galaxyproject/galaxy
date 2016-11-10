define([
    "mvc/collection/collection-li",
    "mvc/dataset/dataset-li-edit",
    "mvc/base-mvc",
    "utils/localization"
], function( DC_LI, DATASET_LI_EDIT, BASE_MVC, _l ){

'use strict';
//==============================================================================
var DCListItemView = DC_LI.DCListItemView;
/** @class Edit view for DatasetCollection.
 */
var DCListItemEdit = DCListItemView.extend(
/** @lends DCListItemEdit.prototype */{

    /** override to add linkTarget */
    initialize : function( attributes ){
        DCListItemView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCListItemEdit(' + modelString + ')';
    }
});


//==============================================================================
var DCEListItemView = DC_LI.DCEListItemView;
/** @class Read only view for DatasetCollectionElement.
 */
var DCEListItemEdit = DCEListItemView.extend(
/** @lends DCEListItemEdit.prototype */{
//TODO: this might be expendable - compacted with HDAListItemView

    /** set up */
    initialize  : function( attributes ){
        DCEListItemView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCEListItemEdit(' + modelString + ')';
    }
});


//==============================================================================
// NOTE: this does not inherit from DatasetDCEListItemView as you would expect
//TODO: but should - if we can find something simpler than using diamond
/** @class Editable view for a DatasetCollectionElement that is also an DatasetAssociation
 *      (a dataset contained in a dataset collection).
 */
var DatasetDCEListItemEdit = DATASET_LI_EDIT.DatasetListItemEdit.extend(
/** @lends DatasetDCEListItemEdit.prototype */{

    /** set up */
    initialize  : function( attributes ){
        DATASET_LI_EDIT.DatasetListItemEdit.prototype.initialize.call( this, attributes );
    },

    // NOTE: this does not inherit from DatasetDCEListItemView - so we duplicate this here
    //TODO: fix
    /** In this override, only get details if in the ready state.
     *  Note: fetch with no 'change' event triggering to prevent automatic rendering.
     */
    _fetchModelDetails : function(){
        var view = this;
        if( view.model.inReadyState() && !view.model.hasDetails() ){
            return view.model.fetch({ silent: true });
        }
        return jQuery.when();
    },

    /** Override to remove delete button */
    _renderDeleteButton : function(){
        return null;
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DatasetDCEListItemEdit(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
DatasetDCEListItemEdit.prototype.templates = (function(){

    return _.extend( {}, DATASET_LI_EDIT.DatasetListItemEdit.prototype.templates, {
        titleBar : DC_LI.DatasetDCEListItemView.prototype.templates.titleBar
    });
}());


//==============================================================================
/** @class Read only view for a DatasetCollectionElement that is also a DatasetCollection
 *      (a nested DC).
 */
var NestedDCDCEListItemEdit = DC_LI.NestedDCDCEListItemView.extend(
/** @lends NestedDCDCEListItemEdit.prototype */{

    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'NestedDCDCEListItemEdit(' + modelString + ')';
    }
});


//==============================================================================
    return {
        DCListItemEdit          : DCListItemEdit,
        DCEListItemEdit         : DCEListItemEdit,
        DatasetDCEListItemEdit  : DatasetDCEListItemEdit,
        NestedDCDCEListItemEdit : NestedDCDCEListItemEdit
    };
});
