import * as parseBibtex from "libs/bibtex";
import baseMVC from "mvc/base-mvc";
import _l from "utils/localization";

/* global Backbone */

_.extend(parseBibtex.ENTRY_TYPES_, {
    online: 998, // Galaxy MOD: Handle @online entries for preprints.
    data: 999 // Galaxy MOD: Handle @data citations coming from figshare.
});

var logNamespace = "citation";
//==============================================================================
/** @class model for tool citations.
 *  @name Citation
 *  @augments Backbone.Model
 */
var Citation = Backbone.Model.extend(baseMVC.LoggableMixin).extend({
    _logNamespace: logNamespace,

    defaults: {
        content: ""
    },

    initialize: function() {
        var parsed;
        try {
            // TODO: to model.parse/.validate
            parsed = parseBibtex(this.attributes.content);
        } catch (err) {
            return;
        }
        // bibtex returns successfully parsed in .entries and any parsing errors in .errors
        if (parsed.errors.length) {
            // the gen. form of these errors seems to be [ line, col, char, error message ]
            var errors = parsed.errors.reduce((all, current) => `${all}; ${current}`);
            // throw new Error( 'Error parsing bibtex: ' + errors );
            this.log(`Error parsing bibtex: ${errors}`);
        }

        this._fields = {};
        this.entry = _.first(parsed.entries);
        if (this.entry) {
            var rawFields = this.entry.Fields;
            for (var key in rawFields) {
                var value = rawFields[key];
                var lowerKey = key.toLowerCase();
                this._fields[lowerKey] = value;
            }
        }
    },
    entryType: function() {
        return this.entry ? this.entry.EntryType : undefined;
    },
    fields: function() {
        return this._fields;
    }
});

//==============================================================================
/** @class Backbone collection of citations.
 */
var BaseCitationCollection = Backbone.Collection.extend(baseMVC.LoggableMixin).extend({
    _logNamespace: logNamespace,

    /** root api url */
    urlRoot: `${Galaxy.root}api`,
    partial: true, // Assume some tools in history/workflow may not be properly annotated yet.
    model: Citation
});

var HistoryCitationCollection = BaseCitationCollection.extend({
    /** complete api url */
    url: function() {
        return `${this.urlRoot}/histories/${this.history_id}/citations`;
    }
});

var ToolCitationCollection = BaseCitationCollection.extend({
    /** complete api url */
    url: function() {
        return `${this.urlRoot}/tools/${this.tool_id}/citations`;
    },
    partial: false // If a tool has citations, assume they are complete.
});

//==============================================================================

export default {
    Citation: Citation,
    HistoryCitationCollection: HistoryCitationCollection,
    ToolCitationCollection: ToolCitationCollection
};
