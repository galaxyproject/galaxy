import * as Backbone from "libs/backbone";
import AJAX_QUEUE from "utils/ajax-queue";

/** ms between fetches when checking running jobs/datasets for updates */
var UPDATE_DELAY = 4000;
var NON_TERMINAL_STATES = ["new", "queued", "running"];
var ERROR_STATES = ["error", "deleted"];
/** Fetch state on add or just wait for polling to start. */
var FETCH_STATE_ON_ADD = false;

var JobStatesSummary = Backbone.Model.extend({
    url: function() {
        return `${Galaxy.root}api/histories/${this.attributes.history_id}/contents/dataset_collections/${
            this.attributes.collection_id
        }/jobs_summary`;
    },

    hasDetails: function() {
        return this.has("populated_state");
    },

    new: function() {
        return !this.hasDetails() || this.get("populated_state") == "new";
    },

    errored: function() {
        return this.get("populated_state") === "error" || this.anyWithStates(ERROR_STATES);
    },

    states: function() {
        return this.get("states") || {};
    },

    anyWithState: function(queryState) {
        return (this.states()[queryState] || 0) > 0;
    },

    anyWithStates: function(queryStates) {
        var states = this.states();
        for (var index in queryStates) {
            if ((states[queryStates[index]] || 0) > 0) {
                return true;
            }
        }
        return false;
    },

    numWithStates: function(queryStates) {
        var states = this.states();
        var count = 0;
        for (var index in queryStates) {
            count += states[queryStates[index]] || 0;
        }
        return count;
    },

    numInError: function() {
        return this.numWithStates(ERROR_STATES);
    },

    running: function() {
        return this.anyWithState("running");
    },

    terminal: function() {
        if (this.new()) {
            return false;
        } else {
            var anyNonTerminal = this.anyWithStates(NON_TERMINAL_STATES);
            return !anyNonTerminal;
        }
    },

    jobCount: function() {
        var states = this.states();
        var count = 0;
        for (var index in states) {
            count += states[index];
        }
        return count;
    },

    toString: function() {
        return `JobStatesSummary(id=${this.get("id")})`;
    }
});

var JobStatesSummaryCollection = Backbone.Collection.extend({
    model: JobStatesSummary,

    initialize: function() {
        if (FETCH_STATE_ON_ADD) {
            this.on({
                add: model => model.fetch()
            });
        }

        /** cached timeout id for the dataset updater */
        this.updateTimeoutId = null;
        // this.checkForUpdates();
        this.active = true;
    },

    monitor: function(options) {
        this.clearUpdateTimeout();
        if (!this.active) {
            return;
        }

        var _delayThenMonitorAgain = () => {
            this.updateTimeoutId = setTimeout(() => {
                this.monitor(options);
            }, UPDATE_DELAY);
        };

        var updateFunctions = this.models
            .filter(model => {
                return !model.terminal();
            })
            .map(summary => {
                return () => {
                    console.log("Fetching...");
                    return summary.fetch();
                };
            });

        if (updateFunctions.length > 0) {
            return new AJAX_QUEUE.AjaxQueue(updateFunctions).done(_delayThenMonitorAgain);
        } else {
            _delayThenMonitorAgain();
        }
    },

    /** clear the timeout and the cached timeout id */
    clearUpdateTimeout: function() {
        if (this.updateTimeoutId) {
            clearTimeout(this.updateTimeoutId);
            this.updateTimeoutId = null;
        }
    },

    toString: function() {
        return `JobStatesSummaryCollection()`;
    }
});

export default { JobStatesSummary, JobStatesSummaryCollection };
