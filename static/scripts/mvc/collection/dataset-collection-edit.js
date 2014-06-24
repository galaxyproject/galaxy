define([
    "mvc/dataset/hda-model",
    "mvc/collection/dataset-collection-base",
], function( hdaModel, datasetCollectionBase ){
//==============================================================================
/** @class Editing view for HistoryDatasetCollectionAssociation.
 *  @name DatasetCollectionEditView
 *
 *  @augments DatasetCollectionBaseView
 *  @constructs
 */
var DatasetCollectionEditView = datasetCollectionBase.DatasetCollectionBaseView.extend( {

    initialize  : function( attributes ){
        datasetCollectionBase.DatasetCollectionBaseView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... edit attr, delete
    /** Render icon-button group for the common, most easily accessed actions.
     *      Overrides _render_titleButtons to include editing related buttons.
     *  @see DatasetCollectionBaseView#_render_titleButtons
     *  @returns {jQuery} rendered DOM
     */
    _render_titleButtons : function(){
        // render the display, edit attr and delete icon-buttons
        return datasetCollectionBase.DatasetCollectionBaseView.prototype._render_titleButtons.call( this ).concat([
            this._render_deleteButton()
        ]);
    },

    /** Render icon-button to delete this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_deleteButton : function(){
        // don't show delete if...
        if( ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NEW )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            return null;
        }
        
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
        if( this.model.get( 'deleted' ) ){
            deleteBtnData = {
                title       : _l( 'Dataset collection is already deleted' ),
                disabled    : true
            };
        }
        deleteBtnData.faIcon = 'fa-times';
        return faIconButton( deleteBtnData );
    }

});

//==============================================================================
return {
    DatasetCollectionEditView  : DatasetCollectionEditView
};

});
