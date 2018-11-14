import jQuery from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import BASE_MVC from "mvc/base-mvc";

//=============================================================================
/**
 * A Collection that can be limited/offset/re-ordered/filtered.
 * @type {Backbone.Collection}
 */
var ControlledFetchCollection = Backbone.Collection.extend({
    /** call setOrder on initialization to build the comparator based on options */
    initialize: function(models, options) {
        Backbone.Collection.prototype.initialize.call(this, models, options);
        this.setOrder(options.order || this.order, { silent: true });
    },

    /** set up to track order changes and re-sort when changed */
    _setUpListeners: function() {
        return this.on({
            "changed-order": this.sort
        });
    },

    /** override to provide order and offsets based on instance vars, set limit if passed,
     *  and set allFetched/fire 'all-fetched' when xhr returns
     */
    fetch: function(options) {
        options = this._buildFetchOptions(options);
        let Galaxy = getGalaxyInstance();
        Galaxy.debug("fetch options:", options);
        return Backbone.Collection.prototype.fetch.call(this, options);
    },

    /** build ajax data/parameters from options */
    _buildFetchOptions: function(options) {
        let Galaxy = getGalaxyInstance();

        // note: we normally want options passed in to override the defaults built here
        // so most of these fns will generate defaults
        options = _.clone(options) || {};

        // jquery ajax option; allows multiple q/qv for filters (instead of 'q[]')
        options.traditional = true;

        // options.data
        // we keep limit, offset, etc. in options *as well as move it into data* because:
        // - it makes fetch calling convenient to add it to a single options map (instead of as mult. args)
        // - it allows the std. event handlers (for fetch, etc.) to have access
        //   to the pagination options too
        //      (i.e. this.on( 'sync', function( options ){ if( options.limit ){ ... } }))
        // however, when we send to xhr/jquery we copy them to data also so that they become API query params
        options.data = options.data || this._buildFetchData(options);
        Galaxy.debug("data:", options.data);

        // options.data.filters --> options.data.q, options.data.qv
        var filters = this._buildFetchFilters(options);
        Galaxy.debug("filters:", filters);
        if (!_.isEmpty(filters)) {
            _.extend(options.data, this._fetchFiltersToAjaxData(filters));
        }
        Galaxy.debug("data:", options.data);
        return options;
    },

    /** Build the dictionary to send to fetch's XHR as data */
    _buildFetchData: function(options) {
        var defaults = {};
        if (this.order) {
            defaults.order = this.order;
        }
        return _.defaults(_.pick(options, this._fetchParams), defaults);
    },

    /** These attribute keys are valid params to fetch/API-index */
    _fetchParams: [
        /** model dependent string to control the order of models returned */
        "order",
        /** limit the number of models returned from a fetch */
        "limit",
        /** skip this number of models when fetching */
        "offset",
        /** what series of attributes to return (model dependent) */
        "view",
        /** individual keys to return for the models (see api/histories.index) */
        "keys"
    ],

    /** add any needed filters here based on collection state */
    _buildFetchFilters: function(options) {
        // override
        return _.clone(options.filters || {});
    },

    /** Convert dictionary filters to qqv style arrays */
    _fetchFiltersToAjaxData: function(filters) {
        // return as a map so ajax.data can extend from it
        var filterMap = {
            q: [],
            qv: []
        };
        _.each(filters, (v, k) => {
            // don't send if filter value is empty
            if (v === undefined || v === "") {
                return;
            }
            // json to python
            if (v === true) {
                v = "True";
            }
            if (v === false) {
                v = "False";
            }
            if (v === null) {
                v = "None";
            }
            // map to k/v arrays (q/qv)
            filterMap.q.push(k);
            filterMap.qv.push(v);
        });
        return filterMap;
    },

    /** override to reset allFetched flag to false */
    reset: function(models, options) {
        this.allFetched = false;
        return Backbone.Collection.prototype.reset.call(this, models, options);
    },

    // ........................................................................ order
    order: null,

    /** @type {Object} map of collection available sorting orders containing comparator fns */
    comparators: {
        update_time: BASE_MVC.buildComparator("update_time", {
            ascending: false
        }),
        "update_time-asc": BASE_MVC.buildComparator("update_time", {
            ascending: true
        }),
        create_time: BASE_MVC.buildComparator("create_time", {
            ascending: false
        }),
        "create_time-asc": BASE_MVC.buildComparator("create_time", {
            ascending: true
        })
    },

    /** set the order and comparator for this collection then sort with the new order
     *  @event 'changed-order' passed the new order and the collection
     */
    setOrder: function(order, options) {
        options = options || {};
        var collection = this;
        var comparator = collection.comparators[order];
        if (_.isUndefined(comparator)) {
            throw new Error(`unknown order: ${order}`);
        }
        // if( _.isUndefined( comparator ) ){ return; }
        if (comparator === collection.comparator) {
            return;
        }

        collection.order = order;
        collection.comparator = comparator;

        if (!options.silent) {
            collection.trigger("changed-order", options);
        }
        return collection;
    }
});

//=============================================================================
/**
 *
 */
