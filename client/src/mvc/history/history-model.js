import _ from "underscore";
import jQuery from "jquery";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import { HistoryContents } from "mvc/history/history-contents";
import CONTROLLED_FETCH_COLLECTION from "mvc/base/controlled-fetch-collection";
import UTILS from "utils/utils";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";

//==============================================================================
/** @class Model for a Galaxy history resource - both a record of user
 *      tool use and a collection of the datasets those tools produced.
 *  @name History
 *  @augments Backbone.Model
 */
export var History = Backbone.Model.extend(BASE_MVC.LoggableMixin).extend(
    BASE_MVC.mixin(
        BASE_MVC.SearchableModelMixin,
        /** @lends History.prototype */ {
            _logNamespace: "history",

            /** ms between fetches when checking running jobs/datasets for updates */
            UPDATE_DELAY: 4000,

            // values from api (may need more)
            defaults: {
                model_class: "History",
                id: null,
                name: "Unnamed History",
                state: "new",

                deleted: false,
                contents_active: {},
                contents_states: {},
            },

            contentsClass: HistoryContents,

            /** What model fields to search with */
            searchAttributes: ["name", "annotation", "tags"],

            /** Adding title and singular tag */
            searchAliases: {
                title: "name",
                tag: "tags",
            },

            // ........................................................................ set up/tear down
            /** Set up the model
             *  @param {Object} historyJSON model data for this History
             *  @param {Object} options     any extra settings including logger
             */
            initialize: function (historyJSON, options) {
                options = options || {};
                this.logger = options.logger || null;
                this.log(`${this}.initialize:`, historyJSON, options);

                this.urlRoot = `${getAppRoot()}api/histories`;
                /** HistoryContents collection of the HDAs contained in this history. */
                this.contents = new this.contentsClass([], {
                    history: this,
                    historyId: this.get("id"),
                    order: options.order,
                });

                this._setUpListeners();
                this._setUpCollectionListeners();

                /** cached timeout id for the dataset updater */
                this.updateTimeoutId = null;
            },

            /** set up any event listeners for this history including those to the contained HDAs
             *  events: error:contents  if an error occurred with the contents collection
             */
            _setUpListeners: function () {
                // if the model's id changes ('current' or null -> an actual id), update the contents history_id
                return this.on({
                    error: function (model, xhr, options, msg, details) {
                        this.clearUpdateTimeout();
                    },
                    "change:id": function (model, newId) {
                        if (this.contents) {
                            this.contents.historyId = newId;
                        }
                    },
                });
            },

            /** event handlers for the contents submodels */
            _setUpCollectionListeners: function () {
                if (!this.contents) {
                    return this;
                }
                // bubble up errors
                return this.listenTo(this.contents, {
                    error: function () {
                        this.trigger.apply(this, jQuery.makeArray(arguments));
                    },
                });
            },

            // ........................................................................ derived attributes
            /**  */
            contentsShown: function () {
                var contentsActive = this.get("contents_active");
                var shown = contentsActive.active || 0;
                shown += this.contents.includeDeleted ? contentsActive.deleted : 0;
                shown += this.contents.includeHidden ? contentsActive.hidden : 0;
                return shown;
            },

            /** convert size in bytes to a more human readable version */
            nice_size: function () {
                var size = this.get("size");
                return size ? UTILS.bytesToString(size, true, 2) : _l("(empty)");
            },

            /** override to add nice_size */
            toJSON: function () {
                return _.extend(Backbone.Model.prototype.toJSON.call(this), {
                    nice_size: this.nice_size(),
                });
            },

            /** override to allow getting nice_size */
            get: function (key) {
                if (key === "nice_size") {
                    return this.nice_size();
                }
                return Backbone.Model.prototype.get.apply(this, arguments);
            },

            // ........................................................................ common queries
            /** T/F is this history owned by the current user (Galaxy.user)
             *      Note: that this will return false for an anon user even if the history is theirs.
             */
            ownedByCurrUser: function () {
                const Galaxy = getGalaxyInstance();
                // no currUser
                if (!Galaxy || !Galaxy.user) {
                    return false;
                }
                // user is anon or history isn't owned
                if (Galaxy.user.isAnonymous() || Galaxy.user.id !== this.get("user_id")) {
                    return false;
                }
                return true;
            },

            /** Return the number of running jobs assoc with this history (note: unknown === 0) */
            numOfUnfinishedJobs: function () {
                var unfinishedJobIds = this.get("non_ready_jobs");
                return unfinishedJobIds ? unfinishedJobIds.length : 0;
            },

            /** Return the number of running hda/hdcas in this history (note: unknown === 0) */
            numOfUnfinishedShownContents: function () {
                return this.contents.runningAndActive().length || 0;
            },

            // ........................................................................ updates
            _fetchContentRelatedAttributes: function () {
                var contentRelatedAttrs = ["size", "non_ready_jobs", "contents_active", "hid_counter"];
                return this.fetch({
                    data: jQuery.param({
                        keys: contentRelatedAttrs.join(","),
                    }),
                });
            },

            /** check for any changes since the last time we updated (or fetch all if ) */
            refresh: function (options) {
                // console.log( this + '.refresh' );
                options = options || {};

                // note if there was no previous update time, all summary contents will be fetched
                var lastUpdateTime = this.lastUpdateTime;
                // if we don't flip this, then a fully-fetched list will not be re-checked via fetch
                this.contents.allFetched = false;
                var fetchFn =
                    this.contents.currentPage !== 0
                        ? () => this.contents.fetchPage(this.contents.currentPage)
                        : () => this.contents.fetchUpdated(lastUpdateTime);
                // note: if there was no previous update time, all summary contents will be fetched
                return fetchFn().done((response, status, xhr) => {
                    var serverResponseDatetime;
                    try {
                        serverResponseDatetime = new Date(xhr.getResponseHeader("Date"));
                    } catch (err) {
                        console.error(err);
                    }
                    this.lastUpdateTime = serverResponseDatetime || new Date();
                    this.checkForUpdates(options);
                });
            },

            /** continuously fetch updated contents every UPDATE_DELAY ms if this history's datasets or jobs are unfinished */
            checkForUpdates: function (options) {
                // console.log( this + '.checkForUpdates' );
                options = options || {};
                var delay = this.UPDATE_DELAY;
                if (!this.id) {
                    return;
                }

                var _delayThenUpdate = () => {
                    // prevent buildup of updater timeouts by clearing previous if any, then set new and cache id
                    this.clearUpdateTimeout();
                    this.updateTimeoutId = setTimeout(() => {
                        this.refresh(options);
                    }, delay);
                };

                // if there are still datasets in the non-ready state, recurse into this function with the new time
                var nonReadyContentCount = this.numOfUnfinishedShownContents();
                // console.log( 'nonReadyContentCount:', nonReadyContentCount );
                if (nonReadyContentCount > 0) {
                    _delayThenUpdate();
                } else {
                    // no datasets are running, but currently runnning jobs may still produce new datasets
                    // see if the history has any running jobs and continue to update if so
                    // (also update the size for the user in either case)
                    this._fetchContentRelatedAttributes().done((historyData) => {
                        // console.log( 'non_ready_jobs:', historyData.non_ready_jobs );
                        if (this.numOfUnfinishedJobs() > 0) {
                            _delayThenUpdate();
                        } else {
                            // otherwise, let listeners know that all updates have stopped
                            this.trigger("ready");
                        }
                    });
                }
            },

            /** clear the timeout and the cached timeout id */
            clearUpdateTimeout: function () {
                if (this.updateTimeoutId) {
                    clearTimeout(this.updateTimeoutId);
                    this.updateTimeoutId = null;
                }
            },

            stopPolling: function () {
                this.clearUpdateTimeout();
                if (this.contents) {
                    this.contents.stopPolling();
                }
            },

            // ........................................................................ ajax
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

            /** fetch this histories data (using options) then it's contents (using contentsOptions) */
            fetchWithContents: function (options, contentsOptions) {
                options = options || {};
                var self = this;

                // console.log( this + '.fetchWithContents' );
                // TODO: push down to a base class
                options.view = "dev-detailed";

                // fetch history then use history data to fetch (paginated) contents
                return this.fetch(options).then(function getContents(history) {
                    self.contents.history = self;
                    self.contents.setHistoryId(history.id);
                    return self.fetchContents(contentsOptions);
                });
            },

            /** fetch this histories contents, adjusting options based on the stored history preferences */
            fetchContents: function (options) {
                options = options || {};

                // we're updating, reset the update time
                this.lastUpdateTime = new Date();
                return this.contents.fetchCurrentPage(options);
            },

            /** save this history, _Mark_ing it as deleted (just a flag) */
            _delete: function (options) {
                if (this.get("deleted")) {
                    return jQuery.when();
                }
                return this.save({ deleted: true }, options);
            },
            /** purge this history, _Mark_ing it as purged and removing all dataset data from the server */
            purge: function (options) {
                if (this.get("purged")) {
                    return jQuery.when();
                }
                return this.save({ deleted: true, purged: true }, options);
            },
            /** save this history, _Mark_ing it as undeleted */
            undelete: function (options) {
                if (!this.get("deleted")) {
                    return jQuery.when();
                }
                return this.save({ deleted: false }, options);
            },

            /** Make a copy of this history on the server
             *  @param {Boolean} current    if true, set the copy as the new current history (default: true)
             *  @param {String} name        name of new history (default: none - server sets to: Copy of <current name>)
             *  @fires copied               passed this history and the response JSON from the copy
             *  @returns {xhr}
             */
            copy: function (current, name, allDatasets) {
                current = current !== undefined ? current : true;
                if (!this.id) {
                    throw new Error("You must set the history ID before copying it.");
                }

                var postData = { history_id: this.id };
                if (current) {
                    postData.current = true;
                }
                if (name) {
                    postData.name = name;
                }
                if (!allDatasets) {
                    postData.all_datasets = false;
                }
                postData.view = "dev-detailed";

                var history = this;
                var copy = jQuery.post(this.urlRoot, postData);
                // if current - queue to setAsCurrent before firing 'copied'
                if (current) {
                    return copy.then((response) => {
                        var newHistory = new History(response);
                        return newHistory.setAsCurrent().done(() => {
                            history.trigger("copied", history, response);
                        });
                    });
                }
                return copy.done((response) => {
                    history.trigger("copied", history, response);
                });
            },

            setAsCurrent: function () {
                var history = this;

                var xhr = jQuery.getJSON(`${getAppRoot()}history/set_as_current?id=${this.id}`);

                xhr.done(() => {
                    history.trigger("set-as-current", history);
                });
                return xhr;
            },

            // ........................................................................ misc
            toString: function () {
                return `History(${this.get("id")},${this.get("name")})`;
            },
        }
    )
);

