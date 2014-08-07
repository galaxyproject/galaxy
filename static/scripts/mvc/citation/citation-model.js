define([
    "mvc/base-mvc",
    "utils/localization"
], function( baseMVC, _l ){
/* global Backbone */

//==============================================================================
/** @class model for tool citations.
 *  @name Citation
 *
 *  @augments Backbone.Model
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var Citation = Backbone.Model.extend( baseMVC.LoggableMixin ).extend( {
    initialize: function( ) {
        var bibtex = this.attributes.content;
        var entry = new BibtexParser(bibtex).entries[0];
        this.entry = entry;
        this._fields = {};
        var rawFields = entry.Fields;
        for(key in rawFields) {
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
 *
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var BaseCitationCollection = Backbone.Collection.extend( baseMVC.LoggableMixin ).extend( {
    /** root api url */
    urlRoot : galaxy_config.root + 'api',
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