var PaginatedCollection = ControlledFetchCollection.extend({
    /** @type {Number} limit used for each page's fetch */
    limitPerPage: 500,

    initialize: function(models, options) {
        ControlledFetchCollection.prototype.initialize.call(this, models, options);
        this.currentPage = options.currentPage || 0;
    },

    getTotalItemCount: function() {
        return this.length;
    },

    shouldPaginate: function() {
        return this.getTotalItemCount() >= this.limitPerPage;
    },

    getLastPage: function() {
        return Math.floor(this.getTotalItemCount() / this.limitPerPage);
    },

    getPageCount: function() {
        return this.getLastPage() + 1;
    },

    getPageLimitOffset: function(pageNum) {
        pageNum = this.constrainPageNum(pageNum);
        return {
            limit: this.limitPerPage,
            offset: pageNum * this.limitPerPage
        };
    },

    constrainPageNum: function(pageNum) {
        return Math.max(0, Math.min(pageNum, this.getLastPage()));
    },

    /** fetch the next page of data */
    fetchPage: function(pageNum, options) {
        var self = this;
        pageNum = self.constrainPageNum(pageNum);
        self.currentPage = pageNum;
        options = _.defaults(options || {}, self.getPageLimitOffset(pageNum));

        self.trigger("fetching-more");
        return self.fetch(options).always(() => {
            self.trigger("fetching-more-done");
        });
    },

    fetchCurrentPage: function(options) {
        return this.fetchPage(this.currentPage, options);
    },

    fetchPrevPage: function(options) {
        return this.fetchPage(this.currentPage - 1, options);
    },

    fetchNextPage: function(options) {
        return this.fetchPage(this.currentPage + 1, options);
    }
});

//=============================================================================
/**
 * A Collection that will load more elements without reseting.
 */
var InfinitelyScrollingCollection = ControlledFetchCollection.extend({
    /** @type {Number} limit used for the first fetch (or a reset) */
    limitOnFirstFetch: null,
    /** @type {Number} limit used for each subsequent fetch */
    limitPerFetch: 100,

    initialize: function(models, options) {
        ControlledFetchCollection.prototype.initialize.call(this, models, options);
        /** @type {Integer} number of contents to return from the first fetch */
        this.limitOnFirstFetch = options.limitOnFirstFetch || this.limitOnFirstFetch;
        /** @type {Integer} limit for every fetch after the first */
        this.limitPerFetch = options.limitPerFetch || this.limitPerFetch;
        /** @type {Boolean} are all contents fetched? */
        this.allFetched = false;
        /** @type {Integer} what was the offset of the last content returned */
        this.lastFetched = options.lastFetched || 0;
    },

    /** build ajax data/parameters from options */
    _buildFetchOptions: function(options) {
        // options (options for backbone.fetch and jquery.ajax generally)
        // backbone option; false here to make fetching an addititive process
        options.remove = options.remove || false;
        return ControlledFetchCollection.prototype._buildFetchOptions.call(this, options);
    },

    /** fetch the first 'page' of data */
    fetchFirst: function(options) {
        let Galaxy = getGalaxyInstance();
        Galaxy.debug("ControlledFetchCollection.fetchFirst:", options);
        options = options ? _.clone(options) : {};
        this.allFetched = false;
        this.lastFetched = 0;
        return this.fetchMore(
            _.defaults(options, {
                reset: true,
                limit: this.limitOnFirstFetch
            })
        );
    },

    /** fetch the next page of data */
    fetchMore: function(options) {
        let Galaxy = getGalaxyInstance();

        Galaxy.debug("ControlledFetchCollection.fetchMore:", options);
        options = _.clone(options || {});
        var collection = this;

        Galaxy.debug("fetchMore, options.reset:", options.reset);
        if (!options.reset && collection.allFetched) {
            return jQuery.when();
        }

        // TODO: this fails in the edge case where
        //  the first fetch offset === limit (limit 4, offset 4, collection.length 4)
        if (options.reset) {
            options.offset = 0;
        } else if (options.offset === undefined) {
            options.offset = collection.lastFetched;
        }
        var limit = (options.limit = options.limit || collection.limitPerFetch || null);
        Galaxy.debug("fetchMore, limit:", limit, "offset:", options.offset);

        collection.trigger("fetching-more");
        return (
            collection
                .fetch(options)
                .always(() => {
                    collection.trigger("fetching-more-done");
                })
                // maintain allFetched flag and trigger if all were fetched this time
                .done(function _postFetchMore(fetchedData) {
                    var numFetched = _.isArray(fetchedData) ? fetchedData.length : 0;
                    collection.lastFetched += numFetched;
                    Galaxy.debug("fetchMore, lastFetched:", collection.lastFetched);
                    // anything less than a full page means we got all there is to get
                    if (!limit || numFetched < limit) {
                        collection.allFetched = true;
                        collection.trigger("all-fetched", this);
                    }
                })
        );
    },

    /** fetch all the collection */
    fetchAll: function(options) {
        // whitelist options to prevent allowing limit/offset/filters
        // (use vanilla fetch instead)
        options = options || {};
        var self = this;
        options = _.pick(options, "silent");
        options.filters = {};
        return self.fetch(options).done(() => {
            self.allFetched = true;
            self.trigger("all-fetched", self);
        });
    }
});

//==============================================================================
export default {
    ControlledFetchCollection: ControlledFetchCollection,
    PaginatedCollection: PaginatedCollection,
    InfinitelyScrollingCollection: InfinitelyScrollingCollection
};
