define([
    "mvc/dataset/states",
    "mvc/collection/collection-li",
    "mvc/collection/collection-view",
    "mvc/base-mvc",
    "utils/localization"
], function( STATES, DC_LI, DC_VIEW, BASE_MVC, _l ){

'use strict';

//==============================================================================
var _super = DC_LI.DCListItemView;
/** @class Read only view for HistoryDatasetCollectionAssociation (a dataset collection inside a history).
 */
var HDCAListItemView = _super.extend(
/** @lends HDCAListItemView.prototype */{

    className   : _super.prototype.className + " history-content",

    /** event listeners */
    _setUpListeners : function(){
        _super.prototype._setUpListeners.call( this );

        this.listenTo( this.model, {
            'change:populated change:visible' : function( model, options ){ this.render(); },
        });
    },

    /** Override to provide the proper collections panels as the foldout */
    _getFoldoutPanelClass : function(){
        switch( this.model.get( 'collection_type' ) ){
            case 'list':
                return DC_VIEW.ListCollectionView;
            case 'paired':
                return DC_VIEW.PairCollectionView;
            case 'list:paired':
                return DC_VIEW.ListOfPairsCollectionView;
            case 'list:list':
                return DC_VIEW.ListOfListsCollectionView;
        }
        throw new TypeError( 'Uknown collection_type: ' + this.model.get( 'collection_type' ) );
    },

    /** In this override, add the state as a class for use with state-based CSS */
    _swapNewRender : function( $newRender ){
        _super.prototype._swapNewRender.call( this, $newRender );
        //TODO: model currently has no state
        var state = !this.model.get( 'populated' ) ? STATES.RUNNING : STATES.OK;
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

    var warnings = _.extend( {}, _super.prototype.templates.warnings, {
        hidden : BASE_MVC.wrapTemplate([
            // add a warning when hidden
            '<% if( !collection.visible ){ %>',
                '<div class="hidden-msg warningmessagesmall">',
                    _l( 'This collection has been hidden' ),
                '</div>',
            '<% } %>'
        ], 'collection' )
    });

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
        warnings : warnings,
        titleBar : titleBarTemplate
    });
}());


//==============================================================================
    return {
        HDCAListItemView : HDCAListItemView
    };
});
