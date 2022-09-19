<!-- Modelled after Sam's ToolShed ServerSelection.vue -->
<template>
    <span v-if="!loading" class="m-1 text-muted">
        <span v-if="showDropdown" class="dropdown">
            <b-link
                id="dropdownTrsServer"
                data-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                class="font-weight-bold">
                {{ selection.label }}
                <span class="fa fa-caret-down" />
            </b-link>
            <div class="dropdown-menu" aria-labelledby="dropdownTrsServer">
                <a
                    v-for="serverSelection in trsServers"
                    :key="serverSelection.id"
                    class="dropdown-item"
                    href="javascript:void(0)"
                    role="button"
                    @click.prevent="onTrsSelection(serverSelection)"
                    >{{ serverSelection.label }}</a
                >
            </div>
        </span>
        <span v-else>
            <b-link :href="selection.link_url" target="_blank" class="font-weight-bold" :title="selection.doc">
                {{ selection.label }}
            </b-link>
        </span>
    </span>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";

Vue.use(BootstrapVue);

export default {
    props: {
        queryTrsServer: {
            type: String,
            default: null,
        },
        queryTrsId: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            selection: null,
            trsSelection: null,
            trsServers: [],
            loading: true,
        };
    },
    computed: {
        showDropdown() {
            return this.trsServers.length > 1;
        },
    },
    created() {
        this.services = new Services();
        this._configureTrsServers();
    },
    methods: {
        onTrsSelection(selection) {
            this.selection = selection;
            this.$emit("onTrsSelection", selection);
        },
        onError(message) {
            this.$emit("onError", message);
        },
        _configureTrsServers() {
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
                        this.onError("Failed to find requested TRS server " + queryTrsServer);
                    }
                    trsSelection = servers[0];
                }
                this.selection = trsSelection;
                this.loading = false;
                this.onTrsSelection(trsSelection);
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
<style scoped>
span.dropdown {
    display: inline-block;
}
</style>
