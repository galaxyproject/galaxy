<template>
    <UploadWrapper wrapper-class="upload-view-composite">
        <div v-show="showHelper" class="upload-helper">Select a composite type</div>
        <table v-show="!showHelper" ref="uploadTable" class="upload-table ui-table-striped">
            <thead>
                <tr>
                    <th />
                    <th />
                    <th>Description</th>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Settings</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody />
        </table>
        <template v-slot:footer>
            <span class="upload-footer-title">Composite Type:</span>
            <Select2
                ref="footerExtension"
                v-model="extension"
                container-class="upload-footer-extension"
                :enabled="!running">
                <option v-for="(ext, index) in extensions" :key="index" :value="ext.id">{{ ext.text }}</option>
            </Select2>
            <span ref="footerExtensionInfo" class="upload-footer-extension-info upload-icon-button fa fa-search" />
            <span class="upload-footer-title">Genome/Build:</span>
            <Select2 ref="footerGenome" v-model="genome" container-class="upload-footer-genome" :enabled="!running">
                <option v-for="(listGenome, index) in listGenomes" :key="index" :value="listGenome.id">
                    {{ listGenome.text }}
                </option>
            </Select2>
        </template>
        <template v-slot:buttons>
            <b-button ref="btnClose" class="ui-button-default" :title="btnCloseTitle" @click="$emit('dismiss')">
                {{ btnCloseTitle | localize }}
            </b-button>
            <b-button
                id="btn-start"
                ref="btnStart"
                class="ui-button-default"
                :disabled="!readyStart"
                :title="btnStartTitle"
                :variant="readyStart ? 'primary' : ''"
                @click="_eventStart">
                {{ btnStartTitle }}
            </b-button>
            <b-button
                id="btn-reset"
                ref="btnReset"
                class="ui-button-default"
                :title="btnResetTitle"
                @click="_eventReset">
                {{ btnResetTitle }}
            </b-button>
        </template>
    </UploadWrapper>
</template>

<script>
import Select2 from "components/Select2";
import _ from "underscore";
import { refreshContentsWrapper } from "utils/data";
import _l from "utils/localization";
import { submitUpload } from "utils/uploadbox";

import { uploadModelsToPayload } from "./helpers";
import UploadModel from "./upload-model";
import UploadWrapper from "./UploadWrapper";

export default {
    components: {
        UploadWrapper,
        Select2,
    },
    props: {
        hasCallback: {
            type: Boolean,
            default: false,
        },
        details: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            extension: "_select_",
            genome: this.details.defaultDbKey,
            listExtensions: [],
            listGenomes: [],
            running: false,
            showHelper: true,
            btnResetTitle: _l("Reset"),
            btnStartTitle: _l("Start"),
            readyStart: false,
        };
    },
    computed: {
        extensions() {
            const result = _.filter(this.listExtensions, (ext) => ext.composite_files);
            result.unshift({ id: "_select_", text: "Select" });
            return result;
        },
        btnCloseTitle() {
            return this.hasCallback ? "Cancel" : "Close";
        },
    },
    watch: {
        extension: function (value) {
            this.collection.reset();
            const details = this.extensionDetails(value);
            if (details && details.composite_files) {
                _.each(details.composite_files, (item) => {
                    this.collection.add({
                        id: this.collection.size(),
                        file_desc: item.description || item.name,
                        optional: item.optional,
                    });
                });
            }
        },
    },
    created() {
        this.collection = new UploadModel.Collection();
        this.ftpUploadSite = this.details.currentFtp;
    },
    mounted() {
        // listener for collection triggers on change in composite datatype and extension selection
        this.collection.on("add", (model) => {
            this._eventAnnounce(model);
        });
        this.collection.on("change add", () => {
            this.renderNonReactiveComponents();
        });
        this.renderNonReactiveComponents();
    },
    methods: {
        renderNonReactiveComponents: function () {
            var model = this.collection.first();
            if (model && model.get("status") == "running") {
                this.running = true;
            } else {
                this.running = false;
            }
            if (
                this.collection.where({ status: "ready" }).length + this.collection.where({ optional: true }).length ==
                    this.collection.length &&
                this.collection.length > 0
            ) {
                this.readyStart = true;
            } else {
                this.readyStart = false;
            }
            this.showHelper = this.collection.length == 0;
        },

        //
        // upload events / process pipeline
        //

        /** Builds the basic ui with placeholder rows for each composite data type file */
        _eventAnnounce: function (model) {
            /*var upload_row = new UploadRow(this, { model: model });
            this.$uploadTable().find("tbody:first").append(upload_row.$el);
            this.showHelper = this.collection.length == 0;
            upload_row.render();*/
        },

        /** Start upload process */
        _eventStart: function () {
            this.collection.each((model) => {
                model.set({
                    genome: this.genome,
                    extension: this.extension,
                });
            });
            submitUpload({
                url: this.details.uploadPath,
                data: uploadModelsToPayload(this.collection.filter(), this.history_id, true),
                success: (message) => {
                    this._eventSuccess(message);
                },
                error: (message) => {
                    this._eventError(message);
                },
                progress: (percentage) => {
                    this._eventProgress(percentage);
                },
            });
        },

        /** Remove all */
        _eventReset: function () {
            if (this.collection.where({ status: "running" }).length == 0) {
                this.collection.reset();
                this.extension = this.details.defaultExtension;
                this.genome = this.details.defaultDbKey;
                this.renderNonReactiveComponents();
            }
        },

        /** Refresh progress state */
        _eventProgress: function (percentage) {
            this.collection.each((it) => {
                it.set("percentage", percentage);
            });
        },

        /** Refresh success state */
        _eventSuccess: function (message) {
            this.collection.each((it) => {
                it.set("status", "success");
            });
            refreshContentsWrapper();
        },

        /** Refresh error state */
        _eventError: function (message) {
            this.collection.each((it) => {
                it.set({ status: "error", info: message });
            });
        },
    },
};
</script>
