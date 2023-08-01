<template>
    <div class="upload-view-default">
        <div class="upload-top">
            <div class="upload-top-info" v-html="topInfo" />
        </div>
        <div ref="uploadBox" class="upload-box upload-box-with-footer" :class="{ highlight: highlightBox }">
            <div v-show="showHelper" class="upload-helper"><i class="fa fa-files-o" />Drop files here</div>
            <div v-show="!showHelper" class="upload-table ui-table-striped">
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
        <div class="upload-footer text-center">
            <span class="upload-footer-title">Type (set all):</span>
            <UploadSettingsSelect
                :value="extension"
                :options="listExtensions"
                placeholder="Select Type"
                :disabled="running"
                @input="updateExtension" />
            <UploadExtensionDetails :extension="extension" :list-extensions="listExtensions" />
            <span class="upload-footer-title">Reference (set all):</span>
            <UploadSettingsSelect
                :value="genome"
                :options="listGenomes"
                :disabled="running"
                placeholder="Select Reference"
                @input="updateGenome" />
        </div>
        <div class="upload-buttons d-flex justify-content-end">
            <BButton id="btn-local" title="Choose local files" :disabled="!enableSources" @click="uploadSelect">
                <span class="fa fa-laptop"></span>
                <span v-localize>Choose local files</span>
            </BButton>
            <BButton
                v-if="!fileSourcesConfigured || !!ftpUploadSite"
                id="btn-remote-files"
                :disabled="!enableSources"
                @click="_eventRemoteFiles">
                <span class="fa fa-folder-open"></span>
                <span v-localize>Choose remote files</span>
            </BButton>
            <BButton id="btn-new" title="Paste/Fetch data" :disabled="!enableSources" @click="_eventCreate">
                <span class="fa fa-edit"></span>
                <span v-localize>Paste/Fetch data</span>
            </BButton>
            <BButton
                id="btn-start"
                :disabled="!enableStart"
                title="Start"
                :variant="enableStart ? 'primary' : ''"
                @click="_eventStart">
                <span v-localize>Start</span>
            </BButton>
            <BButton id="btn-stop" title="Pause" :disabled="counterRunning == 0" @click="_eventStop">
                <span v-localize>Pause</span>
            </BButton>
            <BButton id="btn-reset" title="Reset" :disabled="!enableReset" @click="_eventReset">
                <span v-localize>Reset</span>
            </BButton>
            <BButton id="btn-close" title="Close" @click="$emit('dismiss')">
                <span v-if="hasCallback" v-localize>Cancel</span>
                <span v-else v-localize>Close</span>
            </BButton>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import axios from "axios";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";
import UploadExtensionDetails from "./UploadExtensionDetails.vue";
import $ from "jquery";
import { getAppRoot } from "onload";
import { filesDialog } from "utils/data";
import { UploadQueue } from "utils/uploadbox";

import { defaultNewFileName, uploadModelsToPayload } from "./helpers";
import { findExtension } from "./utils";

import { BButton } from "bootstrap-vue";
import DefaultRow from "./DefaultRow.vue";
import { defaultModel } from "./model.js";

export default {
    components: { BButton, DefaultRow, UploadExtensionDetails, UploadSettingsSelect },
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
            counterAnnounce: 0,
            counterError: 0,
            counterRunning: 0,
            counterSuccess: 0,
            extension: this.details.defaultExtension,
            genome: this.details.defaultDbKey,
            highlightBox: false,
            listGenomes: [],
            running: false,
            uploadCompleted: 0,
            uploadList: {},
            uploadSize: 0,
            uploadUrl: null,
        };
    },
    computed: {
        showHelper() {
            return Object.keys(this.uploadList).length === 0;
        },
        listExtensions() {
            return this.allExtensions.filter((ext) => !ext.composite_files);
        },
        history_id() {
            return this.details.history_id;
        },
        counterNonRunning() {
            return this.counterAnnounce + this.counterSuccess + this.counterError;
        },
        enableReset() {
            return this.counterRunning == 0 && this.counterNonRunning > 0;
        },
        enableStart() {
            return this.counterRunning == 0 && this.counterAnnounce > 0;
        },
        enableSources() {
            return this.counterRunning == 0 && (this.multiple || this.counterNonRunning == 0);
        },
        topInfo() {
            var message = "";
            if (this.counterAnnounce == 0) {
                //TODO: if (this.uploadbox.compatible()) {
                message = "&nbsp;";
                //} else {
                //    message =
                //        "Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.";
                //}
            } else {
                if (this.counterRunning == 0) {
                    message = `You added ${this.counterAnnounce} file(s) to the queue. Add more files or click 'Start' to proceed.`;
                } else {
                    message = `Please wait...${this.counterAnnounce} out of ${this.counterRunning} remaining.`;
                }
            }
            return message;
        },
    },
    created() {
        this.allExtensions = this.details.effectiveExtensions;
        this.listGenomes = this.details.listGenomes;
        this.ftpUploadSite = this.details.currentFtp;
        this.fileSourcesConfigured = this.details.fileSourcesConfigured;
    },
    mounted() {
        this.initUploadbox();
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
        },

        /** Remove all */
        _eventReset: function () {
            if (this.counterRunning === 0) {
                this.counterAnnounce = 0;
                this.counterSuccess = 0;
                this.counterError = 0;
                this.counterRunning = 0;
                this.uploadbox.reset();
                this.uploadList = {};
                this.extension = this.details.defaultExtension;
                this.genome = this.details.defaultDbKey;
                this.details.model.set("percentage", 0);
            }
        },
        initUploadbox() {
            this.uploadbox = new UploadQueue({
                $uploadBox: this.$refs.uploadBox,
                initUrl: (index) => {
                    if (!this.uploadUrl) {
                        this.uploadUrl = `${getAppRoot()}api/tools/fetch`;
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
            Object.values(this.uploadList).forEach((model) => {
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
        },

        /** Package and upload ftp files in a single request */
        _uploadFtp: function () {
            const list = [];
            Object.values(this.uploadList).forEach((model) => {
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
            Vue.set(this.uploadList, index, uploadModel);
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
        },
        /** Queue is done */
        _eventComplete: function () {
            Object.values(this.uploadList).forEach((model) => {
                if (model.status === "queued") {
                    model.status = "init";
                }
            });
            this.counterRunning = 0;
        },
        /** Remove model from upload list */
        _eventRemove: function (index) {
            const it = this.uploadList[index];
            var status = it.status;
            if (status == "success") {
                this.counterSuccess--;
            } else if (status == "error") {
                this.counterError--;
            } else {
                this.counterAnnounce--;
            }
            Vue.delete(this.uploadList, index);
            this.uploadbox.remove(index);
        },
        /** Show remote files dialog or FTP files */
        _eventRemoteFiles: function () {
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
        },
        /** Create a new file */
        _eventCreate: function () {
            this.uploadbox.add([{ name: defaultNewFileName, size: 0, mode: "new" }]);
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
        /* update un-modified default values when globals change */
        updateExtension(newExtension) {
            this.extension = newExtension;
            Object.values(this.uploadList).forEach((model) => {
                if (model.status === "init" && model.extension === this.details.defaultExtension) {
                    model.extension = newExtension;
                }
            });
        },
        updateGenome: function (newGenome) {
            Object.values(this.uploadList).forEach((model) => {
                if (model.status === "init" && model.genome === this.details.defaultDbKey) {
                    model.genome = newGenome;
                }
            });
        },
    },
};
</script>
<style scoped>
.upload-box-with-footer {
    height: 300px;
}
</style>
