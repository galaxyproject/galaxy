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
// =============================================================================
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
    DatasetDCEViewClass  : DC_LI.DatasetDCEListItemView,
    /** sub view class used for nested collections */
    NestedDCDCEViewClass : DC_LI.NestedDCDCEListItemView,
    /** key of attribute in model to assign to this.collection */
    modelCollectionKey : 'elements',

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HistoryContents events
     *  @param {Object} attributes optional settings for the panel
     */
    initialize : function( attributes ){
        _super.prototype.initialize.call( this, attributes );
        this.linkTarget = attributes.linkTarget || '_blank';

        this.hasUser = attributes.hasUser;
        this.panelStack = [];
        this.parentName = attributes.parentName;

        //window.collectionPanel = this;
    },

    // ------------------------------------------------------------------------ sub-views
    /** In this override, use model.getVisibleContents */
    _filterCollection : function(){
//TODO: should *not* be model.getVisibleContents
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
            hasUser         : this.hasUser
        });
    },

    /** when a sub-view is clicked in the collection panel that is itself a collection,
     *      hide this panel's elements and show the sub-collection in its own panel.
     */
    _setUpItemViewListeners : function( view ){
        var panel = this;
        _super.prototype._setUpItemViewListeners.call( panel, view );
        //TODO:?? doesn't seem to belong here
        if( view.model.get( 'element_type' ) === 'dataset_collection' ){
            view.on( 'expanded', function( collectionView ){
                panel.info( 'expanded', collectionView );
                panel._addCollectionPanel( collectionView );
            });
        }
        return panel;
    },

    /** When a sub-collection is clicked, hide the current panel and render the sub-collection in its own panel  */
    _addCollectionPanel : function( collectionView ){
//TODO: a bit hackish
        var currPanel = this,
            collectionModel = collectionView.model;

        //this.debug( 'collection panel (stack), collectionView:', collectionView );
        //this.debug( 'collection panel (stack), collectionModel:', collectionModel );
        var panel = new PairCollectionPanel({
                model       : collectionModel,
                parentName  : this.model.get( 'name' ),
                linkTarget  : this.linkTarget
            });
        currPanel.panelStack.push( panel );

        currPanel.$( '.controls' ).add( '.list-items' ).hide();
        currPanel.$el.append( panel.$el );
        panel.on( 'close', function(){
            currPanel.render();
            collectionView.collapse();
            currPanel.panelStack.pop();
        });

        //TODO: to hdca-model, hasDetails
        if( !panel.model.hasDetails() ){
            var xhr = panel.model.fetch();
            xhr.done( function(){
                //TODO: (re-)render collection contents
                panel.render();
            });
        } else {
            panel.render();
        }
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
    NestedDCDCEViewClass : DC_LI.NestedDCDCEListItemView,

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
