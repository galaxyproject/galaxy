import _l from "utils/localization";
import _ from "underscore";
import $ from "jquery";
import Select2 from "components/Select2";
import Popover from "mvc/ui/ui-popover";
import UploadExtension from "mvc/upload/upload-extension";
import UploadModel from "mvc/upload/upload-model";
import UploadWrapper from "./UploadWrapper";
import { getGalaxyInstance } from "app";
import UploadFtp from "mvc/upload/upload-ftp";
import LazyLimited from "mvc/lazy/lazy-limited";

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
    },
    methods: {
        $uploadBox() {
            return $(this.$refs.wrapper.$refs.uploadBox);
        },
        initUploadbox(options) {
            const $uploadBox = this.$uploadBox();
            this.uploadbox = $uploadBox.uploadbox(options);
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
                $.uploadpost({
                    data: this.app.toData(list),
                    url: this.app.uploadPath,
                    success: (message) => {
                        _.each(list, (model) => {
                            this._eventSuccess(model.id, message);
                        });
                    },
                    error: (message) => {
                        _.each(list, (model) => {
                            self._eventError(model.id, message);
                        });
                    },
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
            this.enableReset =
                this.counterRunning == 0 && this.counterAnnounce + this.counterSuccess + this.counterError > 0;
            this.enableStart = this.counterRunning == 0 && this.counterAnnounce > 0;
            this.enableBuild =
                this.counterRunning == 0 &&
                this.counterAnnounce == 0 &&
                this.counterSuccess > 0 &&
                this.counterError == 0;
            this.enableSources = this.counterRunning == 0;
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
        /** Show/hide ftp popup */
        _eventFtp: function () {
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
                            },
                        ]);
                    },
                    onremove: function (model_index) {
                        this.collection.remove(model_index);
                    },
                }).$el
            );
        },
        /** Create a new file */
        _eventCreate: function () {
            this.uploadbox.add([{ name: "New File", size: 0, mode: "new" }]);
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
            var details = _.findWhere(this.listExtensions, {
                id: extension,
            });
            return details;
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
            this.listExtensions = this.app.listExtensions;
            this.listGenomes = this.app.listGenomes;
            this.ftpUploadSite = this.app.currentFtp();
        },
        initFtpPopover() {
            // add ftp file viewer
            this.ftp = new Popover({
                title: _l("FTP files"),
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
    },
};
