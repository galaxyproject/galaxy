define([
    "mvc/collection/collection-view",
    "mvc/collection/collection-model",
    "mvc/collection/collection-li-edit",
    "mvc/base-mvc",
    "utils/localization",
    "ui/editable-text",
], function( DC_VIEW, DC_MODEL, DC_EDIT, BASE_MVC, _l ){

'use strict';
/* =============================================================================
TODO:

============================================================================= */
/** @class editable View/Controller for a dataset collection.
 */
var _super = DC_VIEW.CollectionView;
var CollectionViewEdit = _super.extend(
/** @lends CollectionView.prototype */{
    //MODEL is either a DatasetCollection (or subclass) or a DatasetCollectionElement (list of pairs)

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** sub view class used for datasets */
    DatasetDCEViewClass : DC_EDIT.DatasetDCEListItemEdit,
    /** sub view class used for nested collections */
    NestedDCDCEViewClass: DC_EDIT.NestedDCDCEListItemEdit,

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HistoryContents events
     *  @param {Object} attributes optional settings for the panel
     */
    initialize : function( attributes ){
        _super.prototype.initialize.call( this, attributes );
    },

    /** In this override, make the collection name editable
     */
    _setUpBehaviors : function( $where ){
        $where = $where || this.$el;
        _super.prototype._setUpBehaviors.call( this, $where );
        if( !this.model ){ return; }

        // anon users shouldn't have access to any of the following
        if( !Galaxy.user || Galaxy.user.isAnonymous() ){
            return;
        }

        //TODO: extract
        var panel = this,
            nameSelector = '> .controls .name';
        $where.find( nameSelector )
            .attr( 'title', _l( 'Click to rename collection' ) )
            .tooltip({ placement: 'bottom' })
            .make_text_editable({
                on_finish: function( newName ){
                    var previousName = panel.model.get( 'name' );
                    if( newName && newName !== previousName ){
                        panel.$el.find( nameSelector ).text( newName );
                        panel.model.save({ name: newName })
                            .fail( function(){
                                panel.$el.find( nameSelector ).text( panel.model.previous( 'name' ) );
                            });
                    } else {
                        panel.$el.find( nameSelector ).text( previousName );
                    }
                }
            });
    },

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'CollectionViewEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListCollectionViewEdit = CollectionViewEdit.extend(
/** @lends ListCollectionView.prototype */{

    //TODO: not strictly needed - due to switch in CollectionView._getContentClass
    /** sub view class used for datasets */
    DatasetDCEViewClass : DC_EDIT.DatasetDCEListItemEdit,

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListCollectionViewEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class Editable, read-only View/Controller for a dataset collection. */
var PairCollectionViewEdit = ListCollectionViewEdit.extend(
/** @lends PairCollectionViewEdit.prototype */{

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'PairCollectionViewEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class Editable (roughly since these collections are immutable),
 *  View/Controller for a dataset collection.
 */
var NestedPairCollectionViewEdit = PairCollectionViewEdit.extend(
/** @lends NestedPairCollectionViewEdit.prototype */{

    /** Override to remove the editable text from the name/identifier - these collections are considered immutable */
    _setUpBehaviors : function( $where ){
        _super.prototype._setUpBehaviors.call( this, $where );
    },

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'NestedPairCollectionViewEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class editable, View/Controller for a list of pairs dataset collection. */
var ListOfPairsCollectionViewEdit = CollectionViewEdit.extend(
/** @lends ListOfPairsCollectionView.prototype */{

    //TODO: not strictly needed - due to switch in CollectionView._getContentClass
    /** sub view class used for nested collections */
    NestedDCDCEViewClass : DC_EDIT.NestedDCDCEListItemEdit.extend({
        foldoutPanelClass : NestedPairCollectionViewEdit
    }),

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListOfPairsCollectionViewEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class View/Controller for a list of lists dataset collection. */
var ListOfListsCollectionViewEdit = CollectionViewEdit.extend(
/** @lends ListOfListsCollectionView.prototype */{

    //TODO: not strictly needed - due to switch in CollectionView._getContentClass
    /** sub view class used for nested collections */
    NestedDCDCEViewClass : DC_EDIT.NestedDCDCEListItemEdit.extend({
        foldoutPanelClass : NestedPairCollectionViewEdit
    }),

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListOfListsCollectionViewEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//==============================================================================
    return {
        CollectionViewEdit              : CollectionViewEdit,
        ListCollectionViewEdit          : ListCollectionViewEdit,
        PairCollectionViewEdit          : PairCollectionViewEdit,
        ListOfPairsCollectionViewEdit   : ListOfPairsCollectionViewEdit,
        ListOfListsCollectionViewEdit   : ListOfListsCollectionViewEdit
    };
});
