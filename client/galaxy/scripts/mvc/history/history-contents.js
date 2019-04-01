import _ from "underscore";
import jQuery from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import CONTROLLED_FETCH_COLLECTION from "mvc/base/controlled-fetch-collection";
import HDA_MODEL from "mvc/history/hda-model";
import HDCA_MODEL from "mvc/history/hdca-model";
import HISTORY_PREFS from "mvc/history/history-preferences";
import JOB_STATES_MODEL from "mvc/history/job-states-model";
import BASE_MVC from "mvc/base-mvc";
import AJAX_QUEUE from "utils/ajax-queue";

const limitPerPageDefault = window.localStorage.getItem("historyContentsLimitPerPageDefault") || 500;

//==============================================================================
var _super = CONTROLLED_FETCH_COLLECTION.PaginatedCollection;
/** @class Backbone collection for history content.
 *      NOTE: history content seems like a dataset collection, but differs in that it is mixed:
 *          each element can be either an HDA (dataset) or a DatasetCollection and co-exist on
 *          the same level.
 *      Dataset collections on the other hand are not mixed and (so far) can only contain either
 *          HDAs or child dataset collections on one level.
 *      This is why this does not inherit from any of the DatasetCollections (currently).
 */
export var HistoryContents = _super.extend(BASE_MVC.LoggableMixin).extend({
    _logNamespace: "history",

    // ........................................................................ set up
    limitPerPage: limitPerPageDefault,

    /** @type {Integer} how many contents per call to fetch when using progressivelyFetchDetails */
    limitPerProgressiveFetch: limitPerPageDefault,

    /** @type {String} order used here and when fetching from server */
    order: "hid",

    /** complete api url */
    url: function() {
        return `${this.urlRoot}/${this.historyId}/contents`;
    },

    /** Set up */
    initialize: function(models, options) {
        this.on({
            "sync add": this.trackJobStates
        });

        options = options || {};
        this.urlRoot = `${getAppRoot()}api/histories`;
        _super.prototype.initialize.call(this, models, options);

        this.history = options.history || null;
        this.setHistoryId(options.historyId || null);
        /** @type {Boolean} does this collection contain and fetch deleted elements */
        this.includeDeleted = options.includeDeleted || this.includeDeleted;
        /** @type {Boolean} does this collection contain and fetch non-visible elements */
        this.includeHidden = options.includeHidden || this.includeHidden;

        // backbonejs uses collection.model.prototype.idAttribute to determine if a model is *already* in a collection
        //  and either merged or replaced. In this case, our 'model' is a function so we need to add idAttribute
        //  manually here - if we don't, contents will not merge but be replaced/swapped.
        this.model.prototype.idAttribute = "type_id";
    },

    trackJobStates: function() {
        this.each(historyContent => {
            if (historyContent.has("job_states_summary")) {
                return;
            }

            if (historyContent.attributes.history_content_type === "dataset_collection") {
                var jobSourceType = historyContent.attributes.job_source_type;
                var jobSourceId = historyContent.attributes.job_source_id;
                if (jobSourceType && this.jobStateSummariesCollection) {
                    this.jobStateSummariesCollection.add({
                        id: jobSourceId,
                        model: jobSourceType,
                        history_id: this.history_id,
                        collection_id: historyContent.attributes.id
                    });
                    var jobStatesSummary = this.jobStateSummariesCollection.get(jobSourceId);
                    historyContent.jobStatesSummary = jobStatesSummary;
                }
            }
        });
    },

    // ........................................................................ composite collection
    /** since history content is a mix, override model fn into a factory, creating based on history_content_type */
    model: function(attrs, options) {
        if (attrs.history_content_type === "dataset") {
            return new HDA_MODEL.HistoryDatasetAssociation(attrs, options);
        } else if (attrs.history_content_type === "dataset_collection") {
            return new HDCA_MODEL.HistoryDatasetCollection(attrs, options);
        } else {
            return {
                validationError: `Unknown history_content_type: ${attrs.history_content_type}`
            };
        }
    },

    stopPolling: function() {
        if (this.jobStateSummariesCollection) {
            this.jobStateSummariesCollection.active = false;
            this.jobStateSummariesCollection.clearUpdateTimeout();
        }
    },

    setHistoryId: function(newId) {
        this.stopPolling();
        this.historyId = newId;
        if (newId) {
            // If actually reflecting a history - setup storage and monitor jobs.

            this._setUpWebStorage();

            this.jobStateSummariesCollection = new JOB_STATES_MODEL.JobStatesSummaryCollection();
            this.jobStateSummariesCollection.historyId = newId;
            this.jobStateSummariesCollection.monitor();
        }
    },

    /** Set up client side storage. Currently PersistanStorage keyed under 'history:<id>' */
    _setUpWebStorage: function(initialSettings) {
        // TODO: use initialSettings
        this.storage = new HISTORY_PREFS.HistoryPrefs({
            id: HISTORY_PREFS.HistoryPrefs.historyStorageKey(this.historyId)
        });
        this.trigger("new-storage", this.storage, this);

        this.on({
            "include-deleted": function(newVal) {
                this.storage.includeDeleted(newVal);
            },
            "include-hidden": function(newVal) {
                this.storage.includeHidden(newVal);
            }
        });

        this.includeDeleted = this.storage.includeDeleted() || false;
        this.includeHidden = this.storage.includeHidden() || false;
        return this;
    },

    // ........................................................................ common queries
    /** @type {Object} map of collection available sorting orders containing comparator fns */
    comparators: _.extend(_.clone(_super.prototype.comparators), {
        name: BASE_MVC.buildComparator("name", { ascending: true }),
        "name-dsc": BASE_MVC.buildComparator("name", {
            ascending: false
        }),
        hid: BASE_MVC.buildComparator("hid", { ascending: false }),
        "hid-asc": BASE_MVC.buildComparator("hid", { ascending: true })
    }),

    /** Get every model in this collection not in a 'ready' state (running). */
    running: function() {
        return this.filter(c => !c.inReadyState());
    },

    /** return contents that are not ready and not deleted/hidden */
    runningAndActive: function() {
        return this.filter(
            c =>
                !c.inReadyState() &&
                c.get("visible") &&
                // TODO: deletedOrPurged?
                !c.get("deleted")
        );
    },

    /** Get the model with the given hid
     *  @param {Int} hid the hid to search for
     *  @returns {HistoryDatasetAssociation} the model with the given hid or undefined if not found
     */
    getByHid: function(hid) {
        // note: there *can* be more than one content with a given hid, this finds the first based on order
        return this.findWhere({ hid: hid });
    },

    /** return true if all contents have details */
    haveDetails: function() {
        return this.all(c => c.hasDetails());
    },

    // ........................................................................ hidden / deleted
    /** return a new contents collection of only hidden items */
    hidden: function() {
        return this.filter(c => c.hidden());
    },

    /** return a new contents collection of only hidden items */
    deleted: function() {
        return this.filter(c => c.get("deleted"));
    },

    /** return a new contents collection of only hidden items */
    visibleAndUndeleted: function() {
        return this.filter(
            c =>
                c.get("visible") &&
                // TODO: deletedOrPurged?
                !c.get("deleted")
        );
    },

    /** create a setter in order to publish the change */
    setIncludeDeleted: function(setting, options) {
        if (_.isBoolean(setting) && setting !== this.includeDeleted) {
            this.includeDeleted = setting;
            if (_.result(options, "silent")) {
                return;
            }
            this.trigger("include-deleted", setting, this);
        }
    },

    /** create a setter in order to publish the change */
    setIncludeHidden: function(setting, options) {
        if (_.isBoolean(setting) && setting !== this.includeHidden) {
            this.includeHidden = setting;
            options = options || {};
            if (_.result(options, "silent")) {
                return;
            }
            this.trigger("include-hidden", setting, this);
        }
    },

    // ........................................................................ ajax
    // ............ controlled fetch collection
    /** override to get expanded ids from sessionStorage and pass to API as details */
    fetch: function(options) {
        options = options || {};
        if (this.historyId && !options.details) {
            var prefs = HISTORY_PREFS.HistoryPrefs.get(this.historyId).toJSON();
            if (!_.isEmpty(prefs.expandedIds)) {
                options.details = _.values(prefs.expandedIds).join(",");
            }
        }
        return _super.prototype.fetch.call(this, options);
    },

    // ............. ControlledFetch stuff
    /** override to include the API versioning flag */
    _buildFetchData: function(options) {
        return _.extend(_super.prototype._buildFetchData.call(this, options), {
            v: "dev"
        });
    },

    /** Extend to include details and version */
    _fetchParams: _super.prototype._fetchParams.concat([
        // TODO: remove (the need for) both
        /** version */
        "v",
        /** dataset ids to get full details of */
        "details"
    ]),

    /** override to add deleted/hidden filters */
    _buildFetchFilters: function(options) {
        var superFilters = _super.prototype._buildFetchFilters.call(this, options) || {};
        var filters = {};
        if (!this.includeDeleted) {
            filters.deleted = false;
            filters.purged = false;
        }
        if (!this.includeHidden) {
            filters.visible = true;
        }
        return _.defaults(superFilters, filters);
    },

    // ............ paginated collection
    getTotalItemCount: function() {
        return this.history.contentsShown();
    },

    // ............ history contents specific ajax
    /** override to filter requested contents to those updated after the Date 'since' */
    fetchUpdated: function(since, options) {
        if (since) {
            options = options || { filters: {} };
            options.remove = false;
            options.filters = {
                "update_time-ge": since.toISOString(),
                // workflows will produce hidden datasets (non-output datasets) that still
                // need to be updated in the collection or they'll update forever
                // we can remove the default visible filter by using an 'empty' value
                visible: ""
            };
        }
        return this.fetch(options);
    },

    /** fetch all the deleted==true contents of this collection */
    fetchDeleted: function(options) {
        options = options || {};
        options.filters = _.extend(options.filters, {
            // all deleted, purged or not
            deleted: true,
            purged: undefined
        });
        options.remove = false;

        this.trigger("fetching-deleted", this);
        return this.fetch(options).always(() => {
            this.trigger("fetching-deleted-done", this);
        });
    },

    /** fetch all the visible==false contents of this collection */
    fetchHidden: function(options) {
        options = options || {};
        options.filters = _.extend(options.filters, {
            visible: false
        });
        options.remove = false;

        this.trigger("fetching-hidden", this);
        return this.fetch(options).always(() => {
            this.trigger("fetching-hidden-done", this);
        });
    },

    /** fetch detailed model data for all contents in this collection */
    fetchAllDetails: function(options) {
        options = options || {};
        var detailsFlag = { details: "all" };
        options.data = _.extend(options.data || {}, detailsFlag);
        return this.fetch(options);
    },

    // ............. quasi-batch ops
    // TODO: to batch
    /** helper that fetches using filterParams then calls save on each fetched using updateWhat as the save params */
    _filterAndUpdate: function(filterParams, updateWhat) {
        var idAttribute = this.model.prototype.idAttribute;
        var updateArgs = [updateWhat];

        return this.fetch({ filters: filterParams, remove: false }).then(fetched => {
            // convert filtered json array to model array
            fetched = fetched.reduce((modelArray, currJson, i) => {
                var model = this.get(currJson[idAttribute]);
                return model ? modelArray.concat(model) : modelArray;
            }, []);
            return this.ajaxQueue("save", updateArgs, fetched);
        });
    },

    /** using a queue, perform ajaxFn on each of the models in this collection */
    ajaxQueue: function(ajaxFn, args, collection) {
        collection = collection || this.models;
        return new AJAX_QUEUE.AjaxQueue(
            collection
                .slice()
                .reverse()
                .map((content, i) => {
                    var fn = _.isString(ajaxFn) ? content[ajaxFn] : ajaxFn;
                    return () => fn.apply(content, args);
                })
        ).deferred;
    },

    _recursivelyFetch: function(options, detailKeys, deferred, limit, offset) {
        offset = offset || 0;
        var _options = _.extend(_.clone(options), {
            view: "summary",
            keys: detailKeys,
            limit: limit,
            offset: offset,
            reset: offset === 0,
            remove: false
        });

        _.defer(() => {
            this.fetch
                .call(this, _options)
                .fail(deferred.reject)
                .done(response => {
                    deferred.notify(response, limit, offset);
                    if (response.length !== limit) {
                        this.allFetched = true;
                        deferred.resolve(response, limit, offset);
                    } else {
                        this._recursivelyFetch(options, detailKeys, deferred, limit, offset + limit);
                    }
                });
        });
    },

    /** fetch contents' details in batches of limitPerCall - note: only get searchable details here */
    progressivelyFetchDetails: function(options) {
        // TODO: only fetch tags and annotations if specifically requested
        options = options || {};
        let deferred = jQuery.Deferred();
        this._recursivelyFetch(
            options,
            HDA_MODEL.HistoryDatasetAssociation.prototype.searchAttributes.join(","),
            deferred,
            options.limitPerCall || this.limitPerProgressiveFetch
        );
        return deferred;
    },

    /** does some bit of JSON represent something that can be copied into this contents collection */
    isCopyable: function(contentsJSON) {
        var copyableModelClasses = ["HistoryDatasetAssociation", "HistoryDatasetCollectionAssociation"];
        return (
            _.isObject(contentsJSON) && contentsJSON.id && _.contains(copyableModelClasses, contentsJSON.model_class)
        );
    },

    /** copy an existing, accessible hda into this collection */
    copy: function(json) {
        // TODO: somehow showhorn all this into 'save'
        var id;

        var type;
        var contentType;
        if (_.isString(json)) {
            id = json;
            contentType = "hda";
            type = "dataset";
        } else {
            id = json.id;
            contentType =
                {
                    HistoryDatasetAssociation: "hda",
                    LibraryDatasetDatasetAssociation: "ldda",
                    HistoryDatasetCollectionAssociation: "hdca"
                }[json.model_class] || "hda";
            type = contentType === "hdca" ? "dataset_collection" : "dataset";
        }
        var collection = this;

        var xhr = jQuery
            .ajax(this.url(), {
                method: "POST",
                contentType: "application/json",
                data: JSON.stringify({
                    content: id,
                    source: contentType,
                    type: type
                })
            })
            .done(response => {
                collection.add([response], { parse: true });
            })
            .fail((error, status, message) => {
                collection.trigger("error", collection, xhr, {}, "Error copying contents", {
                    type: type,
                    id: id,
                    source: contentType
                });
            });

        return xhr;
    },

    /** create a new HDCA in this collection */
    createHDCA: function(elementIdentifiers, collectionType, name, hideSourceItems, copyElements, options) {
        // normally collection.create returns the new model, but we need the promise from the ajax, so we fake create
        //precondition: elementIdentifiers is an array of plain js objects
        //  in the proper form to create the collectionType
        if (copyElements === undefined) {
            copyElements = true;
        }

        var hdca = this.model({
            history_content_type: "dataset_collection",
            collection_type: collectionType,
            history_id: this.historyId,
            name: name,
            hide_source_items: hideSourceItems || false,
            copy_elements: copyElements,
            // should probably be able to just send in a bunch of json here and restruct per class
            // note: element_identifiers is now (incorrectly) an attribute
            element_identifiers: elementIdentifiers
            // do not create the model on the client until the ajax returns
        });
        return hdca.save(options);
    },

    // ........................................................................ searching
    /** return true if all contents have the searchable attributes */
    haveSearchDetails: function() {
        return (
            this.allFetched &&
            this.all((
                content // null (which is a valid returned annotation value)
            ) =>
                // will return false when using content.has( 'annotation' )
                //TODO: a bit hacky - formalize
                _.has(content.attributes, "annotation")
            )
        );
    },

    /** return a new collection of contents whose attributes contain the substring matchesWhat */
    matches: function(matchesWhat) {
        return this.filter(content => content.matches(matchesWhat));
    },

    // ........................................................................ misc
    /** In this override, copy the historyId to the clone */
    clone: function() {
        var clone = Backbone.Collection.prototype.clone.call(this);
        clone.historyId = this.historyId;
        return clone;
    },

    /** String representation. */
    toString: function() {
        return ["HistoryContents(", [this.historyId, this.length].join(), ")"].join("");
    }
});
