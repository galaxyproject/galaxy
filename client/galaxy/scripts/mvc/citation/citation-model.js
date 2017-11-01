define(["libs/bibtexParse", "mvc/base-mvc", "utils/localization"], function(
    bibtexParse,
    baseMVC,
    _l
) {
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
                parsed = bibtexParse.toJSON(this.attributes.content);
            } catch (err) {
                this.log("Error parsing bibtex: " + err);
            }

            this._fields = {};
            this.entry = _.first(parsed);
            if (this.entry) {
                var rawFields = this.entry.entryTags;
                for (var key in rawFields) {
                    var value = rawFields[key];
                    var lowerKey = key.toLowerCase();
                    this._fields[lowerKey] = value;
                }
            }
        },
        entryType: function() {
            return this.entry ? this.entry.entryType : undefined;
        },
        fields: function() {
            return this._fields;
        }
    });

    //==============================================================================
    /** @class Backbone collection of citations.
 */
    var BaseCitationCollection = Backbone.Collection
        .extend(baseMVC.LoggableMixin)
        .extend({
            _logNamespace: logNamespace,

            /** root api url */
            urlRoot: Galaxy.root + "api",
            partial: true, // Assume some tools in history/workflow may not be properly annotated yet.
            model: Citation
        });

    var HistoryCitationCollection = BaseCitationCollection.extend({
        /** complete api url */
        url: function() {
            return (
                this.urlRoot + "/histories/" + this.history_id + "/citations"
            );
        }
    });

    var ToolCitationCollection = BaseCitationCollection.extend({
        /** complete api url */
        url: function() {
            return this.urlRoot + "/tools/" + this.tool_id + "/citations";
        },
        partial: false // If a tool has citations, assume they are complete.
    });

    //==============================================================================

    return {
        Citation: Citation,
        HistoryCitationCollection: HistoryCitationCollection,
        ToolCitationCollection: ToolCitationCollection
    };
});
