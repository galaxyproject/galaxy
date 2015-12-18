define([
    "libs/bibtex",
    "mvc/base-mvc",
    "utils/localization"
], function( parseBibtex, baseMVC, _l ){
/* global Backbone */
// we use amd here to require, but bibtex uses a global or commonjs pattern.
// webpack will load via commonjs and plain requirejs will load as global. Check both
parseBibtex = parseBibtex || window.BibtexParser;

var logNamespace = 'citation';
//==============================================================================
/** @class model for tool citations.
 *  @name Citation
 *  @augments Backbone.Model
 */
var Citation = Backbone.Model.extend( baseMVC.LoggableMixin ).extend( {
    _logNamespace : logNamespace,

    initialize: function() {
        var bibtex = this.get( 'content' );
        var entry = parseBibtex(bibtex).entries[0];
        this.entry = entry;
        this._fields = {};
        var rawFields = entry.Fields;
        for(var key in rawFields) {
            var value = rawFields[ key ];
            var lowerKey = key.toLowerCase();
            this._fields[ lowerKey ] = value;
        }
    },
    entryType: function() {
        return this.entry.EntryType;
    },
    fields: function() {
        return this._fields;
    }
} );

//==============================================================================
/** @class Backbone collection of citations.
 */
var BaseCitationCollection = Backbone.Collection.extend( baseMVC.LoggableMixin ).extend( {
    _logNamespace : logNamespace,

    /** root api url */
    urlRoot : Galaxy.root + 'api',
    partial : true, // Assume some tools in history/workflow may not be properly annotated yet.
    model : Citation,
} );

var HistoryCitationCollection = BaseCitationCollection.extend( {
    /** complete api url */
    url : function() {
        return this.urlRoot + '/histories/' + this.history_id + '/citations';
    }
} );

var ToolCitationCollection = BaseCitationCollection.extend( {
    /** complete api url */
    url : function() {
        return this.urlRoot + '/tools/' + this.tool_id + '/citations';
    },
    partial : false, // If a tool has citations, assume they are complete.
} );


//==============================================================================
return {
    Citation : Citation,
    HistoryCitationCollection  : HistoryCitationCollection,
    ToolCitationCollection: ToolCitationCollection
};

});