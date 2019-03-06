<template>
    <b-modal class="data-dialog-modal" v-model="modalShow" :ok-only="true" ok-title="Close">
        <template slot="modal-header">
            <b-input-group v-if="optionsShow">
                <b-input v-model="filter" placeholder="Type to Search" />
                <b-input-group-append>
                    <b-btn :disabled="!filter" @click="filter = ''">Clear</b-btn>
                </b-input-group-append>
            </b-input-group>
        </template>
        <b-alert v-if="errorMessage" variant="danger" :show="errorShow"> {{ errorMessage }} </b-alert>
        <div v-else>
            <div v-if="optionsShow">
                <b-table
                    small
                    hover
                    :items="items"
                    :fields="fields"
                    :filter="filter"
                    @row-clicked="selected"
                    @filtered="filtered"
                >
                    <template slot="name" slot-scope="data">
                        <i v-if="isDataset(data.item)" class="fa fa-file-o"/>
                        <i v-else class="fa fa-copy" /> {{ data.item.hid }}: {{ data.value }}
                    </template>
                    <template slot="extension" slot-scope="data">
                        {{ data.value ? data.value : "-" }}
                    </template>
                    <template slot="update_time" slot-scope="data">
                        {{ data.value ? data.value.substring(0, 16).replace("T", " ") : "-" }}
                    </template>
                    <template slot="arrow" slot-scope="data">
                        <b-button variant="link" size="sm"
                            class="py-0"
                            v-if="!isDataset(data.item)"
                            @click.stop="load(data.item.url)">
                            View
                        </b-button>
                    </template>
                </b-table>
                <div v-if="nItems == 0">
                    <div v-if="filter">
                        No search results found for: <b>{{ this.filter }}</b>.
                    </div>
                    <div v-else>
                        No entries.
                    </div>
                </div>
            </div>
            <div v-else>
                <span class="fa fa-spinner fa-spin"/>
                <span>Please wait...</span>
            </div>
        </div>
        <div slot="modal-footer" class="w-100">
            <b-btn size="sm" class="float-left"
                v-if="undoShow"
                @click="load()">
                <div class="fa fa-caret-left mr-1"/>Back
            </b-btn>
            <b-btn size="sm" class="float-right ml-1"
                variant="primary"
                @click="done"
                :disabled="values.length === 0">
                Ok
            </b-btn>
            <b-btn size="sm" class="float-right"
                @click="modalShow=false">
                Cancel
            </b-btn>
         </div>
    </b-modal>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
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
                    "class": "text-right"
                }
            },
            url: null,
            values: [],
            valuesType: null,
            filter: null,
            nItems: 0,
            items: [],
            errorMessage: null,
            errorShow: true,
            modalShow: true,
            undoShow: false,
            optionsShow: false,

            filter: null,
            nItems: 0,
            currentPage: 0,
            perPage: 10,
            items: [],
            errorMessage: null,
            errorShow: true,
            historyId: null,
            modalShow: true,
            optionsShow: false
        };
    },
    created: function() {
        this.load();
    },
    methods: {
        isDataset: function(item) {
            return item.history_content_type == "dataset";
        },
        filtered: function(items) {
            this.nItems = items.length;
        },
        clicked: function(record) {
            let host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
            this.callback(`${host}/${record.url}/display`);
            this.modalShow = false;
        },
        selected: function(record) {
            if (!this.multiple || this.valuesType !== record.history_content_type) {
                this.values = [];
                this.valuesType = record.history_content_type;
            }
            let found = this.values.findIndex(value =>
                ["id", "history_content_type"]
                .every(key => value[key] == record[key]));
            if (found == -1) {
                this.values.push(record);
            } else {
                this.values.splice(found, 1);
            }
            this.items.every(item => item._rowVariant = "default");
            this.values.every(value => value._rowVariant = "success");
        },
        done: function() {
            let results = [];
            this.values.forEach(v => {
                let host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
                results.push(`${host}/api/histories/${v.history_id}/contents/${v.id}/display`);
            });
            if (results.length > 0 && !this.multiple) {
                results = results[0];
            }
            this.modalShow = false;
            this.callback(results);
        },
        load: function(url) {
            let Galaxy = getGalaxyInstance();
            this.optionsShow = false;
            this.undoShow = false;
            let hasUrl = !!url;
            if (!hasUrl) {
                let historyId = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
                if (historyId) {
                    url = `${Galaxy.root}api/histories/${historyId}/contents`;
                } else {
                    this.errorMessage = "History not accessible.";
                    return;
                }
            }
            axios
                .get(url)
                .then(response => {
                    this.items = [];
                    this.stack = [response.data];
                    while (this.stack.length > 0) {
                        let root = this.stack.pop();
                        if (Array.isArray(root)) {
                            root.forEach(element => {
                                this.stack.push(element);
                            });
                        } else if (root.elements) {
                            this.stack.push(root.elements);
                        } else if (root.object) {
                            this.stack.push(root.object);
                        } else if (root.hid) {
                            this.items.push(root);
                            window.console.log(root);
                        }
                    }
                    this.optionsShow = true;
                    this.undoShow = hasUrl;
                })
                .catch(e => {
                    if (e.response) {
                        this.errorMessage = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
                    } else {
                        this.errorMessage = "Server unavailable.";
                    }
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
