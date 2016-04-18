define([
    "mvc/dataset/states",
    "mvc/base-mvc",
    "utils/localization"
], function( STATES, BASE_MVC, _l ){
'use strict';

//==============================================================================
/** @class Mixin for HistoryContents content (HDAs, HDCAs).
 */
var HistoryContentMixin = {

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
    // In order to be part of a MIXED bbone collection, we can't rely on the id
    //  (which may collide btwn models of different classes)
    // Instead, use type_id which prefixes the history_content_type so the bbone collection can differentiate
    idAttribute : 'type_id',

    /** override because backbone tests boolean( idAttribute ), but it's not an empty string even for new models
     *  due to our use of type_id.
     */
    // isNew : function(){
    //     return !this.get( 'id' );
    // },

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
    //TODO?: these are probably better done on the leaf classes
    /** history content goes through the 'api/histories' API */
    urlRoot: Galaxy.root + 'api/histories/',

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
    toString : function(){
        return ([ this.get( 'type_id' ), this.get( 'hid' ), this.get( 'name' ) ].join(':'));
    }
};


//==============================================================================
    return {
        HistoryContentMixin : HistoryContentMixin
    };
});
