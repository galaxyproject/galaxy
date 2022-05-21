import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import AJAX_QUEUE from "utils/ajax-queue";

/** ms between fetches when checking running jobs/datasets for updates */
var UPDATE_DELAY = 2000;
var NON_TERMINAL_STATES = ["new", "queued", "running", "waiting"];
var ERROR_STATES = ["error", "deleted"];
var TERMINAL_STATES = ["ok"].concat(ERROR_STATES);
const POPULATED_STATE_FAILED = "failed";
/** Fetch state on add or just wait for polling to start. */
var FETCH_STATE_ON_ADD = false;
var BATCH_FETCH_STATE = true;

var JobStatesSummary = Backbone.Model.extend({
    url: function () {
        return `${getAppRoot()}api/histories/${this.attributes.history_id}/contents/dataset_collections/${
            this.attributes.collection_id
        }/jobs_summary`;
    },

    hasDetails: function () {
        return this.has("populated_state");
    },

    new: function () {
        return !this.hasDetails() || this.get("populated_state") == "new";
    },

    populationFailed: function () {
        return this.get("populated_state") === POPULATED_STATE_FAILED;
    },

    errored: function () {
        return this.populationFailed() || this.anyWithStates(ERROR_STATES);
    },

    states: function () {
        return this.get("states") || {};
    },

    anyWithState: function (queryState) {
        return (this.states()[queryState] || 0) > 0;
    },

    anyWithStates: function (queryStates) {
        var states = this.states();
        for (var index in queryStates) {
            if ((states[queryStates[index]] || 0) > 0) {
                return true;
            }
        }
        return false;
    },

    numWithStates: function (queryStates) {
        var states = this.states();
        var count = 0;
        for (var index in queryStates) {
            count += states[queryStates[index]] || 0;
        }
        return count;
    },

    numInError: function () {
        return this.numWithStates(ERROR_STATES);
    },

    numTerminal: function () {
        return this.numWithStates(TERMINAL_STATES);
    },

    running: function () {
        return this.anyWithState("running");
    },

    terminal: function () {
        if (this.new()) {
            return false;
        } else {
            var anyNonTerminal = this.anyWithStates(NON_TERMINAL_STATES);
            return !anyNonTerminal;
        }
    },

    jobCount: function () {
        var states = this.states();
        var count = 0;
        for (var index in states) {
            count += states[index];
        }
        return count;
    },

    toString: function () {
        return `JobStatesSummary(id=${this.get("id")})`;
    },
});

var JobStatesSummaryCollection = Backbone.Collection.extend({
    model: JobStatesSummary,

    initialize: function () {
        /* By default we wait for a polling update to do model fetch because
           FETCH_STATE_ON_ADD is false to load the application and target components
           as quickly as possible. that said if the polling is turned off
           (!this.active) and collections are added - we need to fetch those still.
           This happens for instance in the single history view where a history is
           shown in a static way and not polled.
        */
        if (FETCH_STATE_ON_ADD) {
            this.on({
                add: (model) => model.fetch(),
            });
        } else {
            this.on({
                add: (model) => {
                    if (!this.active) {
                        model.fetch();
                    }
                },
            });
        }

        /** cached timeout id for the dataset updater */
        this.updateTimeoutId = null;
        // this.checkForUpdates();
        this.active = true;
    },

    trackModel: function (historyContent) {
        if (historyContent.has("job_states_summary")) {
            // already tracked...
            return;
        }

        const historyId = this.historyId;
        if (historyContent.attributes.history_content_type === "dataset_collection") {
            var jobSourceType = historyContent.attributes.job_source_type;
            var jobSourceId = historyContent.attributes.job_source_id;
            if (jobSourceType) {
                this.add({
                    id: jobSourceId,
                    model: jobSourceType,
                    history_id: historyId,
                    collection_id: historyContent.attributes.id,
                });
                historyContent.jobStatesSummary = this.get(jobSourceId);
            }
        }
    },

    url: function () {
        var nonTerminalModels = this.models.filter((model) => {
            return !model.terminal();
        });
        var ids = nonTerminalModels
            .map((summary) => {
                return summary.get("id");
            })
            .join(",");
        var types = nonTerminalModels
            .map((summary) => {
                return summary.get("model");
            })
            .join(",");
        return `${getAppRoot()}api/histories/${this.historyId}/jobs_summary?ids=${ids}&types=${types}`;
    },

    monitor: function () {
        this.clearUpdateTimeout();
        if (!this.active) {
            return;
        }

        var _delayThenMonitorAgain = () => {
            this.updateTimeoutId = setTimeout(() => {
                this.monitor();
            }, UPDATE_DELAY);
        };

        var nonTerminalModels = this.models.filter((model) => {
            return !model.terminal();
        });

        if (nonTerminalModels.length > 0 && !BATCH_FETCH_STATE) {
            // Allow models to fetch their own details.
            var updateFunctions = nonTerminalModels.map((summary) => {
                return () => {
                    return summary.fetch();
                };
            });

            return new AJAX_QUEUE.AjaxQueue(updateFunctions).done(_delayThenMonitorAgain);
        } else if (nonTerminalModels.length > 0) {
            // Batch fetch updated state...
            this.fetch({ remove: false }).done(_delayThenMonitorAgain);
        } else {
            _delayThenMonitorAgain();
        }
    },

    /** clear the timeout and the cached timeout id */
    clearUpdateTimeout: function () {
        if (this.updateTimeoutId) {
            clearTimeout(this.updateTimeoutId);
            this.updateTimeoutId = null;
        }
    },

    toString: function () {
        return `JobStatesSummaryCollection()`;
    },
});

export default {
    JobStatesSummary,
    JobStatesSummaryCollection,
    FETCH_STATE_ON_ADD,
    NON_TERMINAL_STATES,
    ERROR_STATES,
};
