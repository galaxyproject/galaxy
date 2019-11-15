<template>
    <div class="overflow-auto h-100" @scroll="onScroll">
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" message="Loading datasets" />
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <delayed-input class="mb-3" @onChange="onQuery" placeholder="Search Datasets" />
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
            scrolled: false,
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
                    sortable: false
                }
            ],
            query: "",
            limit: 50,
            offset: 0,
            sortBy: "name",
            sortDesc: false,
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
        load(concat = false) {
            this.services
                .getDatasets({
                    query: this.query,
                    sortBy: this.sortBy,
                    sortDesc: this.sortDesc,
                    offset: this.offset,
                    limit: this.limit
                })
                .then(datasets => {
                    if (concat) {
                        this.rows = this.rows.concat(datasets);
                    } else {
                        this.rows = datasets;
                    }
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        },
        onTags: function(item) {},
        onQuery(query) {
            this.query = query;
            this.offset = 0;
            this.load();
        },
        onSort: function(item) {
            this.sortBy = item.sortBy;
            this.sortDesc = item.sortDesc;
            this.offset = 0;
            this.load();
        },
        onScroll({ target: { scrollTop, clientHeight, scrollHeight } }) {
            if (scrollTop + clientHeight >= scrollHeight) {
                if (this.offset + this.limit <= this.rows.length) {
                    this.offset += this.limit;
                    this.load(true);
                }
            }
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
