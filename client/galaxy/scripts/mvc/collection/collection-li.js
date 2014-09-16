define([
    "mvc/list/list-item",
    "mvc/dataset/dataset-li",
    "mvc/base-mvc",
    "utils/localization"
], function( LIST_ITEM, DATASET_LI, BASE_MVC, _l ){
/* global Backbone, LoggableMixin */
//==============================================================================
var FoldoutListItemView = LIST_ITEM.FoldoutListItemView,
    ListItemView = LIST_ITEM.ListItemView;
/** @class Read only view for DatasetCollection.
 */
var DCListItemView = FoldoutListItemView.extend(
/** @lends DCListItemView.prototype */{
//TODO: may not be needed

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    className   : FoldoutListItemView.prototype.className + " dataset-collection",
    id          : function(){
        return [ 'dataset_collection', this.model.get( 'id' ) ].join( '-' );
    },

    /** override to add linkTarget */
    initialize : function( attributes ){
        FoldoutListItemView.prototype.initialize.call( this, attributes );
        this.linkTarget = attributes.linkTarget || '_blank';
    },

    // ......................................................................... rendering
    //TODO:?? possibly move to listItem
    /** render a subtitle to show the user what sort of collection this is */
    _renderSubtitle : function(){
        var $subtitle = $( '<div class="subtitle"></div>' );
        //TODO: would be good to get this in the subtitle
        //var len = this.model.elements.length;
        switch( this.model.get( 'collection_type' ) ){
            case 'list':
                return $subtitle.text( _l( 'a list of datasets' ) );
            case 'paired':
                return $subtitle.text( _l( 'a pair of datasets' ) );
            case 'list:paired':
                return $subtitle.text( _l( 'a list of paired datasets' ) );
        }
        return $subtitle;
    },

    // ......................................................................... foldout
    /** override to add linktarget to sub-panel */
    _getFoldoutPanelOptions : function(){
        var options = FoldoutListItemView.prototype._getFoldoutPanelOptions.call( this );
        return _.extend( options, {
            linkTarget : this.linkTarget
        });
    },

    /** override to not catch sub-panel selectors */
    $selector : function(){
        return this.$( '> .selector' );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCListItemView(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
DCListItemView.prototype.templates = (function(){

    // use element identifier
    var titleBarTemplate = BASE_MVC.wrapTemplate([
        '<div class="title-bar clear" tabindex="0">',
            '<div class="title">',
                '<span class="name"><%- collection.element_identifier || collection.name %></span>',
            '</div>',
            '<div class="subtitle"></div>',
        '</div>'
    ], 'collection' );

    return _.extend( {}, FoldoutListItemView.prototype.templates, {
        titleBar : titleBarTemplate
    });
}());


//==============================================================================
/** @class Read only view for DatasetCollectionElement.
 */
var DCEListItemView = ListItemView.extend(
/** @lends DCEListItemView.prototype */{
//TODO: this might be expendable - compacted with HDAListItemView

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** add the DCE class to the list item */
    className   : ListItemView.prototype.className + " dataset-collection-element",
    /** jq fx speed for this view */
    fxSpeed     : 'fast',

    /** set up */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( 'DCEListItemView.initialize:', attributes );
        ListItemView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCEListItemView(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
DCEListItemView.prototype.templates = (function(){

    // use the element identifier here - since that will persist and the user will need it
    var titleBarTemplate = BASE_MVC.wrapTemplate([
        '<div class="title-bar clear" tabindex="0">',
            '<div class="title">',
                '<span class="name"><%- element.element_identifier %></span>',
            '</div>',
            '<div class="subtitle"></div>',
        '</div>'
    ], 'element' );

    return _.extend( {}, ListItemView.prototype.templates, {
        titleBar : titleBarTemplate
    });
}());


//==============================================================================
/** @class Read only view for a DatasetCollectionElement that is also an DatasetAssociation
 *      (a dataset contained in a dataset collection).
 */
var DatasetDCEListItemView = DATASET_LI.DatasetListItemView.extend(
/** @lends DatasetDCEListItemView.prototype */{

    className   : DATASET_LI.DatasetListItemView.prototype.className + " dataset-collection-element",

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** set up */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( 'DatasetDCEListItemView.initialize:', attributes );
        DATASET_LI.DatasetListItemView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DatasetDCEListItemView(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
DatasetDCEListItemView.prototype.templates = (function(){

    // use the element identifier here and not the dataset name
    //TODO:?? can we steal the DCE titlebar?
    var titleBarTemplate = BASE_MVC.wrapTemplate([
        '<div class="title-bar clear" tabindex="0">',
            '<span class="state-icon"></span>',
            '<div class="title">',
                '<span class="name"><%- element.element_identifier %></span>',
            '</div>',
        '</div>'
    ], 'element' );

    return _.extend( {}, DATASET_LI.DatasetListItemView.prototype.templates, {
        titleBar : titleBarTemplate
    });
}());


//==============================================================================
/** @class Read only view for a DatasetCollectionElement that is also a DatasetCollection
 *      (a nested DC).
 */
var NestedDCDCEListItemView = DCListItemView.extend(
/** @lends NestedDCDCEListItemView.prototype */{

    className   : DCListItemView.prototype.className + " dataset-collection-element",

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    /** In this override, add the state as a class for use with state-based CSS */
    _swapNewRender : function( $newRender ){
        DCListItemView.prototype._swapNewRender.call( this, $newRender );
//TODO: model currently has no state
        var state = this.model.get( 'state' ) || 'ok';
        //if( this.model.has( 'state' ) ){
        this.$el.addClass( 'state-' + state );
        //}
        return this.$el;
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'NestedDCDCEListItemView(' + modelString + ')';
    }
});


//==============================================================================
    return {
        DCListItemView          : DCListItemView,
        DCEListItemView         : DCEListItemView,
        DatasetDCEListItemView  : DatasetDCEListItemView,
        NestedDCDCEListItemView : NestedDCDCEListItemView
    };
});
