<template>
    <div class="upload-view-default">
        <div class="upload-top">
            <div class="upload-top-info" v-html="topInfo" />
        </div>
        <div ref="uploadBox" class="upload-box upload-box-with-footer" :class="{ highlight: highlightBox }">
            <div v-show="showHelper" class="upload-helper"><i class="fa fa-files-o" />Drop files here</div>
            <div v-show="!showHelper" ref="uploadTable" class="upload-table ui-table-striped">
                <DefaultRow
                    v-for="(uploadItem, uploadIndex) in uploadList"
                    :key="uploadIndex"
                    :index="uploadIndex"
                    :deferred="uploadItem.deferred"
                    :extension="uploadItem.extension"
                    :file-content="uploadItem.file_content"
                    :file-mode="uploadItem.file_mode"
                    :file-name="uploadItem.file_name"
                    :file-size="uploadItem.file_size"
                    :genome="uploadItem.genome"
                    :listExtensions="listExtensions"
                    :listGenomes="listGenomes"
                    :percentage="uploadItem.percentage"
                    :space_to_tab="uploadItem.space_to_tab"
                    :status="uploadItem.status"
                    :to_posix_lines="uploadItem.to_posix_lines"
                    @remove="_eventRemove"
                    @input="_eventInput" />
            </div>
        </div>
        <div class="upload-footer">
            <span class="upload-footer-title">Type (set all):</span>
            <UploadSettingsSelect
                :value="extension"
                :options="listExtensions"
                :disabled="running"
                @input="updateExtension" />
            <span class="upload-footer-extension-info upload-icon-button fa fa-search" />
            <span class="upload-footer-title">Genome (set all):</span>
            <UploadSettingsSelect :value="genome" :options="listGenomes" :disabled="running" @input="updateGenome" />
        </div>
        <div class="upload-buttons">
            <BButton
                id="btn-close"
                ref="btnClose"
                class="ui-button-default upload-close"
                :title="btnCloseTitle"
                @click="$emit('dismiss')">
                {{ btnCloseTitle }}
            </BButton>
            <BButton
                id="btn-reset"
                ref="btnReset"
                class="ui-button-default"
                :title="btnResetTitle"
                :disabled="!enableReset"
                @click="_eventReset">
                {{ btnResetTitle }}
            </BButton>
            <BButton
                id="btn-stop"
                ref="btnStop"
                class="ui-button-default"
                :title="btnStopTitle"
                :disabled="counterRunning == 0"
                @click="_eventStop">
                {{ btnStopTitle }}
            </BButton>
            <BButton
                id="btn-start"
                ref="btnStart"
                class="ui-button-default upload-start"
                :disabled="!enableStart"
                :title="btnStartTitle"
                :variant="enableStart ? 'primary' : ''"
                @click="_eventStart">
                {{ btnStartTitle }}
            </BButton>
            <BButton
                id="btn-new"
                ref="btnCreate"
                class="ui-button-default upload-paste"
                :title="btnCreateTitle"
                :disabled="!enableSources"
                @click="_eventCreate()">
                <span class="fa fa-edit"></span>{{ btnCreateTitle }}
            </BButton>
            <BButton
                v-if="remoteFiles"
                id="btn-ftp"
                ref="btnFtp"
                class="ui-button-default"
                :disabled="!enableSources"
                @click="_eventRemoteFiles">
                <span class="fa fa-folder-open-o"></span>{{ btnFilesTitle }}
            </BButton>
            <BButton
                id="btn-local"
                ref="btnLocal"
                class="ui-button-default"
                :title="btnLocalTitle"
                :disabled="!enableSources"
                @click="uploadSelect">
                <span class="fa fa-laptop"></span>{{ btnLocalTitle }}
            </BButton>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";
import $ from "jquery";
import Popover from "mvc/ui/ui-popover";
import UploadExtension from "mvc/upload/upload-extension";
import UploadFtp from "mvc/upload/upload-ftp";
import UploadModel from "mvc/upload/upload-model";
import { getAppRoot } from "onload";
import { filesDialog, refreshContentsWrapper } from "utils/data";
import _l from "utils/localization";
import { UploadQueue } from "utils/uploadbox";

