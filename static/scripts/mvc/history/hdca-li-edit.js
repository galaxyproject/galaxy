define([
    "mvc/dataset/states",
    "mvc/history/hdca-li",
    "utils/localization"
], function( STATES, HDCA_LI, _l ){
//==============================================================================
var _super = HDCA_LI.HDCAListItemView;
/** @class Editing view for HistoryDatasetCollectionAssociation.
 */
var HDCAListItemEdit = _super.extend(
/** @lends HDCAListItemEdit.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    // ......................................................................... delete
    /** In this override, add the delete button. */
    _renderPrimaryActions : function(){
        this.log( this + '._renderPrimaryActions' );
        // render the display, edit attr and delete icon-buttons
        return _super.prototype._renderPrimaryActions.call( this )
            .concat([
                this._renderDeleteButton()
            ]);
    },

    /** Render icon-button to delete this collection. */
    _renderDeleteButton : function(){
        var self = this,
            deleted = this.model.get( 'deleted' );
        return faIconButton({
            title       : deleted? _l( 'Dataset collection is already deleted' ): _l( 'Delete' ),
            classes     : 'delete-btn',
            faIcon      : 'fa-times',
            disabled    : deleted,
            onclick     : function() {
                // ...bler... tooltips being left behind in DOM (hover out never called on deletion)
                self.$el.find( '.icon-btn.delete-btn' ).trigger( 'mouseout' );
                self.model[ 'delete' ]();
            }
        });
    },

    // ......................................................................... misc
    /** string rep */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDCAListItemEdit(' + modelString + ')';
    }
});

//==============================================================================
    return {
        HDCAListItemEdit : HDCAListItemEdit
    };
});
