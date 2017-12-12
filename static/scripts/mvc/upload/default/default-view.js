define("mvc/upload/default/default-view", ["exports", "utils/localization", "utils/utils", "mvc/upload/upload-model", "mvc/upload/default/default-row", "mvc/upload/upload-ftp", "mvc/upload/upload-extension", "mvc/ui/ui-popover", "mvc/ui/ui-select", "mvc/ui/ui-misc", "mvc/lazy/lazy-limited", "utils/uploadbox"], function(exports, _localization, _utils, _uploadModel, _defaultRow, _uploadFtp2, _uploadExtension, _uiPopover, _uiSelect, _uiMisc, _lazyLimited) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _uploadModel2 = _interopRequireDefault(_uploadModel);

    var _defaultRow2 = _interopRequireDefault(_defaultRow);

    var _uploadFtp3 = _interopRequireDefault(_uploadFtp2);

    var _uploadExtension2 = _interopRequireDefault(_uploadExtension);

    var _uiPopover2 = _interopRequireDefault(_uiPopover);

    var _uiSelect2 = _interopRequireDefault(_uiSelect);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _lazyLimited2 = _interopRequireDefault(_lazyLimited);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    exports.default = Backbone.View.extend({
        // current upload size in bytes
        upload_size: 0,

        // contains upload row models
        collection: new _uploadModel2.default.Collection(),

        // keeps track of the current uploader state
        counter: {
            announce: 0,
            success: 0,
            error: 0,
            running: 0,
            reset: function reset() {
                this.announce = this.success = this.error = this.running = 0;
            }
        },

        initialize: function initialize(app) {
            var self = this;
            this.app = app;
            this.options = app.options;
            this.list_extensions = app.list_extensions;
            this.list_genomes = app.list_genomes;
            this.ui_button = app.ui_button;
            this.ftp_upload_site = app.currentFtp();

            // build template
            this.setElement(this._template());
            this.$uploadbox = this.$(".upload-box");
            this.$uploadtable = this.$(".upload-table");

            // append buttons to dom
            this.btnLocal = new _uiMisc2.default.Button({
                id: "btn-local",
                title: (0, _localization2.default)("Choose local file"),
                onclick: function onclick() {
                    self.uploadbox.select();
                },
                icon: "fa fa-laptop"
            });
            this.btnFtp = new _uiMisc2.default.Button({
                id: "btn-ftp",
                title: (0, _localization2.default)("Choose FTP file"),
                onclick: function onclick() {
                    self._eventFtp();
                },
                icon: "fa fa-folder-open-o"
            });
            this.btnCreate = new _uiMisc2.default.Button({
                id: "btn-new",
                title: "Paste/Fetch data",
                onclick: function onclick() {
                    self._eventCreate();
                },
                icon: "fa fa-edit"
            });
            this.btnStart = new _uiMisc2.default.Button({
                id: "btn-start",
                title: (0, _localization2.default)("Start"),
                onclick: function onclick() {
                    self._eventStart();
                }
            });
            this.btnStop = new _uiMisc2.default.Button({
                id: "btn-stop",
                title: (0, _localization2.default)("Pause"),
                onclick: function onclick() {
                    self._eventStop();
                }
            });
            this.btnReset = new _uiMisc2.default.Button({
                id: "btn-reset",
                title: (0, _localization2.default)("Reset"),
                onclick: function onclick() {
                    self._eventReset();
                }
            });
            this.btnClose = new _uiMisc2.default.Button({
                id: "btn-close",
                title: (0, _localization2.default)("Close"),
                onclick: function onclick() {
                    self.app.modal.hide();
                }
            });
            _.each([this.btnLocal, this.btnFtp, this.btnCreate, this.btnStop, this.btnReset, this.btnStart, this.btnClose], function(button) {
                self.$(".upload-buttons").prepend(button.$el);
            });

            // file upload
            this.uploadbox = this.$uploadbox.uploadbox({
                url: this.app.options.nginx_upload_path,
                announce: function announce(index, file) {
                    self._eventAnnounce(index, file);
                },
                initialize: function initialize(index) {
                    return self.app.toData([self.collection.get(index)], self.history_id);
                },
                progress: function progress(index, percentage) {
                    self._eventProgress(index, percentage);
                },
                success: function success(index, message) {
                    self._eventSuccess(index, message);
                },
                error: function error(index, message) {
                    self._eventError(index, message);
                },
                complete: function complete() {
                    self._eventComplete();
                },
                ondragover: function ondragover() {
                    self.$uploadbox.addClass("highlight");
                },
                ondragleave: function ondragleave() {
                    self.$uploadbox.removeClass("highlight");
                }
            });

            // add ftp file viewer
            this.ftp = new _uiPopover2.default.View({
                title: (0, _localization2.default)("FTP files"),
                container: this.btnFtp.$el
            });

            // select extension
            this.select_extension = new _uiSelect2.default.View({
                css: "upload-footer-selection",
                container: this.$(".upload-footer-extension"),
                data: _.filter(this.list_extensions, function(ext) {
                    return !ext.composite_files;
                }),
                value: this.options.default_extension,
                onchange: function onchange(extension) {
                    self._changeExtension(extension);
                }
            });

            // handle extension info popover
            this.$(".upload-footer-extension-info").on("click", function(e) {
                new _uploadExtension2.default({
                    $el: $(e.target),
                    title: self.select_extension.text(),
                    extension: self.select_extension.value(),
                    list: self.list_extensions,
                    placement: "top"
                });
            }).on("mousedown", function(e) {
                e.preventDefault();
            });

            // genome extension
            this.select_genome = new _uiSelect2.default.View({
                css: "upload-footer-selection",
                container: this.$(".upload-footer-genome"),
                data: this.list_genomes,
                value: this.options.default_genome,
                onchange: function onchange(genome) {
                    self._changeGenome(genome);
                }
            });

            // Lazy load helper
            this.loader = new _lazyLimited2.default({
                $container: this.$uploadbox,
                collection: this.collection,
                new_content: function new_content(model) {
                    var upload_row = new _defaultRow2.default(self, {
                        model: model
                    });
                    self.$uploadtable.find("> tbody:first").append(upload_row.$el);
                    upload_row.render();
                    return upload_row;
                }
            });

            // events
            this.collection.on("remove", function(model) {
                self._eventRemove(model);
            });
            this.render();
        },

        render: function render() {
            var message = "";
            if (this.counter.announce == 0) {
                if (this.uploadbox.compatible()) {
                    message = "&nbsp;";
                } else {
                    message = "Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.";
                }
            } else {
                if (this.counter.running == 0) {
                    message = "You added " + this.counter.announce + " file(s) to the queue. Add more files or click 'Start' to proceed.";
                } else {
                    message = "Please wait..." + this.counter.announce + " out of " + this.counter.running + " remaining.";
                }
            }
            this.$(".upload-top-info").html(message);
            var enable_reset = this.counter.running == 0 && this.counter.announce + this.counter.success + this.counter.error > 0;
            var enable_start = this.counter.running == 0 && this.counter.announce > 0;
            var enable_sources = this.counter.running == 0;
            var show_table = this.counter.announce + this.counter.success + this.counter.error > 0;
            this.btnReset[enable_reset ? "enable" : "disable"]();
            this.btnStart[enable_start ? "enable" : "disable"]();
            this.btnStart.$el[enable_start ? "addClass" : "removeClass"]("btn-primary");
            this.btnStop[this.counter.running > 0 ? "enable" : "disable"]();
            this.btnLocal[enable_sources ? "enable" : "disable"]();
            this.btnFtp[enable_sources ? "enable" : "disable"]();
            this.btnCreate[enable_sources ? "enable" : "disable"]();
            this.btnFtp.$el[this.ftp_upload_site ? "show" : "hide"]();
            this.$(".upload-table")[show_table ? "show" : "hide"]();
            this.$(".upload-helper")[show_table ? "hide" : "show"]();
        },

        /** A new file has been dropped/selected through the uploadbox plugin */
        _eventAnnounce: function _eventAnnounce(index, file) {
            this.counter.announce++;
            var new_model = new _uploadModel2.default.Model({
                id: index,
                file_name: file.name,
                file_size: file.size,
                file_mode: file.mode || "local",
                file_path: file.path,
                file_data: file
            });
            this.render();
            this.collection.add(new_model);
        },

        /** Progress */
        _eventProgress: function _eventProgress(index, percentage) {
            var it = this.collection.get(index);
            it.set("percentage", percentage);
            this.ui_button.model.set("percentage", this._uploadPercentage(percentage, it.get("file_size")));
        },

        /** Success */
        _eventSuccess: function _eventSuccess(index, message) {
            var it = this.collection.get(index);
            it.set({
                percentage: 100,
                status: "success"
            });
            this.ui_button.model.set("percentage", this._uploadPercentage(100, it.get("file_size")));
            this.upload_completed += it.get("file_size") * 100;
            this.counter.announce--;
            this.counter.success++;
            this.render();
            Galaxy.currHistoryPanel.refreshContents();
        },

        /** Error */
        _eventError: function _eventError(index, message) {
            var it = this.collection.get(index);
            it.set({
                percentage: 100,
                status: "error",
                info: message
            });
            this.ui_button.model.set({
                percentage: this._uploadPercentage(100, it.get("file_size")),
                status: "danger"
            });
            this.upload_completed += it.get("file_size") * 100;
            this.counter.announce--;
            this.counter.error++;
            this.render();
        },

        /** Queue is done */
        _eventComplete: function _eventComplete() {
            this.collection.each(function(model) {
                model.get("status") == "queued" && model.set("status", "init");
            });
            this.counter.running = 0;
            this.render();
        },

        /** Remove model from upload list */
        _eventRemove: function _eventRemove(model) {
            var status = model.get("status");
            if (status == "success") {
                this.counter.success--;
            } else if (status == "error") {
                this.counter.error--;
            } else {
                this.counter.announce--;
            }
            this.uploadbox.remove(model.id);
            this.render();
        },

        //
        // events triggered by this view
        //

        /** Show/hide ftp popup */
        _eventFtp: function _eventFtp() {
            if (!this.ftp.visible) {
                this.ftp.empty();
                var self = this;
                this.ftp.append(new _uploadFtp3.default({
                    collection: this.collection,
                    ftp_upload_site: this.ftp_upload_site,
                    onadd: function onadd(ftp_file) {
                        return self.uploadbox.add([{
                            mode: "ftp",
                            name: ftp_file.path,
                            size: ftp_file.size,
                            path: ftp_file.path
                        }]);
                    },
                    onremove: function onremove(model_index) {
                        self.collection.remove(model_index);
                    }
                }).$el);
                this.ftp.show();
            } else {
                this.ftp.hide();
            }
        },

        /** Create a new file */
        _eventCreate: function _eventCreate() {
            this.uploadbox.add([{
                name: "New File",
                size: 0,
                mode: "new"
            }]);
        },

        /** Start upload process */
        _eventStart: function _eventStart() {
            if (this.counter.announce != 0 && this.counter.running == 0) {
                // prepare upload process
                var self = this;
                this.upload_size = 0;
                this.upload_completed = 0;
                this.collection.each(function(model) {
                    if (model.get("status") == "init") {
                        model.set("status", "queued");
                        self.upload_size += model.get("file_size");
                    }
                });
                this.ui_button.model.set({
                    percentage: 0,
                    status: "success"
                });
                this.counter.running = this.counter.announce;
                this.history_id = this.app.currentHistory();

                // package ftp files separately, and remove them from queue
                this._uploadFtp();

                // queue remaining files
                this.uploadbox.start();
                this.render();
            }
        },

        /** Pause upload process */
        _eventStop: function _eventStop() {
            if (this.counter.running > 0) {
                this.ui_button.model.set("status", "info");
                $(".upload-top-info").html("Queue will pause after completing the current file...");
                this.uploadbox.stop();
            }
        },

        /** Remove all */
        _eventReset: function _eventReset() {
            if (this.counter.running == 0) {
                var self = this;
                this.collection.reset();
                this.counter.reset();
                this.uploadbox.reset();
                this.select_extension.value(this.options.default_extension);
                this.select_genome.value(this.options.default_genome);
                this.ui_button.model.set("percentage", 0);
                this.render();
            }
        },

        /** Update extension for all models */
        _changeExtension: function _changeExtension(extension, defaults_only) {
            var self = this;
            this.collection.each(function(model) {
                if (model.get("status") == "init" && (model.get("extension") == self.options.default_extension || !defaults_only)) {
                    model.set("extension", extension);
                }
            });
        },

        /** Update genome for all models */
        _changeGenome: function _changeGenome(genome, defaults_only) {
            var self = this;
            this.collection.each(function(model) {
                if (model.get("status") == "init" && (model.get("genome") == self.options.default_genome || !defaults_only)) {
                    model.set("genome", genome);
                }
            });
        },

        /** Package and upload ftp files in a single request */
        _uploadFtp: function _uploadFtp() {
            var self = this;
            var list = [];
            this.collection.each(function(model) {
                if (model.get("status") == "queued" && model.get("file_mode") == "ftp") {
                    self.uploadbox.remove(model.id);
                    list.push(model);
                }
            });
            if (list.length > 0) {
                $.uploadpost({
                    data: this.app.toData(list),
                    url: this.app.options.nginx_upload_path,
                    success: function success(message) {
                        _.each(list, function(model) {
                            self._eventSuccess(model.id);
                        });
                    },
                    error: function error(message) {
                        _.each(list, function(model) {
                            self._eventError(model.id, message);
                        });
                    }
                });
            }
        },

        /** Calculate percentage of all queued uploads */
        _uploadPercentage: function _uploadPercentage(percentage, size) {
            return (this.upload_completed + percentage * size) / this.upload_size;
        },

        /** Template */
        _template: function _template() {
            return '<div class="upload-view-default">' + '<div class="upload-top">' + '<h6 class="upload-top-info"/>' + "</div>" + '<div class="upload-box">' + '<div class="upload-helper"><i class="fa fa-files-o"/>Drop files here</div>' + '<table class="upload-table ui-table-striped" style="display: none;">' + "<thead>" + "<tr>" + "<th>Name</th>" + "<th>Size</th>" + "<th>Type</th>" + "<th>Genome</th>" + "<th>Settings</th>" + "<th>Status</th>" + "<th/>" + "</tr>" + "</thead>" + "<tbody/>" + "</table>" + "</div>" + '<div class="upload-footer">' + '<span class="upload-footer-title">Type (set all):</span>' + '<span class="upload-footer-extension"/>' + '<span class="upload-footer-extension-info upload-icon-button fa fa-search"/> ' + '<span class="upload-footer-title">Genome (set all):</span>' + '<span class="upload-footer-genome"/>' + "</div>" + '<div class="upload-buttons"/>' + "</div>";
        }
    });
});
//# sourceMappingURL=../../../../maps/mvc/upload/default/default-view.js.map
