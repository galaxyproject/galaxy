define([
    "mvc/dataset/dataset-li-edit",
    "mvc/history/hda-li",
    "mvc/base-mvc",
    "utils/localization"
], function( DATASET_LI_EDIT, HDA_LI, BASE_MVC, _l ){
//==============================================================================
var _super = DATASET_LI_EDIT.DatasetListItemEdit;
/** @class Editing view for HistoryDatasetAssociation.
 */
var HDAListItemEdit = _super.extend(
/** @lends HDAListItemEdit.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    className   : _super.prototype.className + " history-content",

    // ......................................................................... events
    /** event map */
    events : _.extend( _.clone( _super.prototype.events ), {
        'click .unhide-link' : function( ev ){ this.model.unhide(); return false; }
    }),

    // ......................................................................... misc
    /** string rep */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDAListItemEdit(' + modelString + ')';
    }
});


// ............................................................................ TEMPLATES
/** underscore templates */
HDAListItemEdit.prototype.templates = (function(){
//TODO: move to require text! plugin

    var warnings = _.extend( {}, _super.prototype.templates.warnings, {
        hidden : BASE_MVC.wrapTemplate([
            '<% if( !dataset.visible ){ %>',
                // add a link to unhide a dataset
                '<div class="hidden-msg warningmessagesmall">',
                    _l( 'This dataset has been hidden' ),
                    '<br /><a class="unhide-link" a href="javascript:void(0);">', _l( 'Unhide it' ), '</a>',
                '</div>',
            '<% } %>'
        ], 'dataset' )
    });

    return _.extend( {}, _super.prototype.templates, {
        //NOTE: *steal* the HDAListItemView titleBar
        titleBar : HDA_LI.HDAListItemView.prototype.templates.titleBar,
        warnings : warnings
    });
}());


//==============================================================================
    return {
        HDAListItemEdit  : HDAListItemEdit
    };
});