import { defaultNewFileName, uploadModelsToPayload } from "./helpers";
import { findExtension } from "./utils";

import { BButton } from "bootstrap-vue";
import DefaultRow from "./DefaultRow.vue";
import { defaultModel } from "./model.js";

export default {
    components: { BButton, DefaultRow, UploadSettingsSelect },
    props: {
        multiple: {
            type: Boolean,
            default: true,
        },
        lazyLoadMax: {
            type: Number,
            default: null,
        },
        selectable: {
            type: Boolean,
            default: false,
        },
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
            allExtensions: [],
            btnCreateTitle: _l("Paste/Fetch data"),
            btnLocalTitle: _l("Choose local files"),
            btnResetTitle: _l("Reset"),
            btnStartTitle: _l("Start"),
            btnStopTitle: _l("Pause"),
            counterAnnounce: 0,
            counterError: 0,
            counterRunning: 0,
            counterSuccess: 0,
            enableReset: false,
            enableStart: false,
            enableSources: false,
            extension: this.details.defaultExtension,
            genome: this.details.defaultDbKey,
            highlightBox: false,
            listGenomes: [],
            running: false,
            topInfo: "",
            uploadCompleted: 0,
            uploadList: [],
            uploadSize: 0,
            uploadUrl: null,
        };
    },
    computed: {
        showHelper() {
            return this.uploadList.length === 0;
        },
        listExtensions() {
            return this.allExtensions.filter((ext) => !ext.composite_files);
        },
        btnFilesTitle() {
            if (this.fileSourcesConfigured) {
                return _l("Choose remote files");
            } else {
                return _l("Choose FTP files");
            }
        },
        remoteFiles() {
            // this needs to be true for the tests to pass
            return !!this.fileSourcesConfigured || !!this.ftpUploadSite;
        },
        btnCloseTitle() {
            return this.hasCallback ? "Cancel" : "Close";
        },
        history_id() {
            return this.details.history_id;
        },
    },
    watch: {
        extension: (value) => {
            this.updateExtension(value);
        },
        genome: (value) => {
            this.updateGenome(value);
        },
    },
    created() {
        this.initCollection();
        this.initAppProperties();
    },
    mounted() {
        this.initExtensionInfo();
        this.initFtpPopover();
        this.initUploadbox();
        this._updateStateForCounters();
    },
    methods: {
        /** Update model */
        _eventInput: function (index, newData) {
            const it = this.uploadList[index];
            Object.entries(newData).forEach(([key, value]) => {
                it[key] = value;
            });
        },

        /** Success */
        _eventSuccess: function (index) {
            var it = this.uploadList[index];
            it.percentage = 100;
            it.status = "success";
            this.details.model.set("percentage", this._uploadPercentage(100, it.file_size));
            this.uploadCompleted += it.file_size * 100;
            this.counterAnnounce--;
            this.counterSuccess++;
            this._updateStateForCounters();
            refreshContentsWrapper();
        },

        /** Remove all */
        _eventReset: function () {
            if (this.counterRunning === 0) {
                this.counterAnnounce = 0;
                this.counterSuccess = 0;
                this.counterError = 0;
                this.counterRunning = 0;
                this.uploadbox.reset();
                this.uploadList = [];
                this.extension = this.details.defaultExtension;
                this.genome = this.details.defaultDbKey;
                this.details.model.set("percentage", 0);
                this._updateStateForCounters();
            }
        },
        initUploadbox() {
            this.uploadbox = new UploadQueue({
                $uploadBox: this.$refs.uploadBox,
                initUrl: (index) => {
                    if (!this.uploadUrl) {
                        this.uploadUrl = this.getRequestUrl([this.uploadList[index]], this.history_id);
                    }
                    return this.uploadUrl;
                },
                multiple: this.multiple,
                announce: this._eventAnnounce,
                initialize: (index) => {
                    return uploadModelsToPayload([this.uploadList[index]], this.history_id);
                },
                progress: this._eventProgress,
                success: this._eventSuccess,
                error: this._eventError,
                warning: this._eventWarning,
                complete: this._eventComplete,
                ondragover: () => {
                    this.highlightBox = true;
                },
                ondragleave: () => {
                    this.highlightBox = false;
                },
                chunkSize: this.details.chunkUploadSize,
            });
        },
        uploadSelect: function () {
            this.uploadbox.select();
        },

        /** Start upload process */
        _eventStart: function () {
            if (this.counterAnnounce == 0 || this.counterRunning > 0) {
                return;
            }
            this.uploadSize = 0;
            this.uploadCompleted = 0;
            this.uploadList.forEach((model) => {
                if (model.status === "init") {
                    model.status = "queued";
                    this.uploadSize += model.file_size;
                }
            });
            this.details.model.set({ percentage: 0, status: "success" });
            this.counterRunning = this.counterAnnounce;

            // package ftp files separately, and remove them from queue
            this._uploadFtp();
            this.uploadbox.start();
            this._updateStateForCounters();
        },

        /** Package and upload ftp files in a single request */
        _uploadFtp: function () {
            const list = [];
            this.uploadList.forEach((model) => {
                if (model.status === "queued" && model.file_mode === "ftp") {
                    this.uploadbox.remove(model.id);
                    list.push(model);
                }
            });
            if (list.length > 0) {
                const data = uploadModelsToPayload(list, this.details.history_id);
                axios
                    .post(`${getAppRoot()}api/tools/fetch`, data)
                    .then((message) => {
                        list.forEach((model) => {
                            this._eventSuccess(model.id, message);
                        });
                    })
                    .catch((message) => {
                        list.forEach((model) => {
                            this._eventError(model.id, message);
                        });
                    });
            }
        },
        _updateStateForCounters: function () {
            this.setTopInfoBasedOnCounters();
            const counterNonRunning = this.counterAnnounce + this.counterSuccess + this.counterError;
            this.enableReset = this.counterRunning == 0 && counterNonRunning > 0;
            this.enableStart = this.counterRunning == 0 && this.counterAnnounce > 0;
            this.enableBuild =
                this.counterRunning == 0 &&
                this.counterAnnounce == 0 &&
                this.counterSuccess > 0 &&
                this.counterError == 0;
            this.enableSources = this.counterRunning == 0 && (this.multiple || counterNonRunning == 0);
            var show_table = this.counterAnnounce + this.counterSuccess + this.counterError > 0;
        },
        setTopInfoBasedOnCounters: function () {
            var message = "";
            if (this.counterAnnounce == 0) {
                if (this.uploadbox.compatible()) {
                    message = "&nbsp;";
                } else {
                    message =
                        "Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.";
                }
            } else {
                if (this.counterRunning == 0) {
                    message = `You added ${this.counterAnnounce} file(s) to the queue. Add more files or click 'Start' to proceed.`;
                } else {
                    message = `Please wait...${this.counterAnnounce} out of ${this.counterRunning} remaining.`;
                }
            }
            this.topInfo = message;
        },
        /** Progress */
        _eventProgress: function (index, percentage) {
            const it = this.uploadList[index];
            it.percentage = percentage;
            this.details.model.set("percentage", this._uploadPercentage(percentage, it.file_size));
        },
        /** Calculate percentage of all queued uploads */
        _uploadPercentage: function (percentage, size) {
            return (this.uploadCompleted + percentage * size) / this.uploadSize;
        },
        /** A new file has been dropped/selected through the uploadbox plugin */
        _eventAnnounce: function (index, file) {
            this.counterAnnounce++;
            const uploadModel = {
                ...defaultModel,
                id: index,
                file_name: file.name,
                file_size: file.size,
                file_mode: file.mode || "local",
                file_path: file.path,
                file_uri: file.uri,
                file_data: file,
            };
            this.uploadList.push(uploadModel);
            var newModel = new UploadModel.Model(uploadModel);
            this.collection.add(newModel);
            this._updateStateForCounters();
        },
        /** Error */
        _eventError: function (index, message) {
            var it = this.uploadList[index];
            it.percentage = 100;
            it.status = "error";
            it.info = message;
            this.details.model.set({
                percentage: this._uploadPercentage(100, it.file_size),
                status: "danger",
            });
            this.uploadCompleted += it.file_size * 100;
            this.counterAnnounce--;
            this.counterError++;
            this._updateStateForCounters();
        },
        /** Queue is done */
        _eventComplete: function () {
            this.uploadList.forEach((model) => {
                if (model.status === "queued") {
                    model.status = "init";
                }
            });
            this.counterRunning = 0;
            this._updateStateForCounters();
        },
        /** Remove model from upload list */
        _eventRemove: function (id) {
            const it = this.uploadList[id];
            var status = it.status;
            if (status == "success") {
                this.counterSuccess--;
            } else if (status == "error") {
                this.counterError--;
            } else {
                this.counterAnnounce--;
            }
            this.uploadList.splice(id, 1);
            this.uploadbox.remove(id);
            this._updateStateForCounters();
        },
        /** Show remote files dialog or FTP files */
        _eventRemoteFiles: function () {
            if (this.fileSourcesConfigured) {
                filesDialog(
                    (items) => {
                        this.uploadbox.add(
                            items.map((item) => {
                                const rval = {
                                    mode: "ftp",
                                    name: item.label,
                                    size: item.size,
                                    path: item.url,
                                };
                                return rval;
                            })
                        );
                    },
                    { multiple: true }
                );
            } else {
                this.ftp.show(
                    new UploadFtp({
                        collection: this.collection,
                        ftp_upload_site: this.ftpUploadSite,
                        onadd: (ftp_file) => {
                            return this.uploadbox.add([
                                {
                                    mode: "ftp",
                                    name: ftp_file.path,
                                    size: ftp_file.size,
                                    path: ftp_file.path,
                                    uri: ftp_file.uri,
                                },
                            ]);
                        },
                        onremove: function (model_index) {
                            this.collection.remove(model_index);
                        },
                    }).$el
                );
            }
        },
        /** Create a new file */
        _eventCreate: function () {
            this.uploadbox.add([{ name: defaultNewFileName, size: 0, mode: "new" }]);
        },
        addFiles: function (files) {
            this.uploadbox.add(files);
        },
        /** Pause upload process */
        _eventStop: function () {
            if (this.counterRunning > 0) {
                this.details.model.set("status", "info");
                this.topInfo = "Queue will pause after completing the current file...";
                this.uploadbox.stop();
            }
        },
        _eventWarning: function (index, message) {
            const it = this.uploadList[index];
            it.status = "warning";
            it.info = message;
        },
        $uploadTable() {
            return $(this.$refs.uploadTable);
        },
        extensionDetails(extension) {
            return findExtension(this.details.effectiveExtensions, extension);
        },
        initExtensionInfo() {
            $(this.$refs.footerExtensionInfo)
                .on("click", (e) => {
                    const details = this.extensionDetails(this.extension);
                    if (details) {
                        new UploadExtension({
                            $el: $(e.target),
                            title: details && details.text,
                            extension: details && details.id,
                            list: this.allExtensions,
                            placement: "top",
                        });
                    }
                })
                .on("mousedown", (e) => {
                    e.preventDefault();
                });
        },
        initCollection() {
            this.collection = new UploadModel.Collection();
        },
        initAppProperties() {
            this.allExtensions = this.details.effectiveExtensions;
            this.listGenomes = this.details.listGenomes;
            this.ftpUploadSite = this.details.currentFtp;
            this.fileSourcesConfigured = this.details.fileSourcesConfigured;
        },
        initFtpPopover() {
            // add ftp file viewer
            this.ftp = new Popover({
                title: _l("FTP files"),
                class: "ftp-upload",
                container: this.$refs.btnFtp,
            });
        },
        /* walk collection and update un-modified default values when globals
           change */
        updateExtension(newExtension) {
            this.uploadList.forEach((model) => {
                if (model.status === "init" && model.extension === this.details.defaultExtension) {
                    model.extension = newExtension;
                }
            });
        },
        updateGenome: function (newGenome) {
            this.uploadList.forEach((model) => {
                if (model.status === "init" && model.genome === this.details.defaultDbKey) {
                    model.genome = newGenome;
                }
            });
        },
        getRequestUrl: function (items, history_id) {
            return `${getAppRoot()}api/tools/fetch`;
        },
    },
};
</script>
<style scoped>
.upload-box-with-footer {
    height: 300px;
}
</style>
