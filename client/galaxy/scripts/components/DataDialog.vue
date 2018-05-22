<template>
    <b-modal v-model="modalShow" :title="modalTitle" @ok="handleOk" ok-only="!errMsg">
        <b-alert v-if="errMsg" variant="danger" :show="errMsg">
            {{ errMsg }}
        </b-alert>
        <div v-else>
            <b-form-select v-if="optionsShow" v-model="selected" :options="options"/>
            <div v-if="!optionsShow">
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
            if (this.errMsg) {
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
            optionsShow: false,
            modalShow: true,
            historyId: null,
            selected: null,
            errMsg: null,
            options: []
        };
    },
    created: function() {this.loadOptions()},
    methods: {
        handleOk: function() {
            if (this.selected) {
                let host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
                this.callback(`${host}${this.selected}/display`);
            }
        },
        loadOptions: function() {
            this.historyId = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
            this.selected = null;
            if (this.historyId) {
                axios
                    .get(`${Galaxy.root}api/histories/${this.historyId}/contents`)
                    .then(response => {
                        for(let item of response.data) {
                            this.options.push({value: item.url, text: item.name});
                            if (!this.selected) {
                                this.selected = item.url;
                            }
                        }
                        this.optionsShow = true;
                    })
                    .catch(e => {
                        this.errMsg = e.response.data.err_msg;
                    });
            } else {
                this.errMsg = "History not accessible.";
            }
        }
    }
};
</script>
