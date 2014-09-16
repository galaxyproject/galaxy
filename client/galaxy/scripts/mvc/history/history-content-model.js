define([
    "mvc/dataset/states",
    "mvc/base-mvc",
    "utils/localization"
], function( STATES, BASE_MVC, _l ){
//==============================================================================
/** How the type_id attribute is built for the history's mixed contents collection */
var typeIdStr = function _typeIdStr( type, id ){
    return [ type, id ].join( '-' );
};

//==============================================================================
/** @class Mixin for HistoryContents content (HDAs, HDCAs).
 */
var HistoryContentMixin = {
//TODO:?? into true Backbone.Model?

    /** default attributes for a model */
    defaults : {
        /** parent (containing) history */
        history_id          : null,
        /** some content_type (HistoryContents can contain mixed model classes) */
        history_content_type: null,
        /** indicating when/what order the content was generated in the context of the history */
        hid                 : null,
        /** whether the user wants the content shown (visible) */
        visible             : true
    },

    // ........................................................................ mixed content element
//TODO: there's got to be a way to move this into HistoryContents - if we can do that, this class might not be needed
    // In order to be part of a MIXED bbone collection, we can't rely on the id
    //  (which may collide btwn models of different classes)
    // Build a new id (type_id) that prefixes the history_content_type so the bbone collection can differentiate
    idAttribute : 'type_id',

    /** override constructor to build type_id and insert into original attributes */
    constructor : function( attrs, options ){
        attrs.type_id = typeIdStr( attrs.history_content_type, attrs.id );
        this.debug( 'HistoryContentMixin.constructor:', attrs.type_id );
        Backbone.Model.apply( this, arguments );
    },

    /** object level fn for building the type_id string */
    _typeIdStr : function(){
        return typeIdStr( this.get( 'history_content_type' ), this.get( 'id' ) );
    },

    /** add listener to re-create type_id when the id changes */
    initialize : function( attrs, options ){
        this.on( 'change:id', this._createTypeId );
    },

    /** set the type_id in the model attributes */
    _createTypeId : function(){
        this.set( 'type_id', this._typeIdStr() );
    },

    // ........................................................................ common queries
    /** the more common alias of visible */
    hidden : function(){
        return !this.get( 'visible' );
    },

    /** based on show_deleted, show_hidden (gen. from the container control),
     *      would this ds show in the list of ds's?
     *  @param {Boolean} show_deleted are we showing deleted hdas?
     *  @param {Boolean} show_hidden are we showing hidden hdas?
     */
    isVisible : function( show_deleted, show_hidden ){
//TODO:?? Another unfortunate name collision
        var isVisible = true;
        if( ( !show_deleted )
        &&  ( this.get( 'deleted' ) || this.get( 'purged' ) ) ){
            isVisible = false;
        }
        if( ( !show_hidden )
        &&  ( !this.get( 'visible' ) ) ){
            isVisible = false;
        }
        return isVisible;
    },

    // ........................................................................ ajax
//TODO: global
//TODO: these are probably better done on the leaf classes
    /** history content goes through the 'api/histories' API */
    urlRoot: galaxy_config.root + 'api/histories/',

    /** full url spec. for this content */
    url : function(){
        var url = this.urlRoot + this.get( 'history_id' ) + '/contents/'
             + this.get('history_content_type') + 's/' + this.get( 'id' );
        return url;
    },

    /** save this content as not visible */
    hide : function( options ){
        if( !this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: false }, options );
    },
    /** save this content as visible */
    unhide : function( options ){
        if( this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: true }, options );
    },

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId = this.get( 'hid' ) + ' :"' + this.get( 'name' ) + '",' + nameAndId;
        }
        return 'HistoryContent(' + nameAndId + ')';
    }
};


//==============================================================================
//TODO: needed?
/** @class (Concrete/non-mixin) base model for content items.
 */
var HistoryContent = Backbone.Model.extend( BASE_MVC.LoggableMixin ).extend( HistoryContentMixin );


//==============================================================================
    return {
        typeIdStr           : typeIdStr,
        HistoryContentMixin : HistoryContentMixin,
        HistoryContent      : HistoryContent
    };
});
