<template>
    <div id="structured-history-view">
        <div id="history-view-controls" class="clear">
            <div class="float-left">
                <span v-if="historyHistory['purged'] == false">
                    <span v-if="historyData.user_is_owner == false">
                        <button id="import" class="btn btn-secondary">Import and start using history</button>
                    </span>
                    <span v-if="historyData.user_is_owner && historyData.history_is_current == false">
                        <button id="switch-history" class="btn btn-secondary" v-on:click="switchHistory">
                            Switch to this history
                        </button>
                    </span>
                    <button id="show-structure" class="btn btn-secondary" v-on:click="showStructure">
                        Show structure
                    </button>
                </span>
            </div>
            <div class="float-right">
                <button id="toggle-deleted" class="btn btn-secondary">Include deleted</button>
                <button id="toggle-hidden" class="btn btn-secondary">Include hidden</button>
            </div>
        </div>
        <!-- eslint-disable-next-line vue/require-v-for-key -->
        <div v-for="error in errorMessages">
            <div class="alert alert-danger" role="alert">{{ error }}</div>
        </div>
        <div
            :id="'history-' + historyHistory['id']"
            class="history-panel unified-panel-body"
            style="overflow: auto;"
        ></div>
    </div>
</template>

<script>
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Vue from "vue";
import DisplayStructure from "components/DisplayStructured.vue";
import QueryStringParsing from "utils/query-string-parsing";
import HistoryView from "mvc/history/history-view";
import { getGalaxyInstance } from "app";

export default {
    props: {
        id: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            historyData: {},
            historyHistory: {},
            // TODO: Pick a standard messaging convention and use a child component for it here.
            errorMessages: []
        };
    },
    created: function() {
        let url = getAppRoot() + "history/view/" + this.id;
        this.ajaxCall(url, this.updateHistoryView);
    },
    methods: {
        ajaxCall: function(url, callBack) {
            axios
                .get(url)
                .then(response => {
                    callBack(response);
                })
                .catch(e => {
                    this.showError(
                        "Error fetching histories -- reload the page to retry this request.  Please contact an administrator if the problem persists.",
                        e
                    );
                });
        },
        updateHistoryView: function(response) {
            this.historyData = response.data;
            this.historyHistory = response.data.history;
        },
        showError: function(errorMsg, verbose) {
            console.error(verbose);
            this.errorMessages.push(errorMsg);
        },
        makeHistoryView: function(history) {
            $(function() {
                let options = {
                    hasMasthead: history.use_panels ? "true" : "false",
                    userIsOwner: history.user_is_owner ? "true" : "false",
                    isCurrent: history.history_is_current ? "true" : "false",
                    historyJSON: history.history,
                    showDeletedJson: history.show_deleted,
                    showHiddenJson: history.show_hidden,
                    initialModeDeleted: history.show_deleted ? "showing_deleted" : "not_showing_deleted",
                    initialModeHidden: history.show_hidden ? "showing_hidden" : "not_showing_hidden",
                    allowUserDatasetPurge: history.allow_user_dataset_purge ? "true" : "false"
                };
                options.viewToUse = options.userIsOwner
                    ? { location: "mvc/history/history-view-edit", className: "HistoryViewEdit" }
                    : { location: "mvc/history/history-view", className: "HistoryView" };
                HistoryView.historyEntry(options);
            });
        },
        showStructure: function() {
            let Galaxy = getGalaxyInstance();
            let displayStructureInstance = Vue.extend(DisplayStructure),
                mountView = document.createElement("div");
            Galaxy.page.center.display(mountView);
            new displayStructureInstance({ propsData: { id: QueryStringParsing.get("id") } }).$mount(mountView);
        },
        switchHistory: function() {
            let url = getAppRoot() + "history/switch_to_history?hist_id=" + this.historyHistory["id"];
            this.ajaxCall(url, this.reloadPage);
        },
        reloadPage: function() {
            window.location.reload();
        }
    },
    updated: function() {
        this.makeHistoryView(this.historyData);
    }
};
</script>

<style>
#history-view-controls {
    flex: 0 0 44px;
    background-color: white;
    border-bottom: 1px solid #ddd;
    width: 100%;
    padding: 8px;
}
.history-panel > .controls .title {
    font-size: 120%;
}
.history-panel > .controls .title input {
    font-size: 100%;
}
a.btn {
    text-decoration: none;
}
</style>
