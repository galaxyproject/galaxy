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
                    <b-link class="font-weight-bold" @click="toggleMonitor">
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
                    :sort-by="sortBy"
                    :items="repositories"
                    :filter="filter"
                    @filtered="filtered">
                    <template v-slot:cell(name)="row">
                        <b-link href="#" role="button" class="font-weight-bold" @click="row.toggleDetails">
                            <div v-if="!isLatest(row.item)">
                                <b-badge variant="danger" class="mb-2"> Newer version available! </b-badge>
                            </div>
                            <div class="name">{{ row.item.name }}</div>
                        </b-link>
                        <div>{{ row.item.description }}</div>
                    </template>
                    <template v-slot:row-details="row">
                        <RepositoryDetails :repo="row.item" />
                    </template>
                </b-table>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ filter }}</span
                    >.
                </div>
                <div v-if="showNotAvailable">No installed repositories found.</div>
            </div>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { Services } from "../services";
import LoadingSpan from "components/LoadingSpan";
import Monitor from "./Monitor";
import RepositoryDetails from "./Details";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
        Monitor,
        RepositoryDetails,
    },
    props: {
        filter: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            error: null,
            loading: true,
            message: null,
            messageVariant: null,
            nRepositories: 0,
            repositories: [],
            showMonitor: false,
            sortBy: "name",
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
        },
        numToolsheds() {
            const toolsheds = new Set();
            this.repositories.forEach((x) => {
                toolsheds.add(x.tool_shed);
            });
            return toolsheds.size;
        },
        fields() {
            const fields = [
                {
                    key: "name",
                    sortable: true,
                    sortByFormatted: (value, key, item) => {
                        return `${this.isLatest(item)}_${value}`;
                    },
                },
                {
                    key: "owner",
                    sortable: true,
                },
            ];
            if (this.numToolsheds > 1) {
                fields.push({
                    key: "tool_shed",
                    sortable: true,
                });
            }
            return fields;
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services();
        this.load();
    },
    methods: {
        isLatest(item) {
            const value = item.tool_shed_status && item.tool_shed_status.latest_installable_revision;
            return String(value).toLowerCase() != "false";
        },
        load() {
            this.loading = true;
            this.services
                .getInstalledRepositories({ selectLatest: true })
                .then((repositories) => {
                    this.repositories = repositories;
                    this.nRepositories = repositories.length;
                    this.loading = false;
                })
                .catch((error) => {
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
        },
    },
};
</script>
