define([
    "mvc/list/list-panel",
    "mvc/collection/collection-model",
    "mvc/collection/collection-li",
    "mvc/base-mvc",
    "utils/localization"
], function( LIST_PANEL, DC_MODEL, DC_LI, BASE_MVC, _l ){
/* =============================================================================
TODO:

============================================================================= */
/** @class non-editable, read-only View/Controller for a dataset collection.
 */
var _super = LIST_PANEL.ModelListPanel;
var CollectionPanel = _super.extend(
/** @lends CollectionPanel.prototype */{
    //MODEL is either a DatasetCollection (or subclass) or a DatasetCollectionElement (list of pairs)

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    className           : _super.prototype.className + ' dataset-collection-panel',

    /** sub view class used for datasets */
    DatasetDCEViewClass : DC_LI.DatasetDCEListItemView,
    /** sub view class used for nested collections */
    NestedDCDCEViewClass: DC_LI.NestedDCDCEListItemView,
    /** key of attribute in model to assign to this.collection */
    modelCollectionKey  : 'elements',

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HistoryContents events
     *  @param {Object} attributes optional settings for the panel
     */
    initialize : function( attributes ){
        _super.prototype.initialize.call( this, attributes );
        this.linkTarget = attributes.linkTarget || '_blank';

        this.hasUser = attributes.hasUser;

        /**  */
        this.panelStack = [];
        /**  */
        this.parentName = attributes.parentName;
        /**  */
        this.foldoutStyle = attributes.foldoutStyle || 'foldout';
    },

    // ------------------------------------------------------------------------ sub-views
    /** In this override, use model.getVisibleContents */
    _filterCollection : function(){
//TODO: should *not* be model.getVisibleContents - visibility is not model related
        return this.model.getVisibleContents();
    },

    /** override to return proper view class based on element_type */
    _getItemViewClass : function( model ){
        //this.debug( this + '._getItemViewClass:', model );
//TODO: subclasses use DCEViewClass - but are currently unused - decide
        switch( model.get( 'element_type' ) ){
            case 'hda':
                return this.DatasetDCEViewClass;
            case 'dataset_collection':
                return this.NestedDCDCEViewClass;
        }
        throw new TypeError( 'Unknown element type:', model.get( 'element_type' ) );
    },

    /** override to add link target and anon */
    _getItemViewOptions : function( model ){
        var options = _super.prototype._getItemViewOptions.call( this, model );
        return _.extend( options, {
            linkTarget      : this.linkTarget,
            hasUser         : this.hasUser,
//TODO: could move to only nested: list:paired
            foldoutStyle    : this.foldoutStyle
        });
    },

    // ------------------------------------------------------------------------ collection sub-views
    /** In this override, add/remove expanded/collapsed model ids to/from web storage */
    _setUpItemViewListeners : function( view ){
        var panel = this;
        _super.prototype._setUpItemViewListeners.call( panel, view );

        // use pub-sub to: handle drilldown expansion and collapse
        view.on( 'expanded:drilldown', function( v, drilldown ){
            this._expandDrilldownPanel( drilldown );
        }, this );
        view.on( 'collapsed:drilldown', function( v, drilldown ){
            this._collapseDrilldownPanel( drilldown );
        }, this );
        return this;
    },

    /** Handle drill down by hiding this panels list and controls and showing the sub-panel */
    _expandDrilldownPanel : function( drilldown ){
        this.panelStack.push( drilldown );
        // hide this panel's controls and list, set the name for back navigation, and attach to the $el
        this.$( '> .controls' ).add( this.$list() ).hide();
        drilldown.parentName = this.model.get( 'name' );
        this.$el.append( drilldown.render().$el );
    },

    /** Handle drilldown close by freeing the panel and re-rendering this panel */
    _collapseDrilldownPanel : function( drilldown ){
        this.panelStack.pop();
        this.render();
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : {
        'click .navigation .back'       : 'close'
    },

    /** close/remove this collection panel */
    close : function( event ){
        this.$el.remove();
        this.trigger( 'close' );
    },

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'CollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//------------------------------------------------------------------------------ TEMPLATES
CollectionPanel.prototype.templates = (function(){

    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
            '<div class="navigation">',
                '<a class="back" href="javascript:void(0)">',
                    '<span class="fa fa-icon fa-angle-left"></span>',
                    _l( 'Back to ' ), '<%- view.parentName %>',
                '</a>',
            '</div>',

            '<div class="title">',
                '<div class="name"><%- collection.name || collection.element_identifier %></div>',
                '<div class="subtitle">',
//TODO: remove logic from template
                    '<% if( collection.collection_type === "list" ){ %>',
                        _l( 'a list of datasets' ),
                    '<% } else if( collection.collection_type === "paired" ){ %>',
                        _l( 'a pair of datasets' ),
                    '<% } else if( collection.collection_type === "list:paired" ){ %>',
                        _l( 'a list of paired datasets' ),
                    '<% } %>',
                '</div>',
            '</div>',
        '</div>'
    ], 'collection' );

    return _.extend( _.clone( _super.prototype.templates ), {
        controls : controlsTemplate
    });
}());



// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListCollectionPanel = CollectionPanel.extend(
/** @lends ListCollectionPanel.prototype */{

    //TODO: not strictly needed - due to switch in CollectionPanel._getContentClass
    /** sub view class used for datasets */
    DatasetDCEViewClass : DC_LI.DatasetDCEListItemView,

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListCollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var PairCollectionPanel = ListCollectionPanel.extend(
/** @lends PairCollectionPanel.prototype */{

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'PairCollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListOfPairsCollectionPanel = CollectionPanel.extend(
/** @lends ListOfPairsCollectionPanel.prototype */{

    //TODO: not strictly needed - due to switch in CollectionPanel._getContentClass
    /** sub view class used for nested collections */
    NestedDCDCEViewClass : DC_LI.NestedDCDCEListItemView.extend({
        foldoutPanelClass : PairCollectionPanel
    }),

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListOfPairsCollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//==============================================================================
    return {
        CollectionPanel             : CollectionPanel,
        ListCollectionPanel         : ListCollectionPanel,
        PairCollectionPanel         : PairCollectionPanel,
        ListOfPairsCollectionPanel  : ListOfPairsCollectionPanel
    };
});
