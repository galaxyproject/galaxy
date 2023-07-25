<template>
    <div ref="wrapper" class="upload-view-default">
        <div class="upload-top">
            <div class="upload-top-info" v-html="topInfo"></div>
        </div>
        <div ref="uploadBox" class="upload-box" :style="boxStyle" :class="{ highlight: highlightBox }">
            <div v-show="showHelper" class="upload-helper"><i class="fa fa-files-o" />Drop files here</div>
            <table v-show="!showHelper" ref="uploadTable" class="upload-table ui-table-striped">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Type</th>
                        <th>Genome</th>
                        <th>Settings</th>
                        <th>Status</th>
                        <th />
                    </tr>
                </thead>
                <tbody />
            </table>
        </div>
        <div v-if="hasFooter" class="upload-footer">
            <span class="upload-footer-title">Type (set all):</span>
            <select2
                ref="footerExtension"
                v-model="extension"
                container-class="upload-footer-extension"
                :enabled="!running">
                <option v-for="(ext, index) in extensions" :key="index" :value="ext.id">{{ ext.text }}</option>
            </select2>
            <span class="upload-footer-extension-info upload-icon-button fa fa-search" />
            <span class="upload-footer-title">Genome (set all):</span>
            <select2 ref="footerGenome" v-model="genome" container-class="upload-footer-genome" :enabled="!running">
                <option v-for="(listGenome, index) in listGenomes" :key="index" :value="listGenome.id">
                    {{ listGenome.text }}
                </option>
            </select2>
        </div>
        <div v-else class="clear" />
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
import Select2 from "components/Select2";
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
import LazyLimited from "./lazy-limited";
import { findExtension } from "./utils";

import { BButton } from "bootstrap-vue";
import UploadRow from "mvc/upload/default/default-row";

