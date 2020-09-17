/** Renders the composite upload row view */
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import _l from "utils/localization";
import Utils from "utils/utils";
import UploadSettings from "mvc/upload/upload-settings";
import UploadFtp from "mvc/upload/upload-ftp";
import Popover from "mvc/ui/ui-popover";
import Ui from "mvc/ui/ui-misc";
import "utils/uploadbox";
export default Backbone.View.extend({
    /** Dictionary of upload states and associated icons */
    status_classes: {
        init: "upload-mode fa fa-exclamation text-primary",
        ready: "upload-mode fa fa-check text-success",
        running: "upload-mode fa fa-spinner fa-spin",
        success: "upload-mode fa fa-check",
        error: "upload-mode fa fa-exclamation-triangle",
    },

    initialize: function (app, options) {
        var self = this;
        this.app = app;
        this.model = options.model;
        this.setElement(this._template());
        this.$source = this.$(".upload-source");
        this.$settings = this.$(".upload-settings");
        this.$status = this.$(".upload-status");
        this.$text = this.$(".upload-text");
        this.$text_content = this.$(".upload-text-content");
        this.$info_text = this.$(".upload-info-text");
        this.$info_progress = this.$(".upload-info-progress");
        this.$file_name = this.$(".upload-file-name");
        this.$file_desc = this.$(".upload-file-desc");
        this.$file_size = this.$(".upload-file-size");
        this.$progress_bar = this.$(".upload-progress-bar");
        this.$percentage = this.$(".upload-percentage");

        // build upload functions
        this.uploadinput = this.$el.uploadinput({
            ondragover: function () {
                self.model.get("enabled") && self.$el.addClass("alert-success");
            },
            ondragleave: function () {
                self.$el.removeClass("alert-success");
            },
            onchange: function (files) {
                if (self.model.get("status") != "running" && files && files.length > 0) {
                    self.model.reset({
                        file_data: files[0],
                        file_name: files[0].name,
                        file_size: files[0].size,
                        file_mode: files[0].mode || "local",
                    });
                    self._refreshReady();
                }
            },
        });

        // source selection popup
        this.button_menu = new Ui.ButtonMenu({
            icon: "fa-caret-down",
            title: _l("Select"),
            pull: "left",
        });
        this.$source.append(this.button_menu.$el);
        this.button_menu.addMenu({
            icon: "fa-laptop",
            title: _l("Choose local file"),
            onclick: function () {
                self.uploadinput.dialog();
            },
        });
        if (this.app.ftpUploadSite) {
            this.button_menu.addMenu({
                icon: "fa-folder-open-o",
                title: _l("Choose FTP file"),
                onclick: function () {
                    self._showFtp();
                },
            });
        }
        this.button_menu.addMenu({
            icon: "fa-edit",
            title: "Paste/Fetch data",
            onclick: function () {
                self.model.reset({
                    file_mode: "new",
                    file_name: "New File",
                });
            },
        });

        // add ftp file viewer
        this.ftp = new Popover({
            title: "Select a file",
            container: this.$source.find(".dropdown"),
            placement: "right",
        });

        // append popup to settings icon
        this.settings = new Popover({
            title: _l("Upload configuration"),
            container: this.$settings,
            placement: "bottom",
        });

        // handle text editing event
        this.$text_content.on("change input", (e) => {
            self.model.set({
                url_paste: $(e.target).val(),
                file_size: $(e.target).val().length,
            });
            self._refreshReady();
        });

        // handle settings popover
        this.$settings
            .on("click", (e) => {
                self._showSettings();
            })
            .on("mousedown", (e) => {
                e.preventDefault();
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
        this.listenTo(this.model, "change:file_name", () => {
            self._refreshFileName();
        });
        this.listenTo(this.model, "change:file_mode", () => {
            self._refreshMode();
        });
        this.listenTo(this.model, "change:file_size", () => {
            self._refreshFileSize();
        });
        this.listenTo(this.model, "remove", () => {
            self.remove();
        });
        this.app.collection.on("reset", () => {
            self.remove();
        });
    },

    render: function () {
        this.$el.attr("id", `upload-row-${this.model.id}`);
        this.$file_name.html(_.escape(this.model.get("file_name") || "-"));
        this.$file_desc.html(this.model.get("file_desc") || "Unavailable");
        this.$file_size.html(Utils.bytesToString(this.model.get("file_size")));
        this.$status.removeClass().addClass(this.status_classes.init);
    },

    /** Remove view */
    remove: function () {
        // call the base class remove method
        Backbone.View.prototype.remove.apply(this);
    },

    //
    // handle model events
    //

    /** Refresh ready or not states */
    _refreshReady: function () {
        this.app.collection.each((model) => {
            model.set("status", (model.get("file_size") > 0 && "ready") || "init");
        });
    },

    /** Refresh mode and e.g. show/hide textarea field */
    _refreshMode: function () {
        var file_mode = this.model.get("file_mode");
        if (file_mode == "new") {
            this.height = this.$el.height();
            this.$text
                .css({
                    width: `${this.$el.width() - 16}px`,
                    top: `${this.$el.height() - 8}px`,
                })
                .show();
            this.$el.height(this.$el.height() - 8 + this.$text.height() + 16);
            this.$text_content.val("").trigger("keyup");
        } else {
            this.$el.height(this.height);
            this.$text.hide();
        }
    },

    /** Refresh information */
    _refreshInfo: function () {
        var info = this.model.get("info");
        if (info) {
            this.$info_text.html(`<strong>Failed: </strong>${info}`).show();
        } else {
            this.$info_text.hide();
        }
    },

    /** Refresh percentage */
    _refreshPercentage: function () {
        var percentage = parseInt(this.model.get("percentage"));
        if (percentage != 0) {
            this.$progress_bar.css({ width: `${percentage}%` });
        } else {
            this.$progress_bar.addClass("no-transition");
            this.$progress_bar.css({ width: "0%" });
            this.$progress_bar[0].offsetHeight;
            this.$progress_bar.removeClass("no-transition");
        }
        this.$percentage.html(percentage != 100 ? `${percentage}%` : "Adding to history...");
    },

    /** Refresh status */
    _refreshStatus: function () {
        var status = this.model.get("status");
        this.$status.removeClass().addClass(this.status_classes[status]);
        this.model.set("enabled", status != "running");
        this.$text_content.attr("disabled", !this.model.get("enabled"));
        this.$el.removeClass("table-success table-danger table-warning");
        if (status == "running" || status == "ready") {
            this.model.set("percentage", 0);
        }
        this.$source.find(".button")[status == "running" ? "addClass" : "removeClass"]("disabled");
        if (status == "success") {
            this.$el.addClass("table-success");
            this.model.set("percentage", 100);
            this.$percentage.html("100%");
        }
        if (status == "error") {
            this.$el.addClass("table-danger");
            this.model.set("percentage", 0);
            this.$info_progress.hide();
            this.$info_text.show();
        } else {
            this.$info_progress.show();
            this.$info_text.hide();
        }
    },

    /** File name */
    _refreshFileName: function () {
        this.$file_name.html(this.model.get("file_name") || "-");
    },

    /** File size */
    _refreshFileSize: function () {
        this.$file_size.html(Utils.bytesToString(this.model.get("file_size")));
    },

    /** Show/hide ftp popup */
    _showFtp: function () {
        var self = this;
        this.ftp.show(
            new UploadFtp({
                ftp_upload_site: this.app.ftpUploadSite,
                onchange: function (ftp_file) {
                    self.ftp.hide();
                    if (self.model.get("status") != "running" && ftp_file) {
                        self.model.reset({
                            file_mode: "ftp",
                            file_name: ftp_file.path,
                            file_size: ftp_file.size,
                            file_path: ftp_file.path,
                        });
                        self._refreshReady();
                    }
                },
            }).$el
        );
    },

    /** Show/hide settings popup */
    _showSettings: function () {
        this.settings.show(new UploadSettings(this).$el);
    },

    /** Template */
    _template: function () {
        return `<tr class="upload-row">
                <td>
                    <div class="upload-source"/>
                    <div class="upload-text-column">
                        <div class="upload-text">
                            <div class="upload-text-info">Download data from the web by entering a URL (one per line) or directly paste content.</div>
                            <textarea class="upload-text-content form-control"/>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="upload-status"/>
                </td>
                <td>
                    <div class="upload-file-desc upload-title"/>
                </td>
                <td>
                    <div class="upload-file-name upload-title"/>
                </td>
                <td>
                    <div class="upload-file-size upload-size"/>
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
            </tr>`;
    },
});
