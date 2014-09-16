define([
    "mvc/dataset/states",
    "mvc/collection/collection-li",
    "mvc/collection/collection-panel",
    "mvc/base-mvc",
    "utils/localization"
], function( STATES, DC_LI, DC_PANEL, BASE_MVC, _l ){
/* global Backbone */
//==============================================================================
var _super = DC_LI.DCListItemView;
/** @class Read only view for HistoryDatasetCollectionAssociation (a dataset collection inside a history).
 */
var HDCAListItemView = _super.extend(
/** @lends HDCAListItemView.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    className   : _super.prototype.className + " history-content",

    _getFoldoutPanelClass : function(){
        switch( this.model.get( 'collection_type' ) ){
            case 'list':
                return DC_PANEL.ListCollectionPanel;
            case 'paired':
                return DC_PANEL.PairCollectionPanel;
            case 'list:paired':
                return DC_PANEL.ListOfPairsCollectionPanel;
        }
        throw new TypeError( 'Uknown collection_type: ' + this.model.get( 'collection_type' ) );
    },

    /** In this override, add the state as a class for use with state-based CSS */
    _swapNewRender : function( $newRender ){
        _super.prototype._swapNewRender.call( this, $newRender );
//TODO: model currently has no state
        var state = this.model.get( 'state' ) || STATES.OK;
        //if( this.model.has( 'state' ) ){
        this.$el.addClass( 'state-' + state );
        //}
        return this.$el;
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDCAListItemView(' + modelString + ')';
    }
});

/** underscore templates */
HDCAListItemView.prototype.templates = (function(){

// could steal this from hda-base (or use mixed content)
    var titleBarTemplate = BASE_MVC.wrapTemplate([
        // adding the hid display to the title
        '<div class="title-bar clear" tabindex="0">',
            '<span class="state-icon"></span>',
            '<div class="title">',
                //TODO: remove whitespace and use margin-right
                '<span class="hid"><%- collection.hid %></span> ',
                '<span class="name"><%- collection.name %></span>',
            '</div>',
            '<div class="subtitle"></div>',
        '</div>'
    ], 'collection' );

    return _.extend( {}, _super.prototype.templates, {
        titleBar : titleBarTemplate
    });
}());


//==============================================================================
    return {
        HDCAListItemView : HDCAListItemView
    };
});
