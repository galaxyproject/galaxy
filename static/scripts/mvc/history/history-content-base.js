define([
    "mvc/dataset/states",
    "mvc/base-mvc",
    "utils/localization"
], function( STATES, BASE_MVC, _l ){
//==============================================================================
/** how the type_id attribute is built for the history's mixed contents collection */
var typeIdStr = function _typeIdStr( type, id ){
    return [ type, id ].join( '-' );
};

//==============================================================================
/** @class base model for content items contained in a history or hdca.
 */
var HistoryContentMixin = {
//TODO:?? into true Backbone.Model?

    /** default attributes for a model */
    defaults : {
        // parent (containing) history
        history_id          : null,
        history_content_type: 'dataset_collection',
        hid                 : 0,

        name                : '(unnamed content)',
        // one of HistoryDatasetAssociation.STATES
        state               : 'new',

        deleted             : false,
        visible             : true,

//TODO: update to false when this is correctly passed from the API (when we have a security model for this)
        accessible          : true,
        purged              : false
    },

    // ........................................................................ mixed content element
    // in order to be part of a MIXED bbone collection, we can't rely on the id
    //  (which may collide btwn models of different classes)
    // build a new id (type_id) that prefixes the history_content_type so the bbone collection can differentiate
    idAttribute : 'type_id',

    constructor : function( attrs, options ){
        this.info( 'HistoryContentMixin.constructor:', this, attrs, options );
        attrs.type_id = typeIdStr( attrs.history_content_type, attrs.id );
        Backbone.Model.apply( this, arguments );
    },

    _typeIdStr : function(){
        return typeIdStr( this.get( 'history_content_type' ), this.get( 'id' ) );
    },

    initialize : function( attrs, options ){
        this.debug( 'HistoryContentMixin.initialize', attrs, options );
        // assumes type won't change
        //TODO: not sure this covers all the bases...
        this.on( 'change:id', this._createTypeId );

        this._setUpListeners();
    },

    /** set up any event listeners
     */
    _setUpListeners : function(){
    },

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

    /** Is this hda deleted or purged? */
    isDeletedOrPurged : function(){
        return ( this.get( 'deleted' ) || this.get( 'purged' ) );
    },

    /** Is this HDA in a 'ready' state; where 'Ready' states are states where no
     *      processing (for the ds) is left to do on the server.
     */
    inReadyState : function(){
        var ready = _.contains( STATES.READY_STATES, this.get( 'state' ) );
        return ( this.isDeletedOrPurged() || ready );
    },

    ///** Does this model already contain detailed data (as opposed to just summary level data)? */
    //hasDetails : function(){
    //    // override
    //    return true;
    //},

    /** Convenience function to match hda.has_data. */
    hasData : function(){
        // override
        return true;
    },

    // ........................................................................ ajax
    /**  */
    urlRoot: galaxy_config.root + 'api/histories/',

    /** full url spec. for this HDA */
    url : function(){
        var url = this.urlRoot + this.get( 'history_id' ) + '/contents/'
             + this.get('history_content_type') + 's/' + this.get( 'id' );
        //console.debug( this + '.url:', url );
        return url;
    },

    /** returns misc. web urls for rendering things like re-run, display, etc. */
    urls : function(){
//TODO: would be nice if the API did this
        // override
        return {};
    },

    /** save this HDA, _Mark_ing it as deleted (just a flag) */
    'delete' : function( options ){
        if( this.get( 'deleted' ) ){ return jQuery.when(); }
        return this.save( { deleted: true }, options );
    },
    /** save this HDA, _Mark_ing it as undeleted */
    undelete : function( options ){
        if( !this.get( 'deleted' ) || this.get( 'purged' ) ){ return jQuery.when(); }
        return this.save( { deleted: false }, options );
    },

    /** save this HDA as not visible */
    hide : function( options ){
        if( !this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: false }, options );
    },
    /** save this HDA as visible */
    unhide : function( options ){
        if( this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: true }, options );
    },

    /** purge this HDA and remove the underlying dataset file from the server's fs */
    purge : function _purge( options ){
//TODO: use, override model.destroy, HDA.delete({ purge: true })
        // override
        return jQuery.when();
    },

    // ........................................................................ searching
    /** what attributes of the content will be used in a text search */
    searchAttributes : [
        'name'
    ],

    /** our attr keys don't often match the labels we display to the user - so, when using
     *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
     *      following attr keys.
     */
    searchAliases : {
        title       : 'name'
    },

    /** search the attribute with key attrKey for the string searchFor; T/F if found */
    searchAttribute : function( attrKey, searchFor ){
        var attrVal = this.get( attrKey );
        //console.debug( 'searchAttribute', attrKey, attrVal, searchFor );
        // bail if empty searchFor or unsearchable values
        if( !searchFor
        ||  ( attrVal === undefined || attrVal === null ) ){
            return false;
        }
        // pass to sep. fn for deep search of array attributes
        if( _.isArray( attrVal ) ){ return this._searchArrayAttribute( attrVal, searchFor ); }
        return ( attrVal.toString().toLowerCase().indexOf( searchFor.toLowerCase() ) !== -1 );
    },

    /** deep(er) search for array attributes; T/F if found */
    _searchArrayAttribute : function( array, searchFor ){
        //console.debug( '_searchArrayAttribute', array, searchFor );
        searchFor = searchFor.toLowerCase();
        //precondition: searchFor has already been validated as non-empty string
        //precondition: assumes only 1 level array
        //TODO: could possibly break up searchFor more (CSV...)
        return _.any( array, function( elem ){
            return ( elem.toString().toLowerCase().indexOf( searchFor.toLowerCase() ) !== -1 );
        });
    },

    /** search all searchAttributes for the string searchFor,
     *      returning a list of keys of attributes that contain searchFor
     */
    search : function( searchFor ){
        var model = this;
        return _.filter( this.searchAttributes, function( key ){
            return model.searchAttribute( key, searchFor );
        });
    },

    /** alias of search, but returns a boolean; accepts attribute specifiers where
     *      the attributes searched can be narrowed to a single attribute using
     *      the form: matches( 'genome_build=hg19' )
     *      (the attribute keys allowed can also be aliases to the true attribute key;
     *          see searchAliases above)
     *  @param {String} term   plain text or ATTR_SPECIFIER sep. key=val pair
     *  @returns {Boolean} was term found in (any) attribute(s)
     */
    matches : function( term ){
        var ATTR_SPECIFIER = '=',
            split = term.split( ATTR_SPECIFIER );
        // attribute is specified - search only that
        if( split.length >= 2 ){
            var attrKey = split[0];
            attrKey = this.searchAliases[ attrKey ] || attrKey;
            return this.searchAttribute( attrKey, split[1] );
        }
        // no attribute is specified - search all attributes in searchAttributes
        return !!this.search( term ).length;
    },

    /** an implicit AND search for all terms; IOW, an hda must match all terms given
     *      where terms is a whitespace separated value string.
     *      e.g. given terms of: 'blah bler database=hg19'
     *          an HDA would have to have attributes containing blah AND bler AND a genome_build == hg19
     *      To include whitespace in terms: wrap the term in double quotations.
     */
    matchesAll : function( terms ){
        var model = this;
        // break the terms up by whitespace and filter out the empty strings
        terms = terms.match( /(".*"|\w*=".*"|\S*)/g ).filter( function( s ){ return !!s; });
        return _.all( terms, function( term ){
            term = term.replace( /"/g, '' );
            return model.matches( term );
        });
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
/** @class base model for content items contained in a history or hdca.
 *  @name HistoryContent
 *
 *  @augments Backbone.Model
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryContent = Backbone.Model.extend( BASE_MVC.LoggableMixin ).extend( HistoryContentMixin );
//TODO:?? here or return as module fn?
HistoryContent.typeIdStr = typeIdStr;


//==============================================================================
    return {
        HistoryContentMixin : HistoryContentMixin,
        HistoryContent      : HistoryContent
    };
});
