define("mvc/dataset/dataset-model", ["exports", "mvc/dataset/states", "mvc/base-mvc", "utils/localization"], function(exports, _states, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _states2 = _interopRequireDefault(_states);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "dataset";
    //==============================================================================
    var searchableMixin = _baseMvc2.default.SearchableModelMixin;
    /** @class base model for any DatasetAssociation (HDAs, LDDAs, DatasetCollectionDAs).
     *      No knowledge of what type (HDA/LDDA/DCDA) should be needed here.
     *  The DA's are made searchable (by attribute) by mixing in SearchableModelMixin.
     */
    var DatasetAssociation = Backbone.Model.extend(_baseMvc2.default.LoggableMixin).extend(_baseMvc2.default.mixin(searchableMixin,
        /** @lends DatasetAssociation.prototype */
        {
            _logNamespace: logNamespace,

            /** default attributes for a model */
            defaults: {
                state: _states2.default.NEW,
                deleted: false,
                purged: false,
                name: "(unnamed dataset)",
                accessible: true,
                // sniffed datatype (sam, tabular, bed, etc.)
                data_type: "",
                file_ext: "",
                file_size: 0,

                // array of associated file types (eg. [ 'bam_index', ... ])
                meta_files: [],

                misc_blurb: "",
                misc_info: "",

                tags: []
                // do NOT default on annotation, as this default is valid and will be passed on 'save'
                //  which is incorrect behavior when the model is only partially fetched (annos are not passed in summary data)
                //annotation          : ''
            },

            /** instance vars and listeners */
            initialize: function initialize(attributes, options) {
                this.debug(this + "(Dataset).initialize", attributes, options);

                //!! this state is not in trans.app.model.Dataset.states - set it here -
                if (!this.get("accessible")) {
                    this.set("state", _states2.default.NOT_VIEWABLE);
                }

                /** Datasets rely/use some web controllers - have the model generate those URLs on startup */
                this.urls = this._generateUrls();

                this._setUpListeners();
            },

            /** returns misc. web urls for rendering things like re-run, display, etc. */
            _generateUrls: function _generateUrls() {
                var id = this.get("id");
                if (!id) {
                    return {};
                }
                var urls = {
                    purge: "datasets/" + id + "/purge_async",
                    display: "datasets/" + id + "/display/?preview=True",
                    edit: "datasets/edit?dataset_id=" + id,
                    download: "datasets/" + id + "/display" + this._downloadQueryParameters(),
                    report_error: "dataset/errors?id=" + id,
                    rerun: "tool_runner/rerun?id=" + id,
                    show_params: "datasets/" + id + "/show_params",
                    visualization: "visualization",
                    meta_download: "dataset/get_metadata_file?hda_id=" + id + "&metadata_name="
                };
                _.each(urls, function(value, key) {
                    urls[key] = Galaxy.root + value;
                });
                this.urls = urls;
                return urls;
            },

            _downloadQueryParameters: function _downloadQueryParameters() {
                return "?to_ext=" + this.get("file_ext");
            },

            /** set up any event listeners
             *  event: state:ready  fired when this DA moves into/is already in a ready state
             */
            _setUpListeners: function _setUpListeners() {
                // if the state has changed and the new state is a ready state, fire an event
                this.on("change:state", function(currModel, newState) {
                    this.log(this + " has changed state:", currModel, newState);
                    if (this.inReadyState()) {
                        this.trigger("state:ready", currModel, newState, this.previous("state"));
                    }
                });
                // the download url (currently) relies on having a correct file extension
                this.on("change:id change:file_ext", function(currModel) {
                    this._generateUrls();
                });
            },

            // ........................................................................ common queries
            /** override to add urls */
            toJSON: function toJSON() {
                var json = Backbone.Model.prototype.toJSON.call(this);
                //console.warn( 'returning json?' );
                //return json;
                return _.extend(json, {
                    urls: this.urls
                });
            },

            /** Is this dataset deleted or purged? */
            isDeletedOrPurged: function isDeletedOrPurged() {
                return this.get("deleted") || this.get("purged");
            },

            /** Is this dataset in a 'ready' state; where 'Ready' states are states where no
             *      processing (for the ds) is left to do on the server.
             */
            inReadyState: function inReadyState() {
                var ready = _.contains(_states2.default.READY_STATES, this.get("state"));
                return this.isDeletedOrPurged() || ready;
            },

            /** Does this model already contain detailed data (as opposed to just summary level data)? */
            hasDetails: function hasDetails() {
                // if it's inaccessible assume it has everything it needs
                if (!this.get("accessible")) {
                    return true;
                }
                return this.has("annotation");
            },

            /** Convenience function to match dataset.has_data. */
            hasData: function hasData() {
                return this.get("file_size") > 0;
            },

            // ........................................................................ ajax
            fetch: function fetch(options) {
                var dataset = this;
                return Backbone.Model.prototype.fetch.call(this, options).always(function() {
                    dataset._generateUrls();
                });
            },

            /** override to use actual Dates objects for create/update times */
            parse: function parse(response, options) {
                var parsed = Backbone.Model.prototype.parse.call(this, response, options);
                if (parsed.create_time) {
                    parsed.create_time = new Date(parsed.create_time);
                }
                if (parsed.update_time) {
                    parsed.update_time = new Date(parsed.update_time);
                }
                return parsed;
            },

            /** override to wait by default */
            save: function save(attrs, options) {
                options = options || {};
                options.wait = _.isUndefined(options.wait) ? true : options.wait;
                return Backbone.Model.prototype.save.call(this, attrs, options);
            },

            //NOTE: subclasses of DA's will need to implement url and urlRoot in order to have these work properly
            /** save this dataset, _Mark_ing it as deleted (just a flag) */
            delete: function _delete(options) {
                if (this.get("deleted")) {
                    return jQuery.when();
                }
                return this.save({
                    deleted: true
                }, options);
            },
            /** save this dataset, _Mark_ing it as undeleted */
            undelete: function undelete(options) {
                if (!this.get("deleted") || this.get("purged")) {
                    return jQuery.when();
                }
                return this.save({
                    deleted: false
                }, options);
            },

            /** remove the file behind this dataset from the filesystem (if permitted) */
            purge: function _purge(options) {
                //TODO: use, override model.destroy, HDA.delete({ purge: true })
                if (this.get("purged")) {
                    return jQuery.when();
                }
                options = options || {};
                options.url = this.urls.purge;

                //TODO: ideally this would be a DELETE call to the api
                //  using purge async for now
                var hda = this;

                var xhr = jQuery.ajax(options);
                xhr.done(function(message, status, responseObj) {
                    hda.set({
                        deleted: true,
                        purged: true
                    });
                });
                xhr.fail(function(xhr, status, message) {
                    // Exception messages are hidden within error page including:  '...not allowed in this Galaxy instance.'
                    // unbury and re-add to xhr
                    var error = (0, _localization2.default)("Unable to purge dataset");
                    var messageBuriedInUnfortunatelyFormattedError = "Removal of datasets by users " + "is not allowed in this Galaxy instance";
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        error = xhr.responseJSON.error;
                    } else if (xhr.responseText.indexOf(messageBuriedInUnfortunatelyFormattedError) !== -1) {
                        error = messageBuriedInUnfortunatelyFormattedError;
                    }
                    xhr.responseText = error;
                    hda.trigger("error", hda, xhr, options, (0, _localization2.default)(error), {
                        error: error
                    });
                });
                return xhr;
            },

            // ........................................................................ searching
            /** what attributes of an HDA will be used in a text search */
            searchAttributes: ["name", "file_ext", "genome_build", "misc_blurb", "misc_info", "annotation", "tags"],

            /** our attr keys don't often match the labels we display to the user - so, when using
             *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
             *      following attr keys.
             */
            searchAliases: {
                title: "name",
                format: "file_ext",
                database: "genome_build",
                blurb: "misc_blurb",
                description: "misc_blurb",
                info: "misc_info",
                tag: "tags"
            },

            // ........................................................................ misc
            /** String representation */
            toString: function toString() {
                var nameAndId = this.get("id") || "";
                if (this.get("name")) {
                    nameAndId = "\"" + this.get("name") + "\"," + nameAndId;
                }
                return "Dataset(" + nameAndId + ")";
            }
        }));

    //==============================================================================
    /** @class Backbone collection for dataset associations.
     */
    var DatasetAssociationCollection = Backbone.Collection.extend(_baseMvc2.default.LoggableMixin).extend(
        /** @lends HistoryContents.prototype */
        {
            _logNamespace: logNamespace,

            model: DatasetAssociation,

            /** root api url */
            urlRoot: Galaxy.root + "api/datasets",

            /** url fn */
            url: function url() {
                return this.urlRoot;
            },

            // ........................................................................ common queries
            /** Get the ids of every item in this collection
             *  @returns array of encoded ids
             */
            ids: function ids() {
                return this.map(function(item) {
                    return item.get("id");
                });
            },

            /** Get contents that are not ready
             *  @returns array of content models
             */
            notReady: function notReady() {
                return this.filter(function(content) {
                    return !content.inReadyState();
                });
            },

            /** return true if any datasets don't have details */
            haveDetails: function haveDetails() {
                return this.all(function(dataset) {
                    return dataset.hasDetails();
                });
            },

            // ........................................................................ ajax
            /** using a queue, perform ajaxFn on each of the models in this collection */
            ajaxQueue: function ajaxQueue(ajaxFn, options) {
                var deferred = jQuery.Deferred();
                var startingLength = this.length;
                var responses = [];

                if (!startingLength) {
                    deferred.resolve([]);
                    return deferred;
                }

                // use reverse order (stylistic choice)
                var ajaxFns = this.chain().reverse().map(function(dataset, i) {
                    return function() {
                        var xhr = ajaxFn.call(dataset, options);
                        // if successful, notify using the deferred to allow tracking progress
                        xhr.done(function(response) {
                            deferred.notify({
                                curr: i,
                                total: startingLength,
                                response: response,
                                model: dataset
                            });
                        });
                        // (regardless of previous error or success) if not last ajax call, shift and call the next
                        //  if last fn, resolve deferred
                        xhr.always(function(response) {
                            responses.push(response);
                            if (ajaxFns.length) {
                                ajaxFns.shift()();
                            } else {
                                deferred.resolve(responses);
                            }
                        });
                    };
                }).value();
                // start the queue
                ajaxFns.shift()();

                return deferred;
            },

            // ........................................................................ sorting/filtering
            /** return a new collection of datasets whose attributes contain the substring matchesWhat */
            matches: function matches(matchesWhat) {
                return this.filter(function(dataset) {
                    return dataset.matches(matchesWhat);
                });
            },

            /** String representation. */
            toString: function toString() {
                return ["DatasetAssociationCollection(", this.length, ")"].join("");
            }
        });

    //==============================================================================
    exports.default = {
        DatasetAssociation: DatasetAssociation,
        DatasetAssociationCollection: DatasetAssociationCollection
    };
});
//# sourceMappingURL=../../../maps/mvc/dataset/dataset-model.js.map
