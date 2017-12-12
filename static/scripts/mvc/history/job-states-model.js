define("mvc/history/job-states-model", ["exports", "libs/backbone", "utils/ajax-queue"], function(exports, _backbone, _ajaxQueue) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var Backbone = _interopRequireWildcard(_backbone);

    var _ajaxQueue2 = _interopRequireDefault(_ajaxQueue);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    function _interopRequireWildcard(obj) {
        if (obj && obj.__esModule) {
            return obj;
        } else {
            var newObj = {};

            if (obj != null) {
                for (var key in obj) {
                    if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key];
                }
            }

            newObj.default = obj;
            return newObj;
        }
    }

    /** ms between fetches when checking running jobs/datasets for updates */
    var UPDATE_DELAY = 2000;
    var NON_TERMINAL_STATES = ["new", "queued", "running"];
    var ERROR_STATES = ["error", "deleted"];
    /** Fetch state on add or just wait for polling to start. */
    var FETCH_STATE_ON_ADD = false;
    var BATCH_FETCH_STATE = true;

    var JobStatesSummary = Backbone.Model.extend({
        url: function url() {
            return Galaxy.root + "api/histories/" + this.attributes.history_id + "/contents/dataset_collections/" + this.attributes.collection_id + "/jobs_summary";
        },

        hasDetails: function hasDetails() {
            return this.has("populated_state");
        },

        new: function _new() {
            return !this.hasDetails() || this.get("populated_state") == "new";
        },

        errored: function errored() {
            return this.get("populated_state") === "error" || this.anyWithStates(ERROR_STATES);
        },

        states: function states() {
            return this.get("states") || {};
        },

        anyWithState: function anyWithState(queryState) {
            return (this.states()[queryState] || 0) > 0;
        },

        anyWithStates: function anyWithStates(queryStates) {
            var states = this.states();
            for (var index in queryStates) {
                if ((states[queryStates[index]] || 0) > 0) {
                    return true;
                }
            }
            return false;
        },

        numWithStates: function numWithStates(queryStates) {
            var states = this.states();
            var count = 0;
            for (var index in queryStates) {
                count += states[queryStates[index]] || 0;
            }
            return count;
        },

        numInError: function numInError() {
            return this.numWithStates(ERROR_STATES);
        },

        running: function running() {
            return this.anyWithState("running");
        },

        terminal: function terminal() {
            if (this.new()) {
                return false;
            } else {
                var anyNonTerminal = this.anyWithStates(NON_TERMINAL_STATES);
                return !anyNonTerminal;
            }
        },

        jobCount: function jobCount() {
            var states = this.states();
            var count = 0;
            for (var index in states) {
                count += states[index];
            }
            return count;
        },

        toString: function toString() {
            return "JobStatesSummary(id=" + this.get("id") + ")";
        }
    });

    var JobStatesSummaryCollection = Backbone.Collection.extend({
        model: JobStatesSummary,

        initialize: function initialize() {
            if (FETCH_STATE_ON_ADD) {
                this.on({
                    add: function add(model) {
                        return model.fetch();
                    }
                });
            }

            /** cached timeout id for the dataset updater */
            this.updateTimeoutId = null;
            // this.checkForUpdates();
            this.active = true;
        },

        url: function url() {
            var nonTerminalModels = this.models.filter(function(model) {
                return !model.terminal();
            });
            var ids = nonTerminalModels.map(function(summary) {
                return summary.get("id");
            }).join(",");
            var types = nonTerminalModels.map(function(summary) {
                return summary.get("model");
            }).join(",");
            return Galaxy.root + "api/histories/" + this.historyId + "/jobs_summary?ids=" + ids + "&types=" + types;
        },

        monitor: function monitor() {
            var _this = this;

            this.clearUpdateTimeout();
            if (!this.active) {
                return;
            }

            var _delayThenMonitorAgain = function _delayThenMonitorAgain() {
                _this.updateTimeoutId = setTimeout(function() {
                    _this.monitor();
                }, UPDATE_DELAY);
            };

            var nonTerminalModels = this.models.filter(function(model) {
                return !model.terminal();
            });

            if (nonTerminalModels.length > 0 && !BATCH_FETCH_STATE) {
                // Allow models to fetch their own details.
                var updateFunctions = nonTerminalModels.map(function(summary) {
                    return function() {
                        return summary.fetch();
                    };
                });

                return new _ajaxQueue2.default.AjaxQueue(updateFunctions).done(_delayThenMonitorAgain);
            } else if (nonTerminalModels.length > 0) {
                // Batch fetch updated state...
                this.fetch({
                    remove: false
                }).done(_delayThenMonitorAgain);
            } else {
                _delayThenMonitorAgain();
            }
        },

        /** clear the timeout and the cached timeout id */
        clearUpdateTimeout: function clearUpdateTimeout() {
            if (this.updateTimeoutId) {
                clearTimeout(this.updateTimeoutId);
                this.updateTimeoutId = null;
            }
        },

        toString: function toString() {
            return "JobStatesSummaryCollection()";
        }
    });

    exports.default = {
        JobStatesSummary: JobStatesSummary,
        JobStatesSummaryCollection: JobStatesSummaryCollection,
        FETCH_STATE_ON_ADD: FETCH_STATE_ON_ADD
    };
});
//# sourceMappingURL=../../../maps/mvc/history/job-states-model.js.map
