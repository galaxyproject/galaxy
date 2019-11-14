<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" message="Loading datasets" />
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <b-row class="mb-3">
                    <b-col cols="6">
                        <b-input
                            id="dataset-search"
                            class="m-1"
                            name="query"
                            placeholder="Search Datasets"
                            autocomplete="off"
                            type="text"
                            v-model="filter"
                        />
                    </b-col>
                </b-row>
                <b-table
                    id="dataset-table"
                    striped
                    :fields="fields"
                    :items="rows"
                    :filter="filter"
                    @filtered="filtered"
                >
                </b-table>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ this.filter }}</span
                    >.
                </div>
                <div v-if="showNotAvailable">
                    No datasets found.
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
import LoadingSpan from "components/LoadingSpan.vue";

export default {
    components: {
        LoadingSpan
    },
    data() {
        return {
            error: null,
            fields: [
                {
                    key: "name",
                    sortable: true
                },{
                    key: "extension",
                    sortable: true
                },{
                    key: "history_id",
                    sortable: true
                },{
                    key: "tags",
                    sortable: true
                },{
                    key: "state",
                    sortable: true
                },{
                    key: "update_time",
                    sortable: true
                }
            ],
            filter: "",
            loading: true,
            message: null,
            messageVariant: null,
            nRows: 0,
            rows: []
        };
    },
    computed: {
        showNotFound() {
            return this.nRows === 0 && this.filter;
        },
        showNotAvailable() {
            return this.nRows === 0 && !this.filter;
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
                .getDatasets()
                .then(datasets => {
                    console.log(datasets);
                    this.rows = datasets;
                    this.nRows = this.rows.length;
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        },
        filtered: function(items) {
            this.nRows = items.length;
        },
        onSuccess: function(message) {
            this.message = message;
            this.messageVariant = "success";
        },
        onError: function(message) {
            this.message = message;
            this.messageVariant = "danger";
        }
    }
};
</script>
