/** Renders the default uploader rows */
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import _l from "utils/localization";
import Utils from "utils/utils";
import UploadSettings from "mvc/upload/upload-settings";
import Popover from "mvc/ui/ui-popover";
import UploadExtension from "mvc/upload/upload-extension";
import Select from "mvc/ui/ui-select";
export default Backbone.View.extend({
    /** Dictionary of upload states and associated icons */
    status_classes: {
        init: "upload-icon-button fa fa-trash-o",
        queued: "upload-icon fa fa-spinner fa-spin",
        running: "upload-icon fa fa-spinner fa-spin",
        warning: "upload-icon fa fa-spinner fa-spin",
        success: "upload-icon-button fa fa-check",
        error: "upload-icon-button fa fa-exclamation-triangle"
    },

    initialize: function(app, options) {
        var self = this;
        this.app = app;
        this.list_extensions = app.list_extensions;
        this.model = options.model;
        this.setElement(this._template(options.model));
        this.$mode = this.$(".upload-mode");
        this.$title = this.$(".upload-title");
        this.$text = this.$(".upload-text");
        this.$size = this.$(".upload-size");
        this.$info_text = this.$(".upload-info-text");
        this.$info_progress = this.$(".upload-info-progress");
        this.$text_content = this.$(".upload-text-content");
        this.$settings = this.$(".upload-settings");
        this.$symbol = this.$(".upload-symbol");
        this.$progress_bar = this.$(".upload-progress-bar");
        this.$percentage = this.$(".upload-percentage");

        // append popup to settings icon
        this.settings = new Popover({
            title: _l("Upload configuration"),
            container: this.$(".upload-settings"),
            placement: "bottom"
        });

        // identify default genome and extension values
        var default_genome = this.app.select_genome.value();
        var default_extension = this.app.select_extension.value();

        // create select genomes
        this.select_genome = new Select.View({
            css: "upload-genome",
            data: self.app.list_genomes,
            container: this.$(".upload-genome"),
            value: default_genome,
            onchange: function(genome) {
                self.model.set("genome", genome);
            }
        });

        // create select extension
        this.select_extension = new Select.View({
            css: "upload-extension",
            data: _.filter(this.list_extensions, ext => !ext.composite_files),
            container: this.$(".upload-extension"),
            value: default_extension,
            onchange: function(extension) {
                self.model.set("extension", extension);
            }
        });

        // initialize genome and extension values
        this.model.set({
            genome: default_genome,
            extension: default_extension
        });

        // handle click event
        this.$symbol.on("click", () => {
            self._removeRow();
        });

        // handle extension info popover
        this.$(".upload-extension-info")
            .on("click", e => {
                let upload_ext = this.upload_extension;
                if (upload_ext) {
                    if (upload_ext.extension_popup.visible) {
                        upload_ext.extension_popup.hide();
                    } else {
                        upload_ext.extension_popup.remove();
                        this._makeUploadExtensionsPopover(e);
                    }
                } else {
                    this._makeUploadExtensionsPopover(e);
                }
            })
            .on("mousedown", e => {
                e.preventDefault();
            });

        // handle settings popover
        this.$settings
            .on("click", e => {
                self._showSettings();
            })
            .on("mousedown", e => {
                e.preventDefault();
            });

        // handle text editing event
        this.$text_content.on("change input", e => {
            self.model.set({
                url_paste: $(e.target).val(),
                file_size: $(e.target).val().length
            });
        });

        // handle text editing event
        this.$title.on("change input", e => {
            self.model.set({ file_name: $(e.target).val() });
        });

        // model events
        this.listenTo(this.model, "change:percentage", () => {
            self._refreshPercentage();
        });
        this.listenTo(this.model, "change:status", () => {
            self._refreshStatus();
        });
        this.listenTo(this.model, "change:info", () => {
            self._refreshInfo();
        });
        this.listenTo(this.model, "change:genome", () => {
            self._refreshGenome();
        });
        this.listenTo(this.model, "change:extension", () => {
            self._refreshExtension();
        });
        this.listenTo(this.model, "change:file_size", () => {
            self._refreshFileSize();
        });
    },

    render: function() {
        this._refreshType();
        this._refreshPercentage();
        this._refreshStatus();
        this._refreshInfo();
        this._refreshGenome();
        this._refreshExtension();
        this._refreshFileSize();
    },

    /** Remove view */
    remove: function() {
        this.select_genome.remove();
        this.select_extension.remove();
        Backbone.View.prototype.remove.apply(this);
    },

    /** Render type */
    _refreshType: function() {
        var options = this.model.attributes;
        this.$title.val(_.escape(options.file_name));
        this.$size.html(Utils.bytesToString(options.file_size));
        this.$mode
            .removeClass()
            .addClass("upload-mode")
            .addClass("text-primary");
        if (options.file_mode == "new") {
            this.$text
                .css({
                    width: `${this.$el.width() - 16}px`,
                    top: `${this.$el.height() - 8}px`
                })
                .show();
            this.$el.height(this.$el.height() - 8 + this.$text.height() + 16);
            this.$mode.addClass("fa fa-edit");
        } else if (options.file_mode == "local") {
            this.$mode.addClass("fa fa-laptop");
        } else if (options.file_mode == "ftp") {
            this.$mode.addClass("fa fa-folder-open-o");
        }
    },

    /** Update extension */
    _refreshExtension: function() {
        this.select_extension.value(this.model.get("extension"));
    },

    /** Update genome */
    _refreshGenome: function() {
        this.select_genome.value(this.model.get("genome"));
    },

    /** Refresh info text */
    _refreshInfo: function() {
        var info = this.model.get("info");
        if (info) {
            this.$info_text.html(`<strong>Warning: </strong>${info}`).show();
        } else {
            this.$info_text.hide();
        }
    },

    /** Refresh percentage status */
    _refreshPercentage: function() {
        var percentage = parseInt(this.model.get("percentage"));
        this.$progress_bar.css({ width: `${percentage}%` });
        this.$percentage.html(percentage != 100 ? `${percentage}%` : "Adding to history...");
    },

    /** Refresh status */
    _refreshStatus: function() {
        var status = this.model.get("status");
        this.$symbol
            .removeClass()
            .addClass("upload-symbol")
            .addClass(this.status_classes[status]);
        this.model.set("enabled", status == "init");
        var enabled = this.model.get("enabled");
        this.$text_content.attr("disabled", !enabled);
        this.$title.attr("disabled", !enabled);
        if (enabled) {
            this.select_genome.enable();
            this.select_extension.enable();
        } else {
            this.select_genome.disable();
            this.select_extension.disable();
        }
        this.$info_progress.show();
        this.$el.removeClass().addClass("upload-row");
        if (status == "success") {
            this.$el.addClass("table-success");
            this.$percentage.html("100%");
        } else if (status == "error") {
            this.$el.addClass("table-danger");
            this.$info_progress.hide();
        } else if (status == "warning") {
            this.$el.addClass("table-warning");
            this.$info_progress.hide();
        }
    },

    /** Refresh file size */
    _refreshFileSize: function() {
        this.$size.html(Utils.bytesToString(this.model.get("file_size")));
    },

    /** Remove row */
    _removeRow: function() {
        if (["init", "success", "error"].indexOf(this.model.get("status")) !== -1) {
            this.app.collection.remove(this.model);
        }
    },

    /** Attach file info popup */
    _showSettings: function() {
        this.settings.show(new UploadSettings(this).$el);
    },

    /** Make extension popover */
    _makeUploadExtensionsPopover: function(e) {
        this.upload_extension = new UploadExtension({
            $el: $(e.target),
            title: this.select_extension.text(),
            extension: this.select_extension.value(),
            list: this.list_extensions
        });
    },

    /** View template */
    _template: function(options) {
        return `<tr id="upload-row-${options.id}" class="upload-row">
                    <td>
                        <div class="upload-text-column">
                            <div class="upload-mode"/>
                            <input class="upload-title ml-2 border rounded"/>
                            <div class="upload-text">
                                <div class="upload-text-info">
                                    Download data from the web by entering URLs (one per line) or directly paste content.
                                </div>
                                <textarea class="upload-text-content form-control"/>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="upload-size"/>
                    </td>
                    <td>
                        <div class="upload-extension float-left mr-1"/>
                        <div class="upload-extension-info upload-icon-button fa fa-search"/>
                    </td>
                    <td>
                        <div class="upload-genome"/>
                    </td>
                    <td>
                        <div class="upload-settings upload-icon-button fa fa-gear"/>
                    </td>
                    <td>
                        <div class="upload-info">
                            <div class="upload-info-text"/>
                            <div class="upload-info-progress progress">
                                <div class="upload-progress-bar progress-bar progress-bar-success"/>
                                <div class="upload-percentage">0%</div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="upload-symbol ${this.status_classes.init}"/>
                    </td>
                </tr>`;
    }
});
