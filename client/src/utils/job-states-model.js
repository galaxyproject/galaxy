import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";

var NON_TERMINAL_STATES = ["new", "queued", "running", "waiting"];
var ERROR_STATES = ["error", "deleted"];
var TERMINAL_STATES = ["ok", "skipped"].concat(ERROR_STATES);
const POPULATED_STATE_FAILED = "failed";
/** Fetch state on add or just wait for polling to start. */
var FETCH_STATE_ON_ADD = false;

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

export default {
    JobStatesSummary,
    FETCH_STATE_ON_ADD,
    NON_TERMINAL_STATES,
    ERROR_STATES,
};
