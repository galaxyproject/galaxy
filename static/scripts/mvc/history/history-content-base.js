define([
    "mvc/base-mvc",
    "utils/localization"
], function( baseMVC, _l ){
//==============================================================================
/** @class base model for content items contained in a history or hdca.
 *  @name HistoryContent
 *
 *  @augments Backbone.Model
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryContent = Backbone.Model.extend( baseMVC.LoggableMixin ).extend( {
    idAttribute : 'type_id',

    constructor : function( attrs, options ){
        attrs.type_id = HistoryContent.typeIdStr( attrs.history_content_type, attrs.id );
        Backbone.Model.apply( this, arguments );
    },

    initialize : function( attrs, options ){
        // assumes type won't change
        this.on( 'change:id', this._createTypeId );
        //TODO: not sure this covers all the bases...
    },
    _createTypeId : function(){
        this.set( 'type_id', TypeIdModel.typeIdStr( this.get( 'history_content_type' ), this.get( 'id' ) ) );
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

    // ........................................................................ ajax
    /**  */
    urlRoot: galaxy_config.root + 'api/histories/',

    /** full url spec. for this HDA */
    url : function(){
        return this.urlRoot + this.get( 'history_id' ) + '/contents/'
             + this.get('history_content_type') + 's/' + this.get( 'id' );
    },

    /** save this HDA, _Mark_ing it as deleted (just a flag) */
    'delete' : function _delete( options ){
        if( this.get( 'deleted' ) ){ return jQuery.when(); }
        return this.save( { deleted: true }, options );
    },
    /** save this HDA, _Mark_ing it as undeleted */
    undelete : function _undelete( options ){
        if( !this.get( 'deleted' ) || this.get( 'purged' ) ){ return jQuery.when(); }
        return this.save( { deleted: false }, options );
    },

    /** save this HDA as not visible */
    hide : function _hide( options ){
        if( !this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: false }, options );
    },
    /** save this HDA as visible */
    unhide : function _uhide( options ){
        if( this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: true }, options );
    },

    // ........................................................................ searching
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
});

/** create a type + id string for use in mixed collections */
HistoryContent.typeIdStr = function _typeId( type, id ){
    return [ type, id ].join( '-' );
};


//==============================================================================
return {
    HistoryContent : HistoryContent
};});
