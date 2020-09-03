<template>
    <b-card title="TRS Import">
        <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
        <div>
            <b>TRS Server:</b>

            <TrsServerSelection
                :selection="trsSelection"
                :trs-servers="trsServers"
                :loading="trsServersLoading"
                @onTrsSelection="onTrsSelection"
            />
        </div>
        <div>
            <b>TRS ID:</b>
            <b-form-input v-model="toolId" />
        </div>

        <trs-tool :trs-tool="trsTool" v-if="trsTool != null" @onImport="importVersion" />
    </b-card>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import TrsServerSelection from "./TrsServerSelection";
import TrsTool from "./TrsTool";
import { Services } from "./services";
import QueryStringParsing from "utils/query-string-parsing";

Vue.use(BootstrapVue);

export default {
    components: {
        TrsServerSelection,
        TrsTool,
    },
    created() {
        this.services = new Services();
        this.queryTrsServer = QueryStringParsing.get("trs_server");
        this.queryTrsId = QueryStringParsing.get("trs_id");
        this.toolId = this.queryTrsId;
        this.configureTrsServers();
    },
    data() {
        return {
            trsSelection: null,
            trsServers: [],
            trsServersLoading: true,
            toolId: null,
            trsTool: null,
            errorMessage: null,
            queryTrsServer: null,
            queryTrsId: null,
        };
    },
    computed: {
        hasErrorMessage() {
            return this.errorMessage != null;
        },
    },
    watch: {
        toolId: function () {
            this.onToolId();
        },
    },
    methods: {
        configureTrsServers() {
            this.services.getTrsServers().then((servers) => {
                this.trsServers = servers;
                const queryTrsServer = this.queryTrsServer;
                let trsSelection = null;
                if (queryTrsServer) {
                    for (const server of servers) {
                        if (server.id == queryTrsServer) {
                            trsSelection = server;
                            break;
                        }
                        if (possibleServeUrlsMatch(server.api_url, queryTrsServer)) {
                            trsSelection = server;
                            break;
                        }
                        if (possibleServeUrlsMatch(server.link_url, queryTrsServer)) {
                            trsSelection = server;
                            break;
                        }
                    }
                }
                if (trsSelection === null) {
                    if (queryTrsServer) {
                        this.errorMessage = "Failed to find requested TRS server " + queryTrsServer;
                    }
                    trsSelection = servers[0];
                }
                this.trsSelection = trsSelection;
                this.trsServersLoading = false;
                if (this.toolId) {
                    this.onToolId();
                }
            });
        },
        onTrsSelection(selection) {
            this.trsSelection = selection;
        },
        onToolId() {
            if (!this.trsSelection) {
                return;
            }
            this.services
                .getTrsTool(this.trsSelection.id, this.toolId)
                .then((tool) => {
                    this.trsTool = tool;
                    this.errorMessage = null;
                })
                .catch((errorMessage) => {
                    this.trsTool = null;
                    this.errorMessage = errorMessage;
                });
        },
        importVersion(version) {
            this.services
                .importTrsTool(this.trsSelection.id, this.toolId, version.name)
                .then((response_data) => {
                    // copied from the WorkflowImport, de-duplicate somehow
                    window.location = `${getAppRoot()}workflows/list?message=${response_data.message}&status=success`;
                })
                .catch((errorMessage) => {
                    this.errorMessage = errorMessage || "Import failed for an unknown reason.";
                });
        },
    },
};

function possibleServeUrlsMatch(a, b) {
    // let http://trs_server.org/ match with https://trs_server.org for instance,
    // we'll only use the one configured on the backend for making actual calls, but
    // allow some robustness in matching it
    a = a.replace(/^https?:\/\//, "").replace(/\/$/, "");
    b = b.replace(/^https?:\/\//, "").replace(/\/$/, "");
    return a == b;
}
</script>
