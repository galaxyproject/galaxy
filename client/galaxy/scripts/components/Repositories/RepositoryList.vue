<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <span v-if="loading">
                <span class="fa fa-spinner fa-spin" />
                Loading installed repositories...
            </span>
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <b-input
                    id="repository-search"
                    name="query"
                    placeholder="search installed repositories"
                    autocomplete="off"
                    type="text"
                    v-model="filter"
                />
                <div class="mt-3 mb-1 mx-1 text-muted">
                    {{ repositories.length }} repositories installed on this instance.
                </div>
                <b-table
                    id="repository-table"
                    striped
                    :fields="fields"
                    :items="repositories"
                    :filter="filter"
                    @filtered="filtered"
                >
                    <template slot="name" slot-scope="row">
                        <b-link href="#" role="button" class="font-weight-bold" @click="row.toggleDetails">
                            {{ row.item.name }}
                        </b-link>
                        <p>{{ row.item.description }}</p>
                    </template>
                    <template slot="tool_shed" slot-scope="row">
                        <b-link :href="row.item.tool_shed_url" role="button" class="font-weight-bold">
                            {{ row.item.tool_shed }}
                        </b-link>
                    </template>
                    <template slot="row-details" slot-scope="row">
                        <repositorydetails :repo="row.item" />
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
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
import RepositoryDetails from "./RepositoryDetails.vue";

export default {
    components: {
        repositorydetails: RepositoryDetails
    },
    data() {
        return {
            error: null,
            fields: {
                name: {
                    sortable: true
                },
                owner: {
                    sortable: true
                }
            },
            filter: "",
            loading: true,
            message: null,
            messageVariant: null,
            nRepositories: 0,
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
            this.filter = "";
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
        filtered: function(items) {
            this.nRepositories = items.length;
        }
    }
};
</script>
