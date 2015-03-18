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

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'CollectionPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//------------------------------------------------------------------------------ TEMPLATES
// CollectionPanelEdit.prototype.templates = (function(){

//     var controlsTemplate = BASE_MVC.wrapTemplate([
//         '<div class="controls">',
//             '<div class="navigation">',
//                 '<a class="back" href="javascript:void(0)">',
//                     '<span class="fa fa-icon fa-angle-left"></span>',
//                     _l( 'Back to ' ), '<%- view.parentName %>',
//                 '</a>',
//             '</div>',

//             '<div class="title">',
//                 '<div class="name"><%- collection.name || collection.element_identifier %></div>',
//                 '<div class="subtitle">',
// //TODO: remove logic from template
//                     '<% if( collection.collection_type === "list" ){ %>',
//                         _l( 'a list of datasets' ),
//                     '<% } else if( collection.collection_type === "paired" ){ %>',
//                         _l( 'a pair of datasets' ),
//                     '<% } else if( collection.collection_type === "list:paired" ){ %>',
//                         _l( 'a list of paired datasets' ),
//                     '<% } %>',
//                 '</div>',
//             '</div>',
//         '</div>'
//     ], 'collection' );

//     return _.extend( _.clone( _super.prototype.templates ), {
//         controls : controlsTemplate
//     });
// }());



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
/** @class non-editable, read-only View/Controller for a dataset collection. */
var PairCollectionPanelEdit = ListCollectionPanelEdit.extend(
/** @lends PairCollectionPanel.prototype */{

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'PairCollectionPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListOfPairsCollectionPanelEdit = CollectionPanelEdit.extend(
/** @lends ListOfPairsCollectionPanel.prototype */{

    //TODO: not strictly needed - due to switch in CollectionPanel._getContentClass
    /** sub view class used for nested collections */
    NestedDCDCEViewClass : DC_EDIT.NestedDCDCEListItemEdit.extend({
        foldoutPanelClass : PairCollectionPanelEdit
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
