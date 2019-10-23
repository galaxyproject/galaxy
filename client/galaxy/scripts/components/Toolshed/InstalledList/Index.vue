<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" message="Loading installed repositories" />
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <div class="m-1">
                    <span class="installed-message text-muted">
                        {{ repositories.length }} repositories installed on this instance.
                    </span>
                    <b-link @click="toggleMonitor">
                        <span v-if="showMonitor">
                            <span class="fa fa-angle-double-up" />
                            <span>Hide installation progress.</span>
                        </span>
                        <span v-else>
                            <span class="fa fa-angle-double-down" />
                            <span>Show installation progress.</span>
                        </span>
                    </b-link>
                </div>
                <Monitor v-if="showMonitor" @onQuery="onQuery" />
                <b-table
                    id="repository-table"
                    striped
                    :fields="fields"
                    :items="repositories"
                    :filter="filter"
                    @filtered="filtered"
                >
                    <template v-slot:cell(name)="row">
                        <b-link href="#" role="button" class="font-weight-bold" @click="row.toggleDetails">
                            <div v-if="!asbool(row.item.tool_shed_status.latest_installable_revision)">
                                <b-badge variant="danger" class="mb-2">
                                    Newer version available!
                                </b-badge>
                            </div>
                            {{ row.item.name }}
                        </b-link>
                        <p>{{ row.item.description }}</p>
                    </template>
                    <template slot="row-details" slot-scope="row">
                        <RepositoryDetails :repo="row.item" />
                    </template>
                </b-table>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ this.filter }}</span
                    >.
                </div>
                <div v-if="showNotAvailable">
                    No installed repositories found.
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { Services } from "../services.js";
import LoadingSpan from "components/LoadingSpan";
import Monitor from "./Monitor";
import RepositoryDetails from "./Details";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
        Monitor,
        RepositoryDetails
    },
    props: ["filter"],
    data() {
        return {
            error: null,
            fields: [
                {
                    key: "name",
                    sortable: true
                },
                {
                    key: "owner",
                    sortable: true
                }
            ],
            loading: true,
            message: null,
            messageVariant: null,
            nRepositories: 0,
            repositories: [],
            showMonitor: false
        };
    },
    computed: {
        showNotFound() {
            return this.nRepositories === 0 && this.filter;
        },
        showNotAvailable() {
            return this.nRepositories === 0 && !this.filter;
        },
        showMessage() {
            return !!this.message;
        }
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.load();
    },
    methods: {
        asbool(value) {
            return String(value).toLowerCase() == "true";
        },
        load() {
            this.loading = true;
            this.services
                .getInstalledRepositories()
                .then(repositories => {
                    this.repositories = repositories;
                    this.nRepositories = repositories.length;
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        },
        filtered(items) {
            this.nRepositories = items.length;
        },
        toggleMonitor() {
            this.showMonitor = !this.showMonitor;
        },
        onQuery(query) {
            this.$emit("onQuery", query);
        }
    }
};
</script>
