<template>
    <b-modal class="data-dialog-modal" v-if="modalShow" visible ok-only ok-title="Close">
        <template slot="modal-header">
            <data-dialog-search v-model="filter" />
        </template>
        <b-alert v-if="errorMessage" variant="danger" show v-html="errorMessage" />
        <div v-else>
            <div v-if="optionsShow">
                <b-table
                    small
                    hover
                    :items="items"
                    :fields="fields"
                    :filter="filter"
                    :per-page="perPage"
                    :current-page="currentPage"
                    @row-clicked="clicked"
                    @filtered="filtered"
                >
                    <template slot="name" slot-scope="data">
                        <i v-if="isDataset(data.item)" class="fa fa-file-o" /> <i v-else class="fa fa-copy" />
                        {{ data.value ? data.value : "-" }}
                    </template>
                    <template slot="details" slot-scope="data">
                        {{ data.value ? data.value : "-" }}
                    </template>
                    <template slot="time" slot-scope="data">
                        {{ data.value ? data.value : "-" }}
                    </template>
                    <template slot="arrow" slot-scope="data">
                        <b-button
                            variant="link"
                            size="sm"
                            class="py-0"
                            v-if="!isDataset(data.item)"
                            @click.stop="load(data.item.url)"
                        >
                            View
                        </b-button>
                    </template>
                </b-table>
                <div v-if="nItems === 0">
                    <div v-if="filter">
                        No search results found for: <b>{{ this.filter }}</b
                        >.
                    </div>
                    <div v-else>No entries.</div>
                </div>
                <b-pagination v-if="nItems > perPage" v-model="currentPage" :per-page="perPage" :total-rows="nItems" />
            </div>
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
        </div>
        <div v-if="!errorMessage" slot="modal-footer" class="w-100">
            <b-btn size="sm" class="float-left" v-if="undoShow" @click="load()">
                <div class="fa fa-caret-left mr-1" />
                Back
            </b-btn>
            <b-btn size="sm" class="float-right ml-1" variant="primary" @click="finalize" :disabled="!hasValues">
                Ok
            </b-btn>
            <b-btn size="sm" class="float-right" @click="modalShow = false"> Cancel </b-btn>
        </div>
    </b-modal>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import DataDialogSearch from "./DataDialogSearch.vue";
import { isDataset } from "./utilities.js";
import { Model } from "./model.js";
import { Services } from "./services.js";

Vue.use(BootstrapVue);

export default {
    components: {
        "data-dialog-search": DataDialogSearch
    },
    props: {
        callback: {
            type: Function,
            required: true
        },
        multiple: {
            type: Boolean,
            default: false
        },
        format: {
            type: String,
            default: "download"
        },
        library: {
            type: Boolean,
            default: true
        }
    },
    data() {
        return {
            currentPage: 1,
            errorMessage: null,
            fields: {
                name: {
                    sortable: true
                },
                details: {
                    sortable: true
                },
                time: {
                    sortable: true
                },
                arrow: {
                    label: "",
                    sortable: false,
                    class: "text-right"
                }
            },
            filter: null,
            items: [],
            modalShow: true,
            nItems: 0,
            optionsShow: false,
            perPage: 100,
            undoShow: false
        };
    },
    created: function() {
        this.services = new Services();
        this.model = new Model({ multiple: this.multiple, format: this.format });
        this.load();
    },
    methods: {
        /** Returns true if the item is a dataset entry **/
        isDataset: isDataset,
        /** Returns true if records have been added to the model **/
        hasValues: function() {
            return this.model.count() > 0;
        },
        /** Resets pagination when a filter/search word is entered **/
        filtered: function(items) {
            this.nItems = items.length;
            this.currentPage = 1;
        },
        /** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
        formatRows() {
            for (let item of this.items) {
                let _rowVariant = "active";
                if (isDataset(item)) {
                    _rowVariant = this.model.exists(item.id) ? "success" : "default";
                }
                Vue.set(item, "_rowVariant", _rowVariant);
            }
        },
        /** Collects selected datasets in value array **/
        clicked: function(record) {
            if (isDataset(record)) {
                this.model.add(record);
                if (this.multiple) {
                    this.formatRows();
                } else {
                    this.finalize();
                }
            }
        },
        /** Called when selection is complete, values are formatted and parsed to external callback **/
        finalize: function() {
            let results = this.model.finalize();
            this.modalShow = false;
            this.callback(results);
        },
        /** Performs server request to retrieve data records **/
        load: function(url) {
            this.filter = null;
            this.optionsShow = false;
            this.undoShow = !this.services.atRoot();
            this.services
                .getData(url)
                .then(items => {
                    this.items = items;
                    this.filtered(this.items);
                    this.optionsShow = true;
                })
                .catch(errorMessage => {
                    this.errorMessage = errorMessage;
                });
        }
    }
};
</script>
<style>
.data-dialog-modal .modal-body {
    max-height: 50vh;
    height: 50vh;
    overflow-y: auto;
}
</style>
