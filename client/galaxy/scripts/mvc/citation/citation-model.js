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
var Citation = Backbone.Model.extend( baseMVC.LoggableMixin ).extend({
    initialize: function() {
        var bibtex = this.attributes.content;
        var parsed = BibtexParser( bibtex );
        // bibtex returns successfully parsed in .entries and any parsing errors in .errors
        if( parsed.errors.length ){
            // the gen. form of these errors seems to be [ line, col, char, error message ]
            var errors = parsed.errors.reduce( function( all, current ){ return all + '; ' + current; });
            // throw new Error( 'Error parsing bibtex: ' + errors );
            this.log( 'Error parsing bibtex: ' + errors );
        }

        this._fields = {};
        this.entry = _.first( parsed.entries );
        if( this.entry ){
            var rawFields = this.entry.Fields;
            for( var key in rawFields ){
                var value = rawFields[ key ];
                var lowerKey = key.toLowerCase();
                this._fields[ lowerKey ] = value;
            }
        }
    },
    entryType: function() {
        return this.entry? this.entry.EntryType : undefined;
    },
    fields: function() {
        return this._fields;
    }
});


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