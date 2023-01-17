<template>
    <selection-dialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="onCancel">
        <template v-slot:search>
            <data-dialog-search v-model="filter" />
        </template>
        <template v-slot:options>
            <data-dialog-table
                v-if="optionsShow"
                :items="items"
                :multiple="multiple"
                :filter="filter"
                @clicked="onClick"
                @open="onLoad" />
        </template>
        <template v-slot:buttons>
            <b-btn v-if="undoShow" size="sm" class="float-left" @click="load()">
                <div class="fa fa-caret-left mr-1" />
                Back
            </b-btn>
            <b-btn v-if="allowUpload" size="sm" class="float-left mr-1" @click="onUpload">
                <div class="fa fa-upload ml-1" />
                Upload
            </b-btn>
            <b-btn
                v-if="multiple"
                size="sm"
                class="float-right ml-1"
                variant="primary"
                :disabled="!hasValue"
                @click="onOk">
                Ok
            </b-btn>
        </template>
    </selection-dialog>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import SelectionDialogMixin from "components/SelectionDialog/SelectionDialogMixin";
import { UrlTracker } from "./utilities";
import { Model } from "./model";
import { Services } from "./services";
import { getAppRoot } from "onload/loadConfig";
import { useGlobalUploadModal } from "composables/globalUploadModal";

Vue.use(BootstrapVue);

export default {
    mixins: [SelectionDialogMixin],
    props: {
        multiple: {
            type: Boolean,
            default: false,
        },
        format: {
            type: String,
            default: "download",
        },
        library: {
            type: Boolean,
            default: true,
        },
        history: {
            type: String,
            required: true,
        },
        modalStatic: {
            type: Boolean,
            default: false,
        },
        allowUpload: {
            type: Boolean,
            default: true,
        },
    },
    setup() {
        const { openGlobalUploadModal } = useGlobalUploadModal();
        return { openGlobalUploadModal };
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
        };
    },
    created: function () {
        this.services = new Services();
        this.urlTracker = new UrlTracker(this.getHistoryUrl());
        this.model = new Model({ multiple: this.multiple, format: this.format });
        this.load();
    },
    methods: {
        /** Returns the default url i.e. the url of the current history **/
        getHistoryUrl() {
            return `${getAppRoot()}api/histories/${this.history}/contents?deleted=false`;
        },
        /** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
        formatRows() {
            for (const item of this.items) {
                let _rowVariant = "active";
                if (item.isLeaf) {
                    _rowVariant = this.model.exists(item.id) ? "success" : "default";
                }
                Vue.set(item, "_rowVariant", _rowVariant);
            }
        },
        /** Collects selected datasets in value array **/
        onClick(record) {
            if (record.isLeaf) {
                this.model.add(record);
                this.hasValue = this.model.count() > 0;
                if (this.multiple) {
                    this.formatRows();
                } else {
                    this.onOk();
                }
            } else {
                this.load(record.url);
            }
        },
        /** Called when user decides to upload new data */
        onUpload() {
            const propsData = {
                multiple: this.multiple,
                format: this.format,
                callback: this.callback,
                modalShow: true,
                selectable: true,
            };
            this.openGlobalUploadModal(propsData);
            this.modalShow = false;
        },
        /** Called when selection is complete, values are formatted and parsed to external callback **/
        onOk() {
            const results = this.model.finalize();
            this.modalShow = false;
            this.callback(results);
            this.$emit("onOk", results);
        },
        /** Called when the modal is hidden */
        onCancel() {
            this.modalShow = false;
            this.$emit("onCancel");
        },
        /** On clicking folder name div: overloader for the @click.stop in DataDialogTable **/
        onLoad(record) {
            this.load(record.url);
        },
        /** Performs server request to retrieve data records **/
        load(url) {
            url = this.urlTracker.getUrl(url);
            this.filter = null;
            this.optionsShow = false;
            this.undoShow = !this.urlTracker.atRoot();
            this.services
                .get(url)
                .then((items) => {
                    if (this.library && this.urlTracker.atRoot()) {
                        items.unshift({
                            label: "Data Libraries",
                            url: `${getAppRoot()}api/libraries`,
                        });
                    }
                    this.items = items;
                    this.formatRows();
                    this.optionsShow = true;
                })
                .catch((errorMessage) => {
                    this.errorMessage = errorMessage;
                });
        },
    },
};
</script>
