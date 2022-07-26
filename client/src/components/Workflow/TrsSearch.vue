<template>
    <b-card title="GA4GH Tool Registry Server (TRS) Workflow Search">
        <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>

        <div>
            <b>TRS Server:</b>

            <TrsServerSelection @onTrsSelection="onTrsSelection" @onError="onTrsSelectionError" />
        </div>

        <div>
            <!-- <b>Search by workflow description:</b> -->
            <b-input-group class="mb-3">
                <b-input id="trs-search-query" v-model="query" placeholder="search query" @keydown.esc="query = ''" />
                <b-input-group-append>
                    <b-btn>
                        <i v-b-popover.bottom="searchHelp" class="fa fa-question" title="Search Help" />
                    </b-btn>
                    <b-btn v-b-tooltip.hover title="clear search" @click="query = ''">
                        <i class="fa fa-times" />
                    </b-btn>
                </b-input-group-append>
            </b-input-group>
        </div>
        <div>
            <b-alert v-if="searching" variant="info" show>
                Searching for {{ searchingFor }}, this may take a while - please be patient.
            </b-alert>
            <b-alert v-else-if="newSearch" variant="info" show> Enter search query to begin search. </b-alert>
            <b-alert v-else-if="results.length == 0" variant="info" show>
                No search results found, refine your search.
            </b-alert>
            <b-table
                v-else
                :fields="fields"
                :items="itemsComputed"
                hover
                striped
                caption-top
                :busy="searching"
                @row-clicked="showRowDetails">
                <template v-slot:row-details="row">
                    <b-card>
                        <trs-tool :trs-tool="row.item.data" @onImport="importVersion(row.item.data.id, $event)" />
                    </b-card>
                </template>
            </b-table>
        </div>
    </b-card>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services, TrsSearchService } from "./services";
import TrsMixin from "./trsMixin";

import VueRx from "vue-rx";

Vue.use(VueRx);
Vue.use(BootstrapVue);

export default {
    mixins: [TrsMixin],
    data() {
        const fields = [
            { key: "name", label: "Name" },
            { key: "description", label: "Description" },
            { key: "organization", label: "Organization" },
        ];
        return {
            query: "",
            results: [],
            trsSelection: null,
            errorMessage: null,
            trsSearchService: new TrsSearchService({}),
            searching: false,
            searchingFor: null,
            newSearch: true,
            fields: fields,
        };
    },
    computed: {
        hasErrorMessage() {
            return this.errorMessage != null;
        },
        itemsComputed() {
            return this.computeItems(this.results);
        },
        searchHelp() {
            return "Search by workflow description. Tags (key:value) can be used to also search by metadata - for instance name:example. Available tags include organization and name.";
        },
    },
    watch: {
        query: function () {
            if (this.query == "") {
                this.newSearch = true;
                this.results = [];
            } else {
                this.trsSearchService.searchQuery = this.query;
            }
        },
    },
    subscriptions() {
        return {
            searchResults: this.trsSearchService.searchResults,
        };
    },
    mounted() {
        let lastSubscription = null;
        this.$observables.searchResults.subscribe({
            next: (x) => {
                this.newSearch = false;
                this.searching = true;
                this.searchingFor = x[0];
                if (lastSubscription !== null) {
                    lastSubscription.unsubscribe();
                }
                lastSubscription = x[1].subscribe({
                    next: (results) => {
                        this.results = results;
                        this.searching = false;
                    },
                });
            },
            error: (e) => {
                this.errorMessage = e;
            },
        });
    },
    created() {
        this.services = new Services();
    },
    methods: {
        onTrsSelection(selection) {
            this.trsSelection = selection;
            this.trsSearchService.trsServer = selection.id;
            this.query = "";
        },
        onTrsSelectionError(message) {
            this.errorMessage = message;
        },
        showRowDetails(row, index, e) {
            if (e.target.nodeName != "A") {
                row._showDetails = !row._showDetails;
            }
        },
        computeItems(results) {
            return results.map((result) => {
                return {
                    id: result.id,
                    name: result.name,
                    description: result.description,
                    data: result,
                    _showDetails: false,
                };
            });
        },
    },
};
</script>
