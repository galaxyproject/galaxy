define([
    "mvc/dataset/dataset-list-element",
    "mvc/base-mvc",
    "utils/localization"
], function( DATASET_LI, BASE_MVC, _l ){
/* global Backbone, LoggableMixin */
//==============================================================================
var ListItemView = BASE_MVC.ListItemView;
/** @class Read only view for DatasetCollection.
 */
var DCBaseView = ListItemView.extend({
//TODO: may not be needed

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    className   : ListItemView.prototype.className + " dataset-collection",
    /**  */
    fxSpeed     : 'fast',

//TODO: ununsed
    /** set up */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( 'DCBaseView.initialize:', attributes );
        ListItemView.prototype.initialize.call( this, attributes );
    },

    /** In this override, don't show`or render any details (no need to do anything here)
     *      - currently the parent control will load a panel for this collection over itself
     *  @fires expanded when a body has been expanded
     */
    expand : function(){
        var view = this;
        return view._fetchModelDetails()
            .always(function(){
                view.trigger( 'expanded', view );
            });
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

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCBaseView(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
DCBaseView.prototype.templates = (function(){

    // use element identifier
    var titleBarTemplate = BASE_MVC.wrapTemplate([
        '<div class="title-bar clear" tabindex="0">',
            '<div class="title">',
                '<span class="name"><%- collection.element_identifier || collection.name %></span>',
            '</div>',
            '<div class="subtitle"></div>',
        '</div>'
    ], 'collection' );

    return _.extend( {}, ListItemView.prototype.templates, {
        titleBar : titleBarTemplate
    });
}());


//==============================================================================
/** @class Read only view for DatasetCollectionElement.
 */
var DCEBaseView = ListItemView.extend({
//TODO: this might be expendable - compacted with HDADCEBaseView

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    logger              : console,

    /** add the DCE class to the list item */
    className   : ListItemView.prototype.className + " dataset-collection-element",
    /** jq fx speed for this view */
    fxSpeed     : 'fast',

    /**  */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( 'DCEBaseView.initialize:', attributes );
        ListItemView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DCEBaseView(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
DCEBaseView.prototype.templates = (function(){

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
/** @class Read only view for a DatasetCollectionElement that is also an HDA.
 */
var DatasetDCEBaseView = DATASET_LI.DatasetListItemView.extend({

    className   : DATASET_LI.DatasetListItemView.prototype.className + " dataset-collection-element",

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    /**  */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( 'DatasetDCEBaseView.initialize:', attributes );
        DATASET_LI.DatasetListItemView.prototype.initialize.call( this, attributes );
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'DatasetDCEBaseView(' + modelString + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
DatasetDCEBaseView.prototype.templates = (function(){

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
var NestedDCDCEBaseView = DCBaseView.extend({

    className   : DCBaseView.prototype.className + " dataset-collection-element",

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    /** In this override, add the state as a class for use with state-based CSS */
    _swapNewRender : function( $newRender ){
        DATASET_LI.DatasetListItemView.prototype._swapNewRender.call( this, $newRender );
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
        return 'NestedDCDCEBaseView(' + modelString + ')';
    }
});


//==============================================================================
    return {
        DCBaseView          : DCBaseView,
        DCEBaseView         : DCEBaseView,
        DatasetDCEBaseView  : DatasetDCEBaseView,
        NestedDCDCEBaseView : NestedDCDCEBaseView
    };
});
