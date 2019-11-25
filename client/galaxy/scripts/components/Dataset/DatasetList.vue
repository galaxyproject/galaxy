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
                        <DatasetName :item="row.item" @showDataset="onShowDataset" />
                    </template>
                    <template v-slot:cell(history_id)="row">
                        <DatasetHistory :item="row.item" @showDataset="onShowDataset" />
                    </template>
                    <template v-slot:cell(context)="row">
                        <DatasetContext :item="row.item" @addToHistory="onAddToHistory" />
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
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";
import DatasetName from "./DatasetName";
import DatasetHistory from "./DatasetHistory";
import DatasetContext from "./DatasetContext";
import DelayedInput from "components/Common/DelayedInput";
import Tags from "components/Common/Tags";
import LoadingSpan from "components/LoadingSpan";
import { mapActions } from "vuex";

export default {
    components: {
        DatasetContext,
        DatasetHistory,
        DatasetName,
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
                    label: "History",
                    key: "history_id",
                    sortable: true
                },
                {
                    key: "tags",
                    sortable: false
                },
                {
                    key: "context",
                    label: "",
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
        this.fetchHistories();
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.load();
    },
    methods: {
        ...mapActions(["fetchHistories"]),
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
        onAddToHistory(item) {
            const Galaxy = getGalaxyInstance();
            const history = Galaxy.currHistoryPanel;
            const dataset_id = item.id;
            const history_id = history.model.id;
            this.services
                .copyDataset(dataset_id, history_id)
                .then(response => {
                    history.loadCurrentHistory();
                })
                .catch(error => {
                    this.onError(error);
                });
        },
        onShowDataset(item) {
            const Galaxy = getGalaxyInstance();
            this.services
                .setHistory(item.history_id)
                .then(history => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                })
                .catch(error => {
                    this.onError(error);
                });
        },
        onTags(item) {
            this.services.updateTags(item.id, "HistoryDatasetAssociation", item.tags).catch(error => {
                this.onError(error);
            });
        },
        onQuery(query) {
            this.query = query;
            this.offset = 0;
            this.load();
        },
        onSort(item) {
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
        onSuccess(message) {
            this.message = message;
            this.messageVariant = "success";
        },
        onError(message) {
            this.message = message;
            this.messageVariant = "danger";
        }
    }
};
</script>
