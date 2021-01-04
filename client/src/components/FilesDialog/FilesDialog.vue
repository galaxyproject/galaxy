<template>
    <selection-dialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="() => (modalShow = false)"
    >
        <template v-slot:search>
            <data-dialog-search v-model="filter" />
        </template>
        <template v-slot:options>
            <data-dialog-table
                v-if="optionsShow"
                :items="items"
                :multiple="multiple"
                :filter="filter"
                :show-details="showDetails"
                :show-time="showTime"
                :show-navigate="mode == 'directory'"
                @clicked="clicked"
                @open="open"
                @load="load"
            />
        </template>
        <template v-slot:buttons>
            <b-btn size="sm" class="float-left" v-if="undoShow" @click="load()">
                <div class="fa fa-caret-left mr-1" />
                Back
            </b-btn>
            <b-btn
                v-if="multiple"
                size="sm"
                class="float-right ml-1"
                variant="primary"
                @click="finalize"
                :disabled="!hasValue"
            >
                Ok
            </b-btn>
        </template>
    </selection-dialog>
</template>

<script>
import Vue from "vue";
import SelectionDialogMixin from "components/SelectionDialog/SelectionDialogMixin";
import { UrlTracker } from "components/DataDialog/utilities";
import { Services } from "./services";
import { Model } from "./model";

export default {
    mixins: [SelectionDialogMixin],
    props: {
        multiple: {
            type: Boolean,
            default: false,
        },
        mode: {
            type: String,
            default: "file",
            validator: (prop) => ["file", "directory"].includes(prop),
        },
        requireWritable: {
            type: Boolean,
            default: false,
        },
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
            showTime: true,
            showDetails: true,
        };
    },
    created: function () {
        this.services = new Services();
        this.urlTracker = new UrlTracker("");
        this.model = new Model({ multiple: this.multiple });
        this.load();
    },
    computed: {
        fileMode() {
            return this.mode == "file";
        },
    },
    methods: {
        /** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
        formatRows() {
            for (const item of this.items) {
                let _rowVariant = "active";
                if (item.isLeaf || !this.fileMode) {
                    _rowVariant = this.model.exists(item.id) ? "success" : "default";
                }
                Vue.set(item, "_rowVariant", _rowVariant);
            }
        },
        /** Collects selected datasets in value array **/
        clicked: function (record) {
            if (record.isLeaf || !this.fileMode) {
                this.model.add(record);
                this.hasValue = this.model.count() > 0;
                if (this.multiple) {
                    this.formatRows();
                } else {
                    this.finalize();
                }
            } else {
                this.open(record);
            }
        },
        open: function (record) {
            this.load(record.url);
        },
        /** Called when selection is complete, values are formatted and parsed to external callback **/
        finalize: function () {
            const results = this.model.finalize();
            this.modalShow = false;
            this.callback(results);
        },
        /** Performs server request to retrieve data records **/
        load: function (url) {
            url = this.urlTracker.getUrl(url);
            this.filter = null;
            this.optionsShow = false;
            this.undoShow = !this.urlTracker.atRoot();
            if (this.urlTracker.atRoot()) {
                this.services
                    .getFileSources()
                    .then((items) => {
                        items = items
                            .filter((item) => !this.requireWritable || item.writable)
                            .map((item) => {
                                return {
                                    id: item.id,
                                    label: item.label,
                                    details: item.doc,
                                    isLeaf: false,
                                    url: item.uri_root,
                                    labelTitle: item.uri_root,
                                };
                            });
                        this.items = items;
                        this.formatRows();
                        this.optionsShow = true;
                        this.showTime = false;
                        this.showDetails = true;
                    })
                    .catch((errorMessage) => {
                        this.errorMessage = errorMessage;
                    });
            } else {
                this.services
                    .list(url)
                    .then((items) => {
                        if (this.fileMode) {
                            items = items.map((item) => {
                                const itemClass = item.class;
                                return {
                                    id: item.uri,
                                    label: item.name,
                                    time: item.ctime,
                                    isLeaf: itemClass == "File",
                                    size: item.size,
                                    url: item.uri,
                                    labelTitle: item.uri,
                                };
                            });
                        } else {
                            items = items
                                .filter((item) => item.class == "Directory")
                                .map((item) => {
                                    return {
                                        id: item.uri,
                                        label: item.name,
                                        time: item.ctime,
                                        isLeaf: false,
                                        size: item.size,
                                        url: item.uri,
                                        labelTitle: item.uri,
                                    };
                                });
                        }
                        this.items = items;
                        this.formatRows();
                        this.optionsShow = true;
                        this.showTime = true;
                        this.showDetails = false;
                    })
                    .catch((errorMessage) => {
                        this.errorMessage = errorMessage;
                    });
            }
        },
    },
};
</script>
