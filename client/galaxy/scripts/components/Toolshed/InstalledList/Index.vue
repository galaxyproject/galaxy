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
                    <b-link id="popover-monitor">
                        <span class="fa fa-angle-double-down" />
                        Show installation queue.
                    </b-link>
                </div>
                <b-popover target="popover-monitor" triggers="hover" placement="top" :show.sync="showMonitor">
                    <template v-slot:title>
                        Installation Monitor
                    </template>
                    <Monitor @onQuery="onQuery" />
                </b-popover>
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
import RepositoryDetails from "./Details.vue";
import Monitor from "./Monitor";
import LoadingSpan from "components/LoadingSpan";

Vue.use(BootstrapVue);

export default {
    components: {
        Monitor,
        LoadingSpan,
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
            showMonitor: false,
            repositories: []
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
        onQuery(q) {
            this.showMonitor = false;
            this.$emit("onQuery", q);
        }
    }
};
</script>
