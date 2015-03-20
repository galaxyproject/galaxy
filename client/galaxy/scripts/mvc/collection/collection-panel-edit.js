define([
    "mvc/collection/collection-panel",
    "mvc/collection/collection-model",
    "mvc/collection/collection-li-edit",
    "mvc/base-mvc",
    "utils/localization"
], function( DC_PANEL, DC_MODEL, DC_EDIT, BASE_MVC, _l ){
/* =============================================================================
TODO:

============================================================================= */
/** @class editable View/Controller for a dataset collection.
 */
var _super = DC_PANEL.CollectionPanel;
var CollectionPanelEdit = _super.extend(
/** @lends CollectionPanel.prototype */{
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
        if( !Galaxy.currUser || Galaxy.currUser.isAnonymous() ){
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
        return 'CollectionPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListCollectionPanelEdit = CollectionPanelEdit.extend(
/** @lends ListCollectionPanel.prototype */{

    //TODO: not strictly needed - due to switch in CollectionPanel._getContentClass
    /** sub view class used for datasets */
    DatasetDCEViewClass : DC_EDIT.DatasetDCEListItemEdit,

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListCollectionPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class Editable, read-only View/Controller for a dataset collection. */
var PairCollectionPanelEdit = ListCollectionPanelEdit.extend(
/** @lends PairCollectionPanelEdit.prototype */{

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'PairCollectionPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class Editable (roughly since these collections are immutable),
 *  View/Controller for a dataset collection.
 */
var NestedPairCollectionPanelEdit = PairCollectionPanelEdit.extend(
/** @lends NestedPairCollectionPanelEdit.prototype */{

    /** Override to remove the editable text from the name/identifier - these collections are considered immutable */
    _setUpBehaviors : function( $where ){
        _super.prototype._setUpBehaviors.call( this, $where );
    },

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'NestedPairCollectionPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListOfPairsCollectionPanelEdit = CollectionPanelEdit.extend(
/** @lends ListOfPairsCollectionPanel.prototype */{

    //TODO: not strictly needed - due to switch in CollectionPanel._getContentClass
    /** sub view class used for nested collections */
    NestedDCDCEViewClass : DC_EDIT.NestedDCDCEListItemEdit.extend({
        foldoutPanelClass : NestedPairCollectionPanelEdit
    }),

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListOfPairsCollectionPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//==============================================================================
    return {
        CollectionPanelEdit             : CollectionPanelEdit,
        ListCollectionPanelEdit         : ListCollectionPanelEdit,
        PairCollectionPanelEdit         : PairCollectionPanelEdit,
        ListOfPairsCollectionPanelEdit  : ListOfPairsCollectionPanelEdit
    };
});
