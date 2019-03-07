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
                    @row-clicked="clicked"
                    @filtered="filtered"
                >
                    <template slot="name" slot-scope="data">
                        <i v-if="data.item.history_content_type == 'dataset'" class="fa fa-file-o" />
                        <i v-else class="fa fa-copy" /> {{ data.item.hid }}: {{ data.value }}
                    </template>
                    <template slot="extension" slot-scope="data">
                        {{ data.value ? data.value : "-" }}
                    </template>
                    <template slot="update_time" slot-scope="data">
                        {{ data.value ? data.value.substring(0, 16).replace("T", " ") : "-" }}
                    </template>
                </b-table>
                <div v-if="nItems == 0">No search results found for: {{ this.filter }}.</div>
            </div>
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
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
                }
            },
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
        filtered: function(items) {
            this.nItems = items.length;
        },
        clicked: function(record) {
            let host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
            this.callback(`${host}/${record.url}/display`);
            this.modalShow = false;
        },
        load: function() {
            let Galaxy = getGalaxyInstance();
            this.historyId = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
            if (this.historyId) {
                axios
                    .get(`${getAppRoot()}api/histories/${this.historyId}/contents`)
                    .then(response => {
                        this.items = response.data;
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
                this.errorMessage = "History not accessible.";
            }
        }
    }
};
</script>
<style>
.data-dialog-modal .modal-body {
    max-height: 50vh;
    overflow-y: auto;
}
</style>
