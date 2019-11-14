<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" message="Loading datasets" />
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <delayed-input class="mb-3" @onChange="onChange" />
                <b-table
                    id="dataset-table"
                    striped
                    :fields="fields"
                    :items="rows"
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
import DelayedInput from "components/common/DelayedInput.vue";
import LoadingSpan from "components/LoadingSpan.vue";

export default {
    components: {
        LoadingSpan,
        DelayedInput
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
            rows: []
        };
    },
    computed: {
        showNotFound() {
            return this.rows.length === 0 && this.filter;
        },
        showNotAvailable() {
            return this.rows.length === 0 && !this.filter;
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
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        },
        onChange: function(query) {
            this.load();
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
