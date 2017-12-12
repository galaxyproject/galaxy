define("mvc/job/job-model", ["exports", "mvc/history/history-contents", "mvc/dataset/states", "utils/ajax-queue", "mvc/base-mvc", "utils/localization"], function(exports, _historyContents, _states, _ajaxQueue, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _historyContents2 = _interopRequireDefault(_historyContents);

    var _states2 = _interopRequireDefault(_states);

    var _ajaxQueue2 = _interopRequireDefault(_ajaxQueue);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "jobs";
    //==============================================================================
    var searchableMixin = _baseMvc2.default.SearchableModelMixin;
    /** @class Represents a job running or ran on the server job handlers.
     */
    var Job = Backbone.Model.extend(_baseMvc2.default.LoggableMixin).extend(_baseMvc2.default.mixin(searchableMixin,
        /** @lends Job.prototype */
        {
            _logNamespace: logNamespace,

            /** default attributes for a model */
            defaults: {
                model_class: "Job",

                tool_id: null,
                exit_code: null,

                inputs: {},
                outputs: {},
                params: {},

                create_time: null,
                update_time: null,
                state: _states2.default.NEW
            },

            /** override to parse params on incomming */
            parse: function parse(response, options) {
                response.params = this.parseParams(response.params);
                return response;
            },

            /** override to treat param values as json */
            parseParams: function parseParams(params) {
                var newParams = {};
                _.each(params, function(value, key) {
                    newParams[key] = JSON.parse(value);
                });
                return newParams;
            },

            /** instance vars and listeners */
            initialize: function initialize(attributes, options) {
                this.debug(this + "(Job).initialize", attributes, options);

                this.set("params", this.parseParams(this.get("params")), {
                    silent: true
                });

                this.outputCollection = attributes.outputCollection || new _historyContents2.default.HistoryContents([]);
                this._setUpListeners();
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
            },

            // ........................................................................ common queries
            /** Is this job in a 'ready' state; where 'Ready' states are states where no
             *      processing is left to do on the server.
             */
            inReadyState: function inReadyState() {
                return _.contains(_states2.default.READY_STATES, this.get("state"));
            },

            /** Does this model already contain detailed data (as opposed to just summary level data)? */
            hasDetails: function hasDetails() {
                //?? this may not be reliable
                return !_.isEmpty(this.get("outputs"));
            },

            // ........................................................................ ajax
            /** root api url */
            urlRoot: Galaxy.root + "api/jobs",
            //url : function(){ return this.urlRoot; },

            // ........................................................................ searching
            // see base-mvc, SearchableModelMixin
            /** what attributes of an Job will be used in a text search */
            //searchAttributes : [
            //    'tool'
            //],

            // ........................................................................ misc
            /** String representation */
            toString: function toString() {
                return ["Job(", this.get("id"), ":", this.get("tool_id"), ")"].join("");
            }
        }));

    //==============================================================================
    /** @class Backbone collection for Jobs.
     */
    var JobCollection = Backbone.Collection.extend(_baseMvc2.default.LoggableMixin).extend(
        /** @lends JobCollection.prototype */
        {
            _logNamespace: logNamespace,

            model: Job,

            /** root api url */
            urlRoot: Galaxy.root + "api/jobs",
            url: function url() {
                return this.urlRoot;
            },

            intialize: function intialize(models, options) {
                console.debug(models, options);
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

            /** Get jobs that are not ready
             *  @returns array of content models
             */
            notReady: function notReady() {
                return this.filter(function(job) {
                    return !job.inReadyState();
                });
            },

            /** return true if any jobs don't have details */
            haveDetails: function haveDetails() {
                return this.all(function(job) {
                    return job.hasDetails();
                });
            },

            // ........................................................................ ajax
            /** fetches all details for each job in the collection using a queue */
            queueDetailFetching: function queueDetailFetching() {
                var collection = this;

                var queue = new _ajaxQueue2.default.AjaxQueue(this.map(function(job) {
                    return function() {
                        return job.fetch({
                            silent: true
                        });
                    };
                }));

                queue.done(function() {
                    collection.trigger("details-loaded");
                });
                return queue;
            },

            //toDAG : function(){
            //    return new JobDAG( this.toJSON() );
            //},

            // ........................................................................ sorting/filtering
            /** return a new collection of jobs whose attributes contain the substring matchesWhat */
            matches: function matches(matchesWhat) {
                return this.filter(function(job) {
                    return job.matches(matchesWhat);
                });
            },

            // ........................................................................ misc
            /** String representation. */
            toString: function toString() {
                return ["JobCollection(", this.length, ")"].join("");
            }

            //----------------------------------------------------------------------------- class vars
        }, {
            /** class level fn for fetching the job details for all jobs in a history */
            fromHistory: function fromHistory(historyId) {
                console.debug(this);
                var Collection = this;
                var collection = new Collection([]);
                collection.fetch({
                    data: {
                        history_id: historyId
                    }
                }).done(function() {
                    window.queue = collection.queueDetailFetching();
                });
                return collection;
            }
        });

    //=============================================================================
    exports.default = {
        Job: Job,
        JobCollection: JobCollection
    };
});
//# sourceMappingURL=../../../maps/mvc/job/job-model.js.map
