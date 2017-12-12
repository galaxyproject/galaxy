define("mvc/upload/composite/composite-row", ["exports", "utils/localization", "utils/utils", "mvc/upload/upload-settings", "mvc/upload/upload-ftp", "mvc/ui/ui-popover", "mvc/ui/ui-misc", "mvc/ui/ui-select", "utils/uploadbox"], function(exports, _localization, _utils, _uploadSettings, _uploadFtp, _uiPopover, _uiMisc, _uiSelect) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _uploadSettings2 = _interopRequireDefault(_uploadSettings);

    var _uploadFtp2 = _interopRequireDefault(_uploadFtp);

    var _uiPopover2 = _interopRequireDefault(_uiPopover);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _uiSelect2 = _interopRequireDefault(_uiSelect);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    exports.default = Backbone.View.extend({
        /** Dictionary of upload states and associated icons */
        status_classes: {
            init: "upload-mode fa fa-exclamation text-primary",
            ready: "upload-mode fa fa-check text-success",
            running: "upload-mode fa fa-spinner fa-spin",
            success: "upload-mode fa fa-check",
            error: "upload-mode fa fa-exclamation-triangle"
        },

        initialize: function initialize(app, options) {
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
                ondragover: function ondragover() {
                    self.model.get("enabled") && self.$el.addClass("warning");
                },
                ondragleave: function ondragleave() {
                    self.$el.removeClass("warning");
                },
                onchange: function onchange(files) {
                    if (self.model.get("status") != "running" && files && files.length > 0) {
                        self.model.reset({
                            file_data: files[0],
                            file_name: files[0].name,
                            file_size: files[0].size,
                            file_mode: files[0].mode || "local"
                        });
                        self._refreshReady();
                    }
                }
            });

            // source selection popup
            this.button_menu = new _uiMisc2.default.ButtonMenu({
                icon: "fa-caret-down",
                title: (0, _localization2.default)("Select"),
                pull: "left"
            });
            this.$source.append(this.button_menu.$el);
            this.button_menu.addMenu({
                icon: "fa-laptop",
                title: (0, _localization2.default)("Choose local file"),
                onclick: function onclick() {
                    self.uploadinput.dialog();
                }
            });
            if (this.app.ftp_upload_site) {
                this.button_menu.addMenu({
                    icon: "fa-folder-open-o",
                    title: (0, _localization2.default)("Choose FTP file"),
                    onclick: function onclick() {
                        self._showFtp();
                    }
                });
            }
            this.button_menu.addMenu({
                icon: "fa-edit",
                title: "Paste/Fetch data",
                onclick: function onclick() {
                    self.model.reset({
                        file_mode: "new",
                        file_name: "New File"
                    });
                }
            });

            // add ftp file viewer
            this.ftp = new _uiPopover2.default.View({
                title: "Choose FTP file:",
                container: this.$source.find(".ui-button-menu"),
                placement: "right"
            });

            // append popup to settings icon
            this.settings = new _uiPopover2.default.View({
                title: (0, _localization2.default)("Upload configuration"),
                container: this.$settings,
                placement: "bottom"
            });

            // handle text editing event
            this.$text_content.on("change input", function(e) {
                self.model.set({
                    url_paste: $(e.target).val(),
                    file_size: $(e.target).val().length
                });
                self._refreshReady();
            });

            // handle settings popover
            this.$settings.on("click", function(e) {
                self._showSettings();
            }).on("mousedown", function(e) {
                e.preventDefault();
            });

            // model events
            this.listenTo(this.model, "change:percentage", function() {
                self._refreshPercentage();
            });
            this.listenTo(this.model, "change:status", function() {
                self._refreshStatus();
            });
            this.listenTo(this.model, "change:info", function() {
                self._refreshInfo();
            });
            this.listenTo(this.model, "change:file_name", function() {
                self._refreshFileName();
            });
            this.listenTo(this.model, "change:file_mode", function() {
                self._refreshMode();
            });
            this.listenTo(this.model, "change:file_size", function() {
                self._refreshFileSize();
            });
            this.listenTo(this.model, "remove", function() {
                self.remove();
            });
            this.app.collection.on("reset", function() {
                self.remove();
            });
        },

        render: function render() {
            this.$el.attr("id", "upload-row-" + this.model.id);
            this.$file_name.html(_.escape(this.model.get("file_name") || "-"));
            this.$file_desc.html(this.model.get("file_desc") || "Unavailable");
            this.$file_size.html(_utils2.default.bytesToString(this.model.get("file_size")));
            this.$status.removeClass().addClass(this.status_classes.init);
        },

        /** Remove view */
        remove: function remove() {
            // call the base class remove method
            Backbone.View.prototype.remove.apply(this);
        },

        //
        // handle model events
        //

        /** Refresh ready or not states */
        _refreshReady: function _refreshReady() {
            this.app.collection.each(function(model) {
                model.set("status", model.get("file_size") > 0 && "ready" || "init");
            });
        },

        /** Refresh mode and e.g. show/hide textarea field */
        _refreshMode: function _refreshMode() {
            var file_mode = this.model.get("file_mode");
            if (file_mode == "new") {
                this.height = this.$el.height();
                this.$text.css({
                    width: this.$el.width() - 16 + "px",
                    top: this.$el.height() - 8 + "px"
                }).show();
                this.$el.height(this.$el.height() - 8 + this.$text.height() + 16);
                this.$text_content.val("").trigger("keyup");
            } else {
                this.$el.height(this.height);
                this.$text.hide();
            }
        },

        /** Refresh information */
        _refreshInfo: function _refreshInfo() {
            var info = this.model.get("info");
            if (info) {
                this.$info_text.html("<strong>Failed: </strong>" + info).show();
            } else {
                this.$info_text.hide();
            }
        },

        /** Refresh percentage */
        _refreshPercentage: function _refreshPercentage() {
            var percentage = parseInt(this.model.get("percentage"));
            if (percentage != 0) {
                this.$progress_bar.css({
                    width: percentage + "%"
                });
            } else {
                this.$progress_bar.addClass("no-transition");
                this.$progress_bar.css({
                    width: "0%"
                });
                this.$progress_bar[0].offsetHeight;
                this.$progress_bar.removeClass("no-transition");
            }
            this.$percentage.html(percentage != 100 ? percentage + "%" : "Adding to history...");
        },

        /** Refresh status */
        _refreshStatus: function _refreshStatus() {
            var status = this.model.get("status");
            this.$status.removeClass().addClass(this.status_classes[status]);
            this.model.set("enabled", status != "running");
            this.$text_content.attr("disabled", !this.model.get("enabled"));
            this.$el.removeClass("success danger warning");
            if (status == "running" || status == "ready") {
                this.model.set("percentage", 0);
            }
            this.$source.find(".button")[status == "running" ? "addClass" : "removeClass"]("disabled");
            if (status == "success") {
                this.$el.addClass("success");
                this.model.set("percentage", 100);
                this.$percentage.html("100%");
            }
            if (status == "error") {
                this.$el.addClass("danger");
                this.model.set("percentage", 0);
                this.$info_progress.hide();
                this.$info_text.show();
            } else {
                this.$info_progress.show();
                this.$info_text.hide();
            }
        },

        /** File name */
        _refreshFileName: function _refreshFileName() {
            this.$file_name.html(this.model.get("file_name") || "-");
        },

        /** File size */
        _refreshFileSize: function _refreshFileSize() {
            this.$file_size.html(_utils2.default.bytesToString(this.model.get("file_size")));
        },

        /** Show/hide ftp popup */
        _showFtp: function _showFtp() {
            if (!this.ftp.visible) {
                var self = this;
                this.ftp.empty();
                this.ftp.append(new _uploadFtp2.default({
                    ftp_upload_site: this.app.ftp_upload_site,
                    onchange: function onchange(ftp_file) {
                        self.ftp.hide();
                        if (self.model.get("status") != "running" && ftp_file) {
                            self.model.reset({
                                file_mode: "ftp",
                                file_name: ftp_file.path,
                                file_size: ftp_file.size,
                                file_path: ftp_file.path
                            });
                            self._refreshReady();
                        }
                    }
                }).$el);
                this.ftp.show();
            } else {
                this.ftp.hide();
            }
        },

        /** Show/hide settings popup */
        _showSettings: function _showSettings() {
            if (!this.settings.visible) {
                this.settings.empty();
                this.settings.append(new _uploadSettings2.default(this).$el);
                this.settings.show();
            } else {
                this.settings.hide();
            }
        },

        /** Template */
        _template: function _template() {
            return '<tr class="upload-row">' + "<td>" + '<div class="upload-source"/>' + '<div class="upload-text-column">' + '<div class="upload-text">' + '<div class="upload-text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' + '<textarea class="upload-text-content form-control"/>' + "</div>" + "</div>" + "</td>" + "<td>" + '<div class="upload-status"/>' + "</td>" + "<td>" + '<div class="upload-file-desc upload-title"/>' + "</td>" + "<td>" + '<div class="upload-file-name upload-title"/>' + "</td>" + "<td>" + '<div class="upload-file-size upload-size"/>' + "</td>" + '<td><div class="upload-settings upload-icon-button fa fa-gear"/></td>' + "<td>" + '<div class="upload-info">' + '<div class="upload-info-text"/>' + '<div class="upload-info-progress progress">' + '<div class="upload-progress-bar progress-bar progress-bar-success"/>' + '<div class="upload-percentage">0%</div>' + "</div>" + "</div>" + "</td>" + "</tr>";
        }
    });
});
//# sourceMappingURL=../../../../maps/mvc/upload/composite/composite-row.js.map
