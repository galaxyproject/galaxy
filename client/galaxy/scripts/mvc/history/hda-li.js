define([
    "mvc/dataset/dataset-li",
    "mvc/base-mvc",
    "utils/localization"
], function( DATASET_LI, BASE_MVC, _l ){

'use strict';

//==============================================================================
var _super = DATASET_LI.DatasetListItemView;
/** @class Read only view for HistoryDatasetAssociation.
 *      Since there are no controls on the HDAView to hide the dataset,
 *      the primary thing this class does (currently) is override templates
 *      to render the HID.
 */
var HDAListItemView = _super.extend(
/** @lends HDAListItemView.prototype */{

    className   : _super.prototype.className + " history-content",

    initialize : function( attributes, options ){
        _super.prototype.initialize.call( this, attributes, options );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDAListItemView(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
HDAListItemView.prototype.templates = (function(){

    var titleBarTemplate = BASE_MVC.wrapTemplate([
        // adding the hid display to the title
        '<div class="title-bar clear" tabindex="0">',
            '<span class="state-icon"></span>',
            '<div class="title">',
                //TODO: remove whitespace and use margin-right
                '<span class="hid"><%- dataset.hid %></span> ',
                '<span class="name"><%- dataset.name %></span>',
            '</div>',
        '</div>'
    ], 'dataset' );

    var warnings = _.extend( {}, _super.prototype.templates.warnings, {
        hidden : BASE_MVC.wrapTemplate([
            // add a warning when hidden
            '<% if( !dataset.visible ){ %>',
                '<div class="hidden-msg warningmessagesmall">',
                    _l( 'This dataset has been hidden' ),
                '</div>',
            '<% } %>'
        ], 'dataset' )
    });

    return _.extend( {}, _super.prototype.templates, {
        titleBar : titleBarTemplate,
        warnings : warnings
    });
}());



//==============================================================================
    return {
        HDAListItemView  : HDAListItemView
    };
});
