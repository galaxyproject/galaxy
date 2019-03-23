<template>
    <b-modal class="data-dialog-modal" v-if="modalShow" visible ok-only ok-title="Close">
        <template slot="modal-header">
            <b-input-group>
                <b-input v-model="filter" placeholder="Type to Search" />
                <b-input-group-append>
                    <b-btn :disabled="!filter" @click="filter = ''">Clear</b-btn>
                </b-input-group-append>
            </b-input-group>
        </template>
        <b-alert v-if="errorMessage" variant="danger" show v-html="errorMessage" />
        <div v-else>
            <div v-if="optionsShow">
                <b-table
                    small
                    hover
                    :items="formatedItems"
                    :fields="fields"
                    :filter="filter"
                    :per-page="perPage"
                    :current-page="currentPage"
                    @row-clicked="clicked"
                    @filtered="filtered"
                >
                    <template slot="name" slot-scope="data">
                        <i v-if="isDataset(data.item)" class="fa fa-file-o" /> <i v-else class="fa fa-copy" />
                        {{ data.item.hid }}: {{ data.value }}
                    </template>
                    <template slot="extension" slot-scope="data">
                        {{ data.value ? data.value : "-" }}
                    </template>
                    <template slot="update_time" slot-scope="data">
                        {{ data.value ? data.value.substring(0, 16).replace("T", " ") : "-" }}
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
            <b-btn size="sm" class="float-right ml-1" variant="primary" @click="done" :disabled="values.length === 0">
                Ok
            </b-btn>
            <b-btn size="sm" class="float-right" @click="modalShow = false"> Cancel </b-btn>
        </div>
    </b-modal>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";

Vue.use(BootstrapVue);

export default {
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
            default: "url"
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
                extension: {
                    sortable: true
                },
                update_time: {
                    sortable: true
                },
                arrow: {
                    label: "",
                    sortable: false,
                    class: "text-right"
                }
            },
            filter: null,
            historyId: null,
            items: [],
            modalShow: true,
            navigation: [],
            nItems: 0,
            optionsShow: false,
            perPage: 100,
            undoShow: false,
            values: {}
        };
    },
    computed: {
        /** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
        formatedItems() {
            for (let item of this.items) {
                if (this.isDataset(item)) {
                    let key = item.id;
                    item._rowVariant = this.values[key] ? "success" : "default";
                } else {
                    item._rowVariant = "active";
                }
            }
            return this.items;
        }
    },
    created: function() {
        this.load();
    },
    methods: {
        /** Returns true if the item is a dataset entry **/
        isDataset: function(item) {
            return item.history_content_type == "dataset" || item.type == "file";
        },
        /** Called when a filter/search word is entered **/
        filtered: function(items) {
            this.nItems = items.length;
            this.currentPage = 1;
        },
        /** Collects selected datasets in value array **/
        clicked: function(record) {
            if (this.isDataset(record)) {
                if (!this.multiple) {
                    this.values = {};
                }
                let key = record.id;
                if (!this.values[key]) {
                    this.values[key] = record;
                } else {
                    delete this.values[key];
                }
                this.values = Object.assign({}, this.values);
                if (!this.multiple) {
                    this.done();
                }
            }
        },
        /** Called when selection is complete, values are formatted and parsed to external callback **/
        done: function() {
            let results = [];
            Object.values(this.values).forEach(v => {
                let value = null;
                if (this.format == "url") {
                    let host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
                    value = `${host}/api/histories/${v.history_id}/contents/${value}/display`;
                } else {
                    value = v;
                }
                results.push(value);
            });
            if (results.length > 0 && !this.multiple) {
                results = results[0];
            }
            this.modalShow = false;
            this.callback(results);
        },
        /** Returns the default url of current history **/
        getHistoryUrl: function() {
            let galaxy = getGalaxyInstance();
            let historyId = galaxy.currHistoryPanel && galaxy.currHistoryPanel.model.id;
            if (historyId) {
                return `${galaxy.root}api/histories/${historyId}/contents?deleted=false`;
            }
        },
        /** Travereses server response to identify dataset records **/
        getItems: function(data) {
            let galaxy = getGalaxyInstance();
            let items = [];
            if (this.navigation.length == 0) {
                items.push({
                    name: "Data Libraries",
                    url: `${galaxy.root}api/libraries`
                });
            }
            let stack = [data];
            while (stack.length > 0) {
                let root = stack.pop();
                if (Array.isArray(root)) {
                    root.forEach(element => {
                        stack.push(element);
                    });
                } else if (root.elements) {
                    stack.push(root.elements);
                } else if (root.object) {
                    stack.push(root.object);
                } else if (root.model_class == "Library") {
                    root.url = `${galaxy.root}api/libraries/${root.id}/contents`;
                    items.push(root);
                } else if (root.type == "file") {
                    root.name = root.name.substring(1);
                    items.push(root);
                } else if (root.hid) {
                    items.push(root);
                }
            }
            return items;
        },
        /** Returns and tracks urls for data drilling **/
        getUrl: function(url) {
            if (url) {
                this.navigation.push(url);
            } else {
                this.navigation.pop();
                let navigationLength = this.navigation.length;
                if (navigationLength > 0) {
                    url = this.navigation[navigationLength - 1];
                } else {
                    url = this.getHistoryUrl();
                }
            }
            return url
        },
        /** Performs server request to retrieve raw data records **/
        load: function(url) {
            url = this.getUrl(url);
            this.filter = null;
            this.optionsShow = false;
            this.undoShow = this.navigation.length > 0;
            if (url) {
                axios
                    .get(url)
                    .then(response => {
                        this.items = this.getItems(response.data);
                        this.filtered(this.items);
                        this.optionsShow = true;
                    })
                    .catch(e => {
                        if (e.response) {
                            this.errorMessage =
                                e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
                        } else {
                            this.errorMessage = "Server unavailable.";
                        }
                    });
            } else {
                this.errorMessage = "Datasets not available.";
            }
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
