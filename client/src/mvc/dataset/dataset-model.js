import _ from "underscore";
import jQuery from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import STATES from "mvc/dataset/states";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";
import TAB_UPDATES from "mvc/user/tab-updates";

var logNamespace = "dataset";
var hiddenupdates = 1;
//==============================================================================
var searchableMixin = BASE_MVC.SearchableModelMixin;
/** @class base model for any DatasetAssociation (HDAs, LDDAs, DatasetCollectionDAs).
 *      No knowledge of what type (HDA/LDDA/DCDA) should be needed here.
 *  The DA's are made searchable (by attribute) by mixing in SearchableModelMixin.
 */
var DatasetAssociation = Backbone.Model.extend(BASE_MVC.LoggableMixin).extend(
    BASE_MVC.mixin(
        searchableMixin,
        /** @lends DatasetAssociation.prototype */ {
            _logNamespace: logNamespace,

            /** default attributes for a model */
            defaults: {
                state: STATES.NEW,
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

                tags: [],
                // do NOT default on annotation, as this default is valid and will be passed on 'save'
                //  which is incorrect behavior when the model is only partially fetched (annos are not passed in summary data)
                //annotation          : ''
            },

            /** instance vars and listeners */
            initialize: function (attributes, options) {
                this.debug(`${this}(Dataset).initialize`, attributes, options);

                //!! this state is not in trans.app.model.Dataset.states - set it here -
                if (!this.get("accessible")) {
                    this.set("state", STATES.NOT_VIEWABLE);
                }

                /** Datasets rely/use some web controllers - have the model generate those URLs on startup */
                this.urls = this._generateUrls();

                this._setUpListeners();
            },

            _getDatasetId: function () {
                return this.get("id");
            },

            /** returns misc. web urls for rendering things like re-run, display, etc. */
            _generateUrls: function () {
                const id = this._getDatasetId();
                if (!id) {
                    return {};
                }
                var urls = {
                    purge: `datasets/${id}/purge_async`,
                    display: `datasets/${id}/display/?preview=True`,
                    edit: `datasets/edit?dataset_id=${id}`,
                    download: `api/datasets/${id}/display${this._downloadQueryParameters()}`,
                    report_error: `dataset/errors?id=${id}`,
                    rerun: `tool_runner/rerun?id=${id}`,
                    show_params: `datasets/${id}/details`,
                    visualization: "visualization",
                    meta_download: `dataset/get_metadata_file?hda_id=${id}&metadata_name=`,
                };
                _.each(urls, (value, key) => {
                    urls[key] = getAppRoot() + value;
                });
                this.urls = urls;
                return urls;
            },

            _downloadQueryParameters: function () {
                return `?to_ext=${this.get("file_ext")}`;
            },

            /** set up any event listeners
             *  event: state:ready  fired when this DA moves into/is already in a ready state
             */
            _setUpListeners: function () {
                // if the state has changed and the new state is a ready state, fire an event
                this.on("change:state", function (currModel, newState) {
                    this.log(`${this} has changed state:`, currModel, newState);
                    if (this.inReadyState()) {
                        this.trigger("state:ready", currModel, newState, this.previous("state"));
                        if (newState != "discarded") {
                            if (newState === "ok") {
                                // If Notifications are supported, send one.
                                if (window.Notification) {
                                    new Notification(`Job complete: ${this.get("name")}`, {
                                        icon: "static/favicon.ico",
                                    });
                                }
                                if (TAB_UPDATES.is_hidden()) {
                                    TAB_UPDATES.hidden_count(hiddenupdates);
                                    hiddenupdates++;
                                }
                            } else if (newState == "error") {
                                // If Notifications are supported, send one.
                                if (window.Notification) {
                                    new Notification(`Job failure: ${this.get("name")}`, {
                                        icon: "static/erricon.ico",
                                    });
                                    if (TAB_UPDATES.is_hidden() && Notification.permission == "granted") {
                                        TAB_UPDATES.change_favicon("static/erricon.ico");
                                    }
                                }
                            }
                        }
                    }
                });
                // the download url (currently) relies on having a correct file extension
                this.on("change:id change:file_ext", function (currModel) {
                    this._generateUrls();
                });
            },

            // ........................................................................ common queries
            /** override to add urls */
            toJSON: function () {
                var json = Backbone.Model.prototype.toJSON.call(this);
                //console.warn( 'returning json?' );
                //return json;
                return _.extend(json, {
                    urls: this.urls,
                });
            },

            /** Is this dataset deleted or purged? */
            isDeletedOrPurged: function () {
                return this.get("deleted") || this.get("purged");
            },

            /** Is this dataset in a 'ready' state; where 'Ready' states are states where no
             *      processing (for the ds) is left to do on the server.
             */
            inReadyState: function () {
                var ready = _.contains(STATES.READY_STATES, this.get("state"));
                return this.isDeletedOrPurged() || ready;
            },

            /** Does this model already contain detailed data (as opposed to just summary level data)? */
            hasDetails: function () {
                // if it's inaccessible assume it has everything it needs
                if (!this.get("accessible")) {
                    return true;
                }
                return this.has("annotation");
            },

            /** Convenience function to match dataset.has_data. */
            hasData: function () {
                return this.get("file_size") > 0;
            },

            // ........................................................................ ajax
            fetch: function (options) {
                var dataset = this;
                return Backbone.Model.prototype.fetch.call(this, options).always(() => {
                    dataset._generateUrls();
                });
            },

            /** override to use actual Dates objects for create/update times */
            parse: function (response, options) {
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
            save: function (attrs, options) {
                options = options || {};
                options.wait = _.isUndefined(options.wait) ? true : options.wait;
                return Backbone.Model.prototype.save.call(this, attrs, options);
            },

            //NOTE: subclasses of DA's will need to implement url and urlRoot in order to have these work properly
            /** save this dataset, _Mark_ing it as deleted (just a flag) */
            delete: function (options) {
                if (this.get("deleted")) {
                    return jQuery.when();
                }
                return this.save({ deleted: true }, options);
            },
            /** save this dataset, _Mark_ing it as undeleted */
            undelete: function (options) {
                if (!this.get("deleted") || this.get("purged")) {
                    return jQuery.when();
                }
                return this.save({ deleted: false }, options);
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
                xhr.done((message, status, responseObj) => {
                    hda.set({ deleted: true, purged: true });
                });
                xhr.fail((xhr, status, message) => {
                    // Exception messages are hidden within error page including:  '...not allowed in this Galaxy instance.'
                    // unbury and re-add to xhr
                    var error = _l("Unable to purge dataset");
                    var messageBuriedInUnfortunatelyFormattedError =
                        "Removal of datasets by users " + "is not allowed in this Galaxy instance";
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        error = xhr.responseJSON.error;
                    } else if (xhr.responseText.indexOf(messageBuriedInUnfortunatelyFormattedError) !== -1) {
                        error = messageBuriedInUnfortunatelyFormattedError;
                    }
                    xhr.responseText = error;
                    hda.trigger("error", hda, xhr, options, _l(error), {
                        error: error,
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
                tag: "tags",
            },

            // ........................................................................ misc
            /** String representation */
            toString: function () {
                var nameAndId = this.get("id") || "";
                if (this.get("name")) {
                    nameAndId = `"${this.get("name")}",${nameAndId}`;
                }
                return `Dataset(${nameAndId})`;
            },
        }
    )
);

//==============================================================================
/** @class Backbone collection for dataset associations.
 */
var DatasetAssociationCollection = Backbone.Collection.extend(BASE_MVC.LoggableMixin).extend(
    /** @lends HistoryContents.prototype */ {
        _logNamespace: logNamespace,

        model: DatasetAssociation,

        /** root api url */
        urlRoot: `${getAppRoot()}api/datasets`,

        /** url fn */
        url: function () {
            return this.urlRoot;
        },

        // ........................................................................ common queries
        /** Get the ids of every item in this collection
         *  @returns array of encoded ids
         */
        ids: function () {
            return this.map((item) => item.get("id"));
        },

        /** Get contents that are not ready
         *  @returns array of content models
         */
        notReady: function () {
            return this.filter((content) => !content.inReadyState());
        },

        /** return true if any datasets don't have details */
        haveDetails: function () {
            return this.all((dataset) => dataset.hasDetails());
        },

        // ........................................................................ ajax
        /** using a queue, perform ajaxFn on each of the models in this collection */
        ajaxQueue: function (ajaxFn, options) {
            var deferred = jQuery.Deferred();
            var startingLength = this.length;
            var responses = [];

            if (!startingLength) {
                deferred.resolve([]);
                return deferred;
            }

            // use reverse order (stylistic choice)
            var ajaxFns = this.chain()
                .reverse()
                .map((dataset, i) => () => {
                    var xhr = ajaxFn.call(dataset, options);
                    // if successful, notify using the deferred to allow tracking progress
                    xhr.done((response) => {
                        deferred.notify({
                            curr: i,
                            total: startingLength,
                            response: response,
                            model: dataset,
                        });
                    });
                    // (regardless of previous error or success) if not last ajax call, shift and call the next
                    //  if last fn, resolve deferred
                    xhr.always((response) => {
                        responses.push(response);
                        if (ajaxFns.length) {
                            ajaxFns.shift()();
                        } else {
                            deferred.resolve(responses);
                        }
                    });
                })
                .value();
            // start the queue
            ajaxFns.shift()();

            return deferred;
        },

        // ........................................................................ sorting/filtering
        /** return a new collection of datasets whose attributes contain the substring matchesWhat */
        matches: function (matchesWhat) {
            return this.filter((dataset) => dataset.matches(matchesWhat));
        },

        /** String representation. */
        toString: function () {
            return ["DatasetAssociationCollection(", this.length, ")"].join("");
        },
    }
);

window.addEventListener("focus", function () {
    const testing = document.getElementById("tabicon");
    if (testing && testing.href.search("erricon") != -1) {
        TAB_UPDATES.change_favicon("static/favicon.ico");
    }
    document.title = "Galaxy";
    hiddenupdates = 1;
});
//==============================================================================
export default {
    DatasetAssociation: DatasetAssociation,
    DatasetAssociationCollection: DatasetAssociationCollection,
};
