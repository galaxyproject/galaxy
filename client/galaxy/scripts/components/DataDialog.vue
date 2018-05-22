<template>
    <b-modal v-model="modalShow" ref="modal" title="Select a dataset" @ok="handleOk">
        <b-alert variant="danger" :show="errMsg">
            {{ errMsg }}
        </b-alert>
        <b-form-select v-model="selected" :options="options"/>
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
    data() {
        return {
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
            let host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
            this.callback(`${host}${this.selected}/display`);
        },
        loadOptions: function() {
            this.historyId = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
            if (this.historyId) {
                axios
                    .get(`${Galaxy.root}api/histories/${this.historyId}/contents`)
                    .then(response => {
                        for(let item of response.data) {
                            this.options.push({value: item.url, text: item.name});
                        }
                    })
                    .catch(e => (this.errMsg = e.response.data.err_msg));
            } else {
                this.errMsg = "History not accessible.";
            }
        }
    }
};
</script>
