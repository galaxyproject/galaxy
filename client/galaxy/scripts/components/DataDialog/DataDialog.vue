<template>
    <b-modal class="data-dialog-modal" v-if="modalShow" visible ok-only ok-title="Close">
        <template slot="modal-header">
            <data-dialog-search v-model="filter" />
        </template>
        <b-alert v-if="errorMessage" variant="danger" show v-html="errorMessage" />
        <div v-else>
            <data-dialog-table
                v-if="optionsShow"
                :items="items"
                :multiple="multiple"
                :filter="filter"
                @clicked="clicked"
                @load="load"
            />
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
        </div>
        <div v-if="!errorMessage" slot="modal-footer" class="w-100">
            <b-btn size="sm" class="float-left" v-if="undoShow" @click="load()">
                <div class="fa fa-caret-left mr-1" />
                Back
            </b-btn>
            <b-btn size="sm" class="float-right ml-1" variant="primary" @click="finalize" :disabled="!hasValue">
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
import DataDialogTable from "./DataDialogTable.vue";
import { UrlTracker } from "./utilities.js";
import { Model } from "./model.js";
import { Services } from "./services.js";

Vue.use(BootstrapVue);

export default {
    components: {
        "data-dialog-search": DataDialogSearch,
        "data-dialog-table": DataDialogTable
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
        },
        root: {
            type: String,
            required: true
        },
        host: {
            type: String,
            required: true
        },
        history: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            errorMessage: null,
            filter: null,
            items: [],
            modalShow: true,
            optionsShow: false,
            undoShow: false,
            hasValue: false,
            oldnewItems: false
        };
    },
    created: function() {
        this.services = new Services({ root: this.root, host: this.host });
        this.urlTracker = new UrlTracker(this.getHistoryUrl());
        this.model = new Model({ multiple: this.multiple, format: this.format });
        this.load();
    },
    methods: {
        /** Returns the default url i.e. the url of the current history **/
        getHistoryUrl: function() {
            return `${this.root}api/histories/${this.history}/contents?deleted=false`;
        },
        /** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
        formatRows() {
            for (let item of this.items) {
                let _rowVariant = "active";
                if (item.isDataset) {
                    _rowVariant = this.model.exists(item.id) ? "success" : "default";
                }
                Vue.set(item, "_rowVariant", _rowVariant);
            }
        },
        /** Collects selected datasets in value array **/
        clicked: function(record) {
            if (record.isDataset) {
                this.model.add(record);
                this.hasValue = this.model.count() > 0;
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
            url = this.urlTracker.getUrl(url);
            this.filter = null;
            this.optionsShow = false;
            this.undoShow = !this.urlTracker.atRoot();
            this.services
                .get(url)
                .then(items => {
                    if (this.library && this.urlTracker.atRoot()) {
                        items.unshift({
                            name: "Data Libraries",
                            url: `${this.root}api/libraries`
                        });
                    }
                    this.items = items;
                    this.formatRows();
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
