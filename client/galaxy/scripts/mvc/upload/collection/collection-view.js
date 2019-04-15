/** Renders contents of the collection uploader */

import _l from "utils/localization";
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import UploadModel from "mvc/upload/upload-model";
import UploadRow from "mvc/upload/collection/collection-row";
import UploadFtp from "mvc/upload/upload-ftp";
import UploadExtension from "mvc/upload/upload-extension";
import Popover from "mvc/ui/ui-popover";
import Select from "mvc/ui/ui-select";
import Ui from "mvc/ui/ui-misc";
import "utils/uploadbox";

export default Backbone.View.extend({
    // current upload size in bytes
    upload_size: 0,

    // contains upload row models
    collection: new UploadModel.Collection(),

    // keeps track of the current uploader state
    counter: {
        announce: 0,
        success: 0,
        error: 0,
        running: 0,
        reset: function() {
            this.announce = this.success = this.error = this.running = 0;
        }
    },

    initialize: function(app) {
        var self = this;
        this.app = app;
        this.options = app.options;
        this.list_extensions = app.list_extensions;
        this.list_genomes = app.list_genomes;
        this.ui_button = app.ui_button;
        this.ftp_upload_site = app.currentFtp();
        this.setElement(this._template());

        // append buttons to dom
        this.btnLocal = new Ui.Button({
            id: "btn-local",
            title: _l("Choose local files"),
            onclick: function() {
                self.uploadbox.select();
            },
            icon: "fa fa-laptop"
        });
        this.btnFtp = new Ui.Button({
            id: "btn-ftp",
            title: _l("Choose FTP files"),
            onclick: function() {
                self._eventFtp();
            },
            icon: "fa fa-folder-open-o"
        });
        this.btnCreate = new Ui.Button({
            id: "btn-new",
            title: "Paste/Fetch data",
            onclick: function() {
                self._eventCreate();
            },
            icon: "fa fa-edit"
        });
        this.btnStart = new Ui.Button({
            id: "btn-start",
            title: _l("Start"),
            onclick: function() {
                self._eventStart();
            }
        });
        this.btnBuild = new Ui.Button({
            id: "btn-build",
            title: _l("Build"),
            onclick: function() {
                self._eventBuild();
            }
        });
        this.btnStop = new Ui.Button({
            id: "btn-stop",
            title: _l("Pause"),
            onclick: function() {
                self._eventStop();
            }
        });
        this.btnReset = new Ui.Button({
            id: "btn-reset",
            title: _l("Reset"),
            onclick: function() {
                self._eventReset();
            }
        });
        this.btnClose = new Ui.Button({
            id: "btn-close",
            title: _l("Close"),
            onclick: function() {
                self.app.modal.hide();
            }
        });
        _.each(
            [
                this.btnLocal,
                this.btnFtp,
                this.btnCreate,
                this.btnStop,
                this.btnReset,
                this.btnStart,
                this.btnBuild,
                this.btnClose
            ],
            button => {
                self.$(".upload-buttons").prepend(button.$el);
            }
        );

        // file upload
        this.uploadbox = this.$(".upload-box").uploadbox({
            url: this.app.options.upload_path,
            announce: function(index, file) {
                self._eventAnnounce(index, file);
            },
            initialize: function(index) {
                return self.app.toData([self.collection.get(index)], self.history_id);
            },
            progress: function(index, percentage) {
                self._eventProgress(index, percentage);
            },
            success: function(index, message) {
                self._eventSuccess(index, message);
            },
            error: function(index, message) {
                self._eventError(index, message);
            },
            complete: function() {
                self._eventComplete();
            },
            ondragover: function() {
                self.$(".upload-box").addClass("highlight");
            },
            ondragleave: function() {
                self.$(".upload-box").removeClass("highlight");
            }
        });

        // add ftp file viewer
        this.ftp = new Popover({
            title: _l("FTP files"),
            container: this.btnFtp.$el
        });

        // select extension
        this.select_extension = new Select.View({
            container: this.$(".upload-footer-extension"),
            data: _.filter(this.list_extensions, ext => !ext.composite_files),
            value: this.options.default_extension,
            onchange: function(extension) {
                self.updateExtension(extension);
            }
        });

        this.collectionType = "list";
        this.select_collection = new Select.View({
            container: this.$(".upload-footer-collection-type"),
            data: [
                { id: "list", text: "List" },
                { id: "paired", text: "Paired" },
                { id: "list:paired", text: "List of Pairs" }
            ],
            value: "list",
            onchange: function(collectionType) {
                self.updateCollectionType(collectionType);
            }
        });

        // handle extension info popover
        this.$(".upload-footer-extension-info")
            .on("click", e => {
                new UploadExtension({
                    $el: $(e.target),
                    title: self.select_extension.text(),
                    extension: self.select_extension.value(),
                    list: self.list_extensions,
                    placement: "top"
                });
            })
            .on("mousedown", e => {
                e.preventDefault();
            });

        // genome extension
        this.select_genome = new Select.View({
            css: "upload-footer-selection",
            container: this.$(".upload-footer-genome"),
            data: this.list_genomes,
            value: this.options.default_genome,
            onchange: function(genome) {
                self.updateGenome(genome);
            }
        });

        // events
        this.collection.on("remove", model => {
            self._eventRemove(model);
        });
        this._updateScreen();
    },

    /** A new file has been dropped/selected through the uploadbox plugin */
    _eventAnnounce: function(index, file) {
        this.counter.announce++;
        var new_model = new UploadModel.Model({
            id: index,
            file_name: file.name,
            file_size: file.size,
            file_mode: file.mode || "local",
            file_path: file.path,
            file_data: file,
            extension: this.select_extension.value(),
            genome: this.select_genome.value()
        });
        this.collection.add(new_model);
        var upload_row = new UploadRow(this, { model: new_model });
        this.$(".upload-table > tbody:first").append(upload_row.$el);
        this._updateScreen();
        upload_row.render();
    },

    /** Progress */
    _eventProgress: function(index, percentage) {
        var it = this.collection.get(index);
        it.set("percentage", percentage);
        this.ui_button.model.set("percentage", this._uploadPercentage(percentage, it.get("file_size")));
    },

    /** Success */
    _eventSuccess: function(index, message) {
        // var hdaId = message["outputs"][0]["id"];
        var hids = _.pluck(message["outputs"], "hid");
        var it = this.collection.get(index);
        it.set({ percentage: 100, status: "success", hids: hids });
        this.ui_button.model.set("percentage", this._uploadPercentage(100, it.get("file_size")));
        this.upload_completed += it.get("file_size") * 100;
        this.counter.announce--;
        this.counter.success++;
        this._updateScreen();
        let Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel.refreshContents();
    },

    /** Error */
    _eventError: function(index, message) {
        var it = this.collection.get(index);
        it.set({ percentage: 100, status: "error", info: message });
        this.ui_button.model.set({
            percentage: this._uploadPercentage(100, it.get("file_size")),
            status: "danger"
        });
        this.upload_completed += it.get("file_size") * 100;
        this.counter.announce--;
        this.counter.error++;
        this._updateScreen();
    },

    /** Queue is done */
    _eventComplete: function() {
        this.collection.each(model => {
            model.get("status") == "queued" && model.set("status", "init");
        });
        this.counter.running = 0;
        this._updateScreen();
    },

    _eventBuild: function() {
        let Galaxy = getGalaxyInstance();
        var allHids = [];
        _.forEach(this.collection.models, upload => {
            allHids.push.apply(allHids, upload.get("hids"));
        });
        var models = _.map(allHids, hid => Galaxy.currHistoryPanel.collection.getByHid(hid));
        var selection = new Galaxy.currHistoryPanel.collection.constructor(models);
        // I'm building the selection wrong because I need to set this historyId directly.
        selection.historyId = Galaxy.currHistoryPanel.collection.historyId;
        Galaxy.currHistoryPanel.buildCollection(this.collectionType, selection, true);
        this.counter.running = 0;
        this._updateScreen();
        this._eventReset();
        this.app.modal.hide();
    },

    /** Remove model from upload list */
    _eventRemove: function(model) {
        var status = model.get("status");
        if (status == "success") {
            this.counter.success--;
        } else if (status == "error") {
            this.counter.error--;
        } else {
            this.counter.announce--;
        }
        this.uploadbox.remove(model.id);
        this._updateScreen();
    },

    //
    // events triggered by this view
    //

    /** Show/hide ftp popup */
    _eventFtp: function() {
        var self = this;
        this.ftp.show(
            new UploadFtp({
                collection: this.collection,
                ftp_upload_site: this.ftp_upload_site,
                onadd: function(ftp_file) {
                    return self.uploadbox.add([
                        {
                            mode: "ftp",
                            name: ftp_file.path,
                            size: ftp_file.size,
                            path: ftp_file.path
                        }
                    ]);
                },
                onremove: function(model_index) {
                    self.collection.remove(model_index);
                }
            }).$el
        );
    },

    /** Create a new file */
    _eventCreate: function() {
        this.uploadbox.add([{ name: "New File", size: 0, mode: "new" }]);
    },

    /** Start upload process */
    _eventStart: function() {
        if (this.counter.announce == 0 || this.counter.running > 0) {
            return;
        }
        var self = this;
        this.upload_size = 0;
        this.upload_completed = 0;
        this.collection.each(model => {
            if (model.get("status") == "init") {
                model.set("status", "queued");
                self.upload_size += model.get("file_size");
            }
        });
        this.ui_button.model.set({ percentage: 0, status: "success" });
        this.counter.running = this.counter.announce;
        this.history_id = this.app.currentHistory();
        this.uploadbox.start();
        this._updateScreen();
    },

    /** Pause upload process */
    _eventStop: function() {
        if (this.counter.running > 0) {
            this.ui_button.model.set("status", "info");
            $(".upload-top-info").html("Queue will pause after completing the current file...");
            this.uploadbox.stop();
        }
    },

    /** Remove all */
    _eventReset: function() {
        if (this.counter.running == 0) {
            this.collection.reset();
            this.counter.reset();
            this.uploadbox.reset();
            this.select_extension.value(this.options.default_extension);
            this.select_genome.value(this.options.default_genome);
            this.ui_button.model.set("percentage", 0);
            this._updateScreen();
        }
    },

    /** Update extension for all models */
    updateExtension: function(extension, defaults_only) {
        var self = this;
        this.collection.each(model => {
            if (
                model.get("status") == "init" &&
                (model.get("extension") == self.options.default_extension || !defaults_only)
            ) {
                model.set("extension", extension);
            }
        });
    },

    /** Update collection type */
    updateCollectionType: function(collectionType) {
        this.collectionType = collectionType;
    },

    /** Update genome for all models */
    updateGenome: function(genome, defaults_only) {
        var self = this;
        this.collection.each(model => {
            if (
                model.get("status") == "init" &&
                (model.get("genome") == self.options.default_genome || !defaults_only)
            ) {
                model.set("genome", genome);
            }
        });
    },

    /** Set screen */
    _updateScreen: function() {
        var message = "";
        if (this.counter.announce == 0) {
            if (this.uploadbox.compatible()) {
                message = "&nbsp;";
            } else {
                message =
                    "Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.";
            }
        } else {
            if (this.counter.running == 0) {
                message = `You added ${
                    this.counter.announce
                } file(s) to the queue. Add more files or click 'Start' to proceed.`;
            } else {
                message = `Please wait...${this.counter.announce} out of ${this.counter.running} remaining.`;
            }
        }
        this.$(".upload-top-info").html(message);
        var enable_reset =
            this.counter.running == 0 && this.counter.announce + this.counter.success + this.counter.error > 0;
        var enable_start = this.counter.running == 0 && this.counter.announce > 0;
        var enable_build =
            this.counter.running == 0 &&
            this.counter.announce == 0 &&
            this.counter.success > 0 &&
            this.counter.error == 0;
        var enable_sources = this.counter.running == 0;
        var show_table = this.counter.announce + this.counter.success + this.counter.error > 0;
        this.btnReset[enable_reset ? "enable" : "disable"]();
        this.btnStart[enable_start ? "enable" : "disable"]();
        this.btnStart.$el[enable_start ? "addClass" : "removeClass"]("btn-primary");
        this.btnBuild[enable_build ? "enable" : "disable"]();
        this.btnBuild.$el[enable_build ? "addClass" : "removeClass"]("btn-primary");
        this.btnStop[this.counter.running > 0 ? "enable" : "disable"]();
        this.btnLocal[enable_sources ? "enable" : "disable"]();
        this.btnFtp[enable_sources ? "enable" : "disable"]();
        this.btnCreate[enable_sources ? "enable" : "disable"]();
        this.btnFtp.$el[this.ftp_upload_site ? "show" : "hide"]();
        this.$(".upload-table")[show_table ? "show" : "hide"]();
        this.$(".upload-helper")[show_table ? "hide" : "show"]();
    },

    /** Calculate percentage of all queued uploads */
    _uploadPercentage: function(percentage, size) {
        return (this.upload_completed + percentage * size) / this.upload_size;
    },

    /** Template */
    _template: function() {
        return `<div class="upload-view-default">
                <div class="upload-top">
                    <div class="upload-top-info"/>
                </div>
                <div class="upload-box">
                    <div class="upload-helper">
                        <i class="fa fa-files-o"/>Drop files here
                    </div>
                    <table class="upload-table ui-table-striped" style="display: none;">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Size</th>
                                <th>Status</th>
                                <th/>
                            </tr>
                        </thead>
                        <tbody/>
                    </table>
                </div>
                <div class="upload-footer">
                    <span class="upload-footer-title">Collection Type:</span>
                    <span class="upload-footer-collection-type"/>
                    <span class="upload-footer-title">File Type:</span>
                    <span class="upload-footer-extension"/>
                    <span class="upload-footer-extension-info upload-icon-button fa fa-search"/>
                    <span class="upload-footer-title">Genome (set all):</span>
                    <span class="upload-footer-genome"/>
                </div>
                <div class="upload-buttons"/>
            </div>`;
    }
});
