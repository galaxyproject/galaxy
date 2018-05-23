<template>
    <b-modal  class="data-dialog-modal" v-model="modalShow" :title="modalTitle" @ok="handleOk" :ok-only="!optionsShow">
        <b-alert v-if="errorMessage" variant="danger" :show="errorShow">
            {{ errorMessage }}
        </b-alert>
        <div v-else>
            <div v-if="optionsShow">
                <b-form-input v-model="filter" placeholder="Type to Search" />
                <br/>
                <b-table small striped hover :items="items" :fields="fields">
                    <template slot="extension" slot-scope="data">
                        {{ data.value ? data.value : "-" }}
                    </template>
                    <template slot="update_time" slot-scope="data">
                        {{ data.value ? data.value.substring(0, 16).replace("T", " ") : "-" }}
                    </template>
                </b-table>
            </div>
            <div v-else>
                <span class="fa fa-spinner fa-spin"/>
                <span>Please wait...</span>
            </div>
        </div>
    </b-modal>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        callback: {
            type: Function,
            required: true
        }
    },
    computed: {
        modalTitle() {
            if (this.errorMessage) {
                return "Failed to load datasets";
            }
            if (this.optionsShow) {
                return "Select a dataset";
            }
            return "Loading datasets";
        }
    },
    data() {
        return {
            fields: {
                hid: {
                    label: "Id",
                    sortable: true
                },
                name: {
                    sortable: true
                },
                history_content_type: {
                    label: "Type",
                    sortable: true
                },
                extension: {
                    sortable: true
                },
                update_time: {
                    label: "Last Changed",
                    sortable: true
                }
            },
            filter: null,
            currentPage: 0,
            perPage: 10,
            items: [],
            errorMessage: null,
            errorShow: true,
            historyId: null,
            modalShow: true,
            options: [],
            optionsShow: false,
            selected: null
        };
    },
    created: function() {this.loadOptions()},
    methods: {
        formatDate: function(dateString) {
            let r = dateString.substring(0, 16);
            return r;
        },
        handleOk: function() {
            if (this.selected) {
                let host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
                this.callback(`${host}${this.selected}/display`);
            }
        },
        loadOptions: function() {
            this.historyId = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
            this.selected = null;
            this.options = [];
            if (this.historyId) {
                axios
                    .get(`${Galaxy.root}api/histories/${this.historyId}/contents`)
                    .then(response => {
                        this.items = response.data;
                        window.console.log(this.items);
                        /*for(let item of response.data) {
                            this.options.push({value: item.url, text: `${item.hid}: ${item.name}`});
                            if (!this.selected) {
                                this.selected = item.url;
                            }
                        }*/
                        this.optionsShow = true;
                    })
                    .catch(e => {
                        if (e.response) {
                            this.errorMessage = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
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
.data-dialog-modal .modal-body{
    max-height: 50vh;
    overflow-y: auto;
}
</style>
