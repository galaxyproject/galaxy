<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" message="Loading datasets" />
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <delayed-input class="mb-3" @onChange="load" placeholder="Search Datasets" />
                <b-table
                    id="dataset-table"
                    striped
                    no-local-sorting
                    @sort-changed="onSort"
                    :fields="fields"
                    :items="rows"
                >
                    <template v-slot:cell(name)="row">
                        <span class="fa fa-check" />
                        {{ row.item.name }}
                    </template>
                    <template v-slot:cell(tags)="row">
                        <Tags :item="row.item" @input="onTags" />
                    </template>
                </b-table>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ this.query }}</span
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
import DelayedInput from "components/Common/DelayedInput";
import Tags from "components/Common/Tags";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
        DelayedInput,
        Tags
    },
    data() {
        return {
            error: null,
            fields: [
                {
                    key: "name",
                    sortable: true
                },
                {
                    key: "extension",
                    sortable: true
                },
                {
                    key: "tags",
                    sortable: true
                }
            ],
            query: "",
            loading: true,
            message: null,
            messageVariant: null,
            rows: []
        };
    },
    computed: {
        showNotFound() {
            return this.rows.length === 0 && this.query;
        },
        showNotAvailable() {
            return this.rows.length === 0 && !this.query;
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
        load(query, sortBy = "name", sortDesc = false) {
            this.query = query;
            this.services
                .getDatasets(query, sortBy, sortDesc)
                .then(datasets => {
                    this.rows = datasets;
                    /*this.rows.forEach(item => {
                        switch (item.state) {
                            case "error":
                                item._rowVariant = "danger";
                                break;
                            case "paused":
                                item._rowVariant = "info";
                        }
                    });*/
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        },
        onTags: function(item) {},
        onSort: function(item) {
            this.load(this.query, item.sortBy, item.sortDesc);
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