export default {
    components: { BButton, Select2 },
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
            uploadUrl: null,
            topInfo: "",
            highlightBox: false,
            showHelper: true,
            extension: this.details.defaultExtension,
            genome: this.details.defaultDbKey,
            listExtensions: [],
            listGenomes: [],
            running: false,
            rowUploadModel: UploadRow,
            counterAnnounce: 0,
            counterSuccess: 0,
            counterError: 0,
            counterRunning: 0,
            uploadSize: 0,
            uploadCompleted: 0,
            enableReset: false,
            enableStart: false,
            enableSources: false,
            btnLocalTitle: _l("Choose local files"),
            btnCreateTitle: _l("Paste/Fetch data"),
            btnStartTitle: _l("Start"),
            btnStopTitle: _l("Pause"),
            btnResetTitle: _l("Reset"),
        };
    },
    computed: {
        extensions() {
            const result = this.listExtensions.filter((ext) => !ext.composite_files);
            return result;
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
        hasFooter() {
            // https://stackoverflow.com/questions/44077277/only-show-slot-if-it-has-content/50096300#50096300
            const name = "footer";
            return !!this.$slots[name] || !!this.$scopedSlots[name];
        },
        boxStyle: function () {
            return {
                height: this.hasFooter ? "300px" : "335px",
            };
        },
    },
    watch: {
        extension: function (value) {
            this.updateExtension(value);
        },
        genome: function (value) {
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
        this.collection.on("remove", (model) => {
            this._eventRemove(model);
        });
        this._updateStateForCounters();
    },
    methods: {
        _newUploadModelProps: function (index, file) {
            return {
                id: index,
                file_name: file.name,
                file_size: file.size,
                file_mode: file.mode || "local",
                file_path: file.path,
                file_uri: file.uri,
                file_data: file,
            };
        },

        /** Success */
        _eventSuccess: function (index) {
            var it = this.collection.get(index);
            it.set({ percentage: 100, status: "success" });
            this._updateStateForSuccess(it);
        },

        /** Remove all */
        _eventReset: function () {
            if (this.counterRunning === 0) {
                this.collection.reset();
                this.counterAnnounce = 0;
                this.counterSuccess = 0;
                this.counterError = 0;
                this.counterRunning = 0;
                this.uploadbox.reset();
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
                        this.uploadUrl = this.getRequestUrl([this.collection.get(index)], this.history_id);
                    }
                    return this.uploadUrl;
                },
                multiple: this.multiple,
                announce: (index, file) => {
                    this._eventAnnounce(index, file);
                },
                initialize: (index) => {
                    return uploadModelsToPayload([this.collection.get(index)], this.history_id);
                },
                progress: (index, percentage) => {
                    this._eventProgress(index, percentage);
                },
                success: (index, message) => {
                    this._eventSuccess(index, message);
                },
                error: (index, message) => {
                    this._eventError(index, message);
                },
                warning: (index, message) => {
                    this._eventWarning(index, message);
                },
                complete: () => {
                    this._eventComplete();
                },
                ondragover: () => {
                    this.highlightBox = true;
                },
                ondragleave: () => {
                    this.highlightBox = false;
                },
                chunkSize: this.details.chunkUploadSize,
            });
            if (this.lazyLoadMax !== null) {
                this.loader = new LazyLimited({
                    $container: this.$refs.uploadBox,
                    collection: this.collection,
                    max: this.lazyLoadMax,
                    new_content: (model) => {
                        return this.renderNewModel(model);
                    },
                });
            }
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
            this.collection.each((model) => {
                if (model.get("status") == "init") {
                    model.set("status", "queued");
                    this.uploadSize += model.get("file_size");
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
            this.collection.each((model) => {
                if (model.get("status") == "queued" && model.get("file_mode") == "ftp") {
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
        renderNewModel: function (model) {
            // Turn backbone upload model into row model and place in table,
            // render in next tick so table can respond first and dynamic
            // sizing works.
            var uploadRow = new this.rowUploadModel(this, { model: model });
            this.$uploadTable().find("tbody:first").append(uploadRow.$el);
            this._updateStateForCounters();
            this.$nextTick(() => {
                uploadRow.render();
            });
            return uploadRow;
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
            this.showHelper = !show_table;
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
            var it = this.collection.get(index);
            it.set("percentage", percentage);
            this.details.model.set("percentage", this._uploadPercentage(percentage, it.get("file_size")));
        },
        /** Calculate percentage of all queued uploads */
        _uploadPercentage: function (percentage, size) {
            return (this.uploadCompleted + percentage * size) / this.uploadSize;
        },
        _updateStateForSuccess: function (model) {
            this.details.model.set("percentage", this._uploadPercentage(100, model.get("file_size")));
            this.uploadCompleted += model.get("file_size") * 100;
            this.counterAnnounce--;
            this.counterSuccess++;
            this._updateStateForCounters();
            refreshContentsWrapper();
        },
        /** A new file has been dropped/selected through the uploadbox plugin */
        _eventAnnounce: function (index, file) {
            this.counterAnnounce++;
            const modelProps = this._newUploadModelProps(index, file);
            var newModel = new UploadModel.Model(modelProps);
            this.collection.add(newModel);
            // if using lazyLoader, let it handle it - else render directly
            if (this.loader) {
                this._updateStateForCounters();
            } else {
                this.renderNewModel(newModel);
            }
        },
        /** Error */
        _eventError: function (index, message) {
            var it = this.collection.get(index);
            it.set({ percentage: 100, status: "error", info: message });
            this.details.model.set({
                percentage: this._uploadPercentage(100, it.get("file_size")),
                status: "danger",
            });
            this.uploadCompleted += it.get("file_size") * 100;
            this.counterAnnounce--;
            this.counterError++;
            this._updateStateForCounters();
        },
        /** Queue is done */
        _eventComplete: function () {
            this.collection.each((model) => {
                model.get("status") == "queued" && model.set("status", "init");
            });
            this.counterRunning = 0;
            this._updateStateForCounters();
        },
        /** Remove model from upload list */
        _eventRemove: function (model) {
            var status = model.get("status");
            if (status == "success") {
                this.counterSuccess--;
            } else if (status == "error") {
                this.counterError--;
            } else {
                this.counterAnnounce--;
            }
            this.uploadbox.remove(model.id);
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
            var it = this.collection.get(index);
            it.set({ status: "warning", info: message });
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
                            list: this.listExtensions,
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
            this.listExtensions = this.details.effectiveExtensions;
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
        updateExtension(extension, defaults_only) {
            this.collection.each((model) => {
                if (
                    model.get("status") == "init" &&
                    (model.get("extension") == this.details.defaultExtension || !defaults_only)
                ) {
                    model.set("extension", extension);
                }
            });
        },
        updateGenome: function (genome, defaults_only) {
            this.collection.each((model) => {
                if (
                    model.get("status") == "init" &&
                    (model.get("genome") == this.details.defaultDbKey || !defaults_only)
                ) {
                    model.set("genome", genome);
                }
            });
        },
        getRequestUrl: function (items, history_id) {
            return `${getAppRoot()}api/tools/fetch`;
        },
    },
};
</script>
