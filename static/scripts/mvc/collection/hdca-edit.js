define([
    "mvc/dataset/states",
    "mvc/collection/hdca-base",
    "utils/localization"
], function( STATES, HDCA_BASE, _l ){
//==============================================================================
var _super = HDCA_BASE.HDCABaseView;
/** @class Editing view for HistoryDatasetCollectionAssociation.
 *  @name DatasetCollectionEditView
 *
 *  @augments HDCABaseView
 *  @constructs
 */
var HDCAEditView = _super.extend({

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    initialize  : function( attributes ){
        _super.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... edit attr, delete
    /** Render icon-button group for the common, most easily accessed actions.
     *      Overrides _render_primaryActions to include editing related buttons.
     *  @returns {jQuery} rendered DOM
     */
    _render_primaryActions : function(){
        this.log( this + '._render_primaryActions' );
        // render the display, edit attr and delete icon-buttons
        return _super.prototype._render_primaryActions.call( this )
            .concat([
                this._render_deleteButton()
            ]);
    },

    /** Render icon-button to delete this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_deleteButton : function(){
        var self = this,
            deleteBtnData = {
                title       : _l( 'Delete' ),
                classes     : 'dataset-delete',
                onclick     : function() {
                    // ...bler... tooltips being left behind in DOM (hover out never called on deletion)
                    self.$el.find( '.icon-btn.dataset-delete' ).trigger( 'mouseout' );
                    self.model[ 'delete' ]();
                }
        };
        if( self.model.get( 'deleted' ) ){
            deleteBtnData = {
                title       : _l( 'Dataset collection is already deleted' ),
                disabled    : true
            };
        }
        deleteBtnData.faIcon = 'fa-times';
        return faIconButton( deleteBtnData );
    },

    // ......................................................................... misc
    /** string rep */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDCAEditView(' + modelString + ')';
    }
});

//==============================================================================
    return {
        HDCAEditView : HDCAEditView
    };
});