//==============================================================================
var _collectionSuper = CONTROLLED_FETCH_COLLECTION.InfinitelyScrollingCollection;
/** @class A collection of histories (per user)
 *      that maintains the current history as the first in the collection.
 *  New or copied histories become the current history.
 */
export var HistoryCollection = _collectionSuper.extend(BASE_MVC.LoggableMixin).extend({
    _logNamespace: "history",

    model: History,
    /** @type {String} initial order used by collection */
    order: "update_time",
    /** @type {Number} limit used for the first fetch (or a reset) */
    limitOnFirstFetch: 10,
    /** @type {Number} limit used for each subsequent fetch */
    limitPerFetch: 10,

    initialize: function (models, options) {
        options = options || {};
        this.log("HistoryCollection.initialize", models, options);
        this.urlRoot = `${getAppRoot()}api/histories`;
        _collectionSuper.prototype.initialize.call(this, models, options);

        /** @type {boolean} should deleted histories be included */
        this.includeDeleted = options.includeDeleted || false;

        /** @type {String} encoded id of the history that's current */
        this.currentHistoryId = options.currentHistoryId;

        this.setUpListeners();
        // note: models are sent to reset *after* this fn ends; up to this point
        // the collection *is empty*
    },

    url: function () {
        return this.urlRoot;
    },

    /** set up reflexive event handlers */
    setUpListeners: function setUpListeners() {
        return this.on({
            // when a history is deleted, remove it from the collection (if optionally set to do so)
            "change:deleted": function (history) {
                // TODO: this becomes complicated when more filters are used
                this.debug("change:deleted", this.includeDeleted, history.get("deleted"));
                if (!this.includeDeleted && history.get("deleted")) {
                    this.remove(history);
                }
            },
            // listen for a history copy, setting it to current
            copied: function (original, newData) {
                this.setCurrent(new History(newData, []));
            },
            // when a history is made current, track the id in the collection
            "set-as-current": function (history) {
                var oldCurrentId = this.currentHistoryId;
                this.trigger("no-longer-current", oldCurrentId);
                this.currentHistoryId = history.id;
            },
        });
    },

    /** override to change view */
    _buildFetchData: function (options) {
        return _.extend(_collectionSuper.prototype._buildFetchData.call(this, options), {
            view: "dev-detailed",
        });
    },

    /** override to filter out deleted and purged */
    _buildFetchFilters: function (options) {
        var superFilters = _collectionSuper.prototype._buildFetchFilters.call(this, options) || {};
        var filters = {};
        if (this.includeDeleted !== true) {
            filters.deleted = false;
            filters.purged = false;
        } else {
            // force API to return both deleted and non
            //TODO: when the API is updated, remove this
            filters.deleted = null;
        }
        return _.defaults(superFilters, filters);
    },

    /** override to fetch current as well (as it may be outside the first 10, etc.) */
    fetchFirst: function (options) {
        // TODO: batch?
        var xhr = jQuery.when();
        if (this.currentHistoryId) {
            xhr = _collectionSuper.prototype.fetchFirst.call(this, {
                silent: true,
                limit: 1,
                filters: {
                    "encoded_id-in": this.currentHistoryId,
                    // without these a deleted current history will return [] here and block the other xhr
                    deleted: null,
                    purged: "",
                },
            });
        }
        return xhr.then(() => {
            options = options || {};
            options.offset = 0;
            return this.fetchMore(options);
        });
    },

    /** @type {Object} map of collection available sorting orders containing comparator fns */
    comparators: _.extend(_.clone(_collectionSuper.prototype.comparators), {
        name: BASE_MVC.buildComparator("name", {
            ascending: true,
        }),
        "name-dsc": BASE_MVC.buildComparator("name", {
            ascending: false,
        }),
        size: BASE_MVC.buildComparator("size", {
            ascending: false,
        }),
        "size-asc": BASE_MVC.buildComparator("size", {
            ascending: true,
        }),
    }),

    /** override to always have the current history first */
    sort: function (options) {
        options = options || {};
        var silent = options.silent;
        var currentHistory = this.remove(this.get(this.currentHistoryId));
        _collectionSuper.prototype.sort.call(this, _.defaults({ silent: true }, options));
        this.unshift(currentHistory, { silent: true });
        if (!silent) {
            this.trigger("sort", this, options);
        }
        return this;
    },

    /** create a new history and by default set it to be the current history */
    create: function create(data, hdas, historyOptions, xhrOptions) {
        //TODO: .create is actually a collection function that's overridden here
        var collection = this;

        var xhr = jQuery.getJSON(`${getAppRoot()}history/create_new_current`);
        return xhr.done((newData) => {
            collection.setCurrent(new History(newData, [], historyOptions || {}));
        });
    },

    /** set the current history to the given history, placing it first in the collection.
     *  Pass standard bbone options for use in unshift.
     *  @triggers new-current passed history and this collection
     */
    setCurrent: function (history, options) {
        options = options || {};
        // new histories go in the front
        this.unshift(history, options);
        this.currentHistoryId = history.get("id");
        if (!options.silent) {
            this.trigger("new-current", history, this);
        }
        return this;
    },

    toString: function toString() {
        return `HistoryCollection(${this.length},current:${this.currentHistoryId})`;
    },
});
