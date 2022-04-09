import _l from "utils/localization";
import $ from "jquery";
import Select2 from "components/Select2";
import Popover from "mvc/ui/ui-popover";
import UploadExtension from "mvc/upload/upload-extension";
import UploadModel from "mvc/upload/upload-model";
import UploadWrapper from "./UploadWrapper";
import { defaultNewFileName, uploadModelsToPayload } from "./helpers";
import { getGalaxyInstance } from "app";
import UploadFtp from "mvc/upload/upload-ftp";
import LazyLimited from "mvc/lazy/lazy-limited";
import { findExtension } from "./utils";
import { filesDialog } from "utils/data";
import { getAppRoot } from "onload";
import { UploadQueue } from "utils/uploadbox";
import axios from "axios";

const localize = _l;

export default {
    components: {
        UploadWrapper,
        Select2,
    },
    props: {
        app: {
            type: Object,
            required: true,
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
    },
    computed: {
        btnFilesTitle() {
            if (this.fileSourcesConfigured) {
                return localize("Choose remote files");
            } else {
                return localize("Choose FTP files");
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
            const storeId = this.$store?.getters["history/currentHistoryId"];
            if (storeId) {
                return storeId;
            }
            const legacyId = this.app.currentHistory();
            return legacyId;
        },
    },
    methods: {
        $uploadBox() {
            return $(this.$refs.wrapper.$refs.uploadBox);
        },
        initUploadbox(options) {
            const $uploadBox = this.$uploadBox();
            options.$uploadBox = $uploadBox;
            this.uploadbox = new UploadQueue(options);
            if (this.lazyLoadMax !== null) {
                const $uploadBox = this.$uploadBox();
                this.loader = new LazyLimited({
                    $container: $uploadBox,
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
            this.appModel.set({ percentage: 0, status: "success" });
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
                const data = uploadModelsToPayload(list, this.history_id);
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
            this.appModel.set("percentage", this._uploadPercentage(percentage, it.get("file_size")));
        },
        /** Calculate percentage of all queued uploads */
        _uploadPercentage: function (percentage, size) {
            return (this.uploadCompleted + percentage * size) / this.uploadSize;
        },
        _updateStateForSuccess: function (model) {
            this.appModel.set("percentage", this._uploadPercentage(100, model.get("file_size")));
            this.uploadCompleted += model.get("file_size") * 100;
            this.counterAnnounce--;
            this.counterSuccess++;
            this._updateStateForCounters();
            const Galaxy = getGalaxyInstance();
            Galaxy.currHistoryPanel.refreshContents();
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
            this.appModel.set({
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
        /** Pause upload process */
        _eventStop: function () {
            if (this.counterRunning > 0) {
                this.appModel.set("status", "info");
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
            return findExtension(this.app.effectiveExtensions, extension);
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
            this.listExtensions = this.app.effectiveExtensions;
            this.listGenomes = this.app.listGenomes;
            this.ftpUploadSite = this.app.currentFtp();
            this.fileSourcesConfigured = this.app.fileSourcesConfigured;
        },
        initFtpPopover() {
            // add ftp file viewer
            this.ftp = new Popover({
                title: _l("FTP files"),
                class: "ftp-upload",
                container: $(this.$refs.btnFtp),
            });
        },
        /* walk collection and update un-modified default values when globals
           change */
        updateExtension(extension, defaults_only) {
            this.collection.each((model) => {
                if (
                    model.get("status") == "init" &&
                    (model.get("extension") == this.app.defaultExtension || !defaults_only)
                ) {
                    model.set("extension", extension);
                }
            });
        },
        updateGenome: function (genome, defaults_only) {
            this.collection.each((model) => {
                if (
                    model.get("status") == "init" &&
                    (model.get("genome") == this.app.defaultGenome || !defaults_only)
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
