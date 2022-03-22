/** Renders the default uploader rows */
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import Utils from "utils/utils";
import UploadExtension from "mvc/upload/upload-extension";
import UploadBoxRow from "mvc/upload/uploadbox-row";
import Select from "mvc/ui/ui-select";
export default UploadBoxRow.extend({
    initialize: function (app, options) {
        var self = this;
        this.app = app;
        this.list_extensions = app.listExtensions;
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

        this._setupSettings();

        // identify default genome and extension values
        var default_genome = this.app.genome;
        var default_extension = this.app.extension;

        // create select genomes
        this.select_genome = new Select.View({
            css: "upload-genome",
            data: self.app.listGenomes,
            container: this.$(".upload-genome"),
            value: default_genome,
            onchange: function (genome) {
                self.model.set("genome", genome);
            },
        });

        // create select extension
        this.select_extension = new Select.View({
            css: "upload-extension",
            data: self.app.extensions,
            container: this.$(".upload-extension"),
            value: default_extension,
            onchange: function (extension) {
                self.model.set("extension", extension);
            },
        });

        // initialize genome and extension values
        this.model.set({
            genome: default_genome,
            extension: default_extension,
        });

        // handle click event
        this.$symbol.on("click", () => {
            self._removeRow();
        });

        // handle extension info popover
        this.$(".upload-extension-info")
            .on("click", (e) => {
                const upload_ext = this.upload_extension;
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
            .on("mousedown", (e) => {
                e.preventDefault();
            });

        // handle settings popover
        this.$settings
            .on("click", (e) => {
                self._showSettings();
            })
            .on("mousedown", (e) => {
                e.preventDefault();
            });

        // handle text editing event
        this.$text_content.on("change input", (e) => {
            self.model.set({
                url_paste: $(e.target).val(),
                file_size: $(e.target).val().length,
            });
        });

        // handle text editing event
        this.$title.on("change input", (e) => {
            self.model.set({ file_name: $(e.target).val() });
        });

        // model events
        this._setupUploadBoxListeners();
        this.listenTo(this.model, "change:genome", () => {
            self._refreshGenome();
        });
        this.listenTo(this.model, "change:extension", () => {
            self._refreshExtension();
        });
    },

    render: function () {
        this._refreshType();
        this._refreshPercentage();
        this._refreshStatus();
        this._refreshInfo();
        this._refreshGenome();
        this._refreshExtension();
        this._refreshFileSize();
    },

    /** Remove view */
    remove: function () {
        this.select_genome.remove();
        this.select_extension.remove();
        Backbone.View.prototype.remove.apply(this);
    },

    /** Render type */
    _refreshType: function () {
        var options = this.model.attributes;
        this.$title.val(_.escape(options.file_name));
        this.$title.select();
        this.$size.html(Utils.bytesToString(options.file_size));
        this.$mode.removeClass().addClass("upload-mode").addClass("text-primary");
        if (options.file_mode == "new") {
            this.$text
                .css({
                    width: `${this.$el.width() - 16}px`,
                    top: `${this.$el.height() - 8}px`,
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
    _refreshExtension: function () {
        this.select_extension.value(this.model.get("extension"));
    },

    /** Update genome */
    _refreshGenome: function () {
        this.select_genome.value(this.model.get("genome"));
    },

    /** Refresh status */
    _refreshStatus: function () {
        var status = this.model.get("status");
        this.$symbol.removeClass().addClass("upload-symbol").addClass(this.status_classes[status]);
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
        this._renderStatusType(status);
    },

    /** Make extension popover */
    _makeUploadExtensionsPopover: function (e) {
        this.upload_extension = new UploadExtension({
            $el: $(e.target),
            title: this.select_extension.text(),
            extension: this.select_extension.value(),
            list: this.list_extensions,
        });
    },

    /** View template */
    _template: function (options) {
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
    },
});
