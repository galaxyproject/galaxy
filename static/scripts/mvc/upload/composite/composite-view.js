define("mvc/upload/composite/composite-view", ["exports", "utils/localization", "utils/utils", "mvc/upload/upload-model", "mvc/upload/composite/composite-row", "mvc/upload/upload-extension", "mvc/ui/ui-popover", "mvc/ui/ui-select", "mvc/ui/ui-misc"], function(exports, _localization, _utils, _uploadModel, _compositeRow, _uploadExtension, _uiPopover, _uiSelect, _uiMisc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _uploadModel2 = _interopRequireDefault(_uploadModel);

    var _compositeRow2 = _interopRequireDefault(_compositeRow);

    var _uploadExtension2 = _interopRequireDefault(_uploadExtension);

    var _uiPopover2 = _interopRequireDefault(_uiPopover);

    var _uiSelect2 = _interopRequireDefault(_uiSelect);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    exports.default = Backbone.View.extend({
        collection: new _uploadModel2.default.Collection(),
        initialize: function initialize(app) {
            var self = this;
            this.app = app;
            this.options = app.options;
            this.list_extensions = app.list_extensions;
            this.list_genomes = app.list_genomes;
            this.ftp_upload_site = app.currentFtp();
            this.setElement(this._template());

            // create button section
            this.btnStart = new _uiMisc2.default.Button({
                title: (0, _localization2.default)("Start"),
                onclick: function onclick() {
                    self._eventStart();
                }
            });
            this.btnClose = new _uiMisc2.default.Button({
                title: (0, _localization2.default)("Close"),
                onclick: function onclick() {
                    self.app.modal.hide();
                }
            });

            // append buttons to dom
            _.each([this.btnStart, this.btnClose], function(button) {
                self.$(".upload-buttons").prepend(button.$el);
            });

            // select extension
            this.select_extension = new _uiSelect2.default.View({
                css: "upload-footer-selection",
                container: this.$(".upload-footer-extension"),
                data: _.filter(this.list_extensions, function(ext) {
                    return ext.composite_files;
                }),
                onchange: function onchange(extension) {
                    self.collection.reset();
                    var details = _.findWhere(self.list_extensions, {
                        id: extension
                    });
                    if (details && details.composite_files) {
                        _.each(details.composite_files, function(item) {
                            self.collection.add({
                                id: self.collection.size(),
                                file_desc: item.description || item.name
                            });
                        });
                    }
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
                value: this.options.default_genome
            });

            // listener for collection triggers on change in composite datatype and extension selection
            this.listenTo(this.collection, "add", function(model) {
                self._eventAnnounce(model);
            });
            this.listenTo(this.collection, "change add", function() {
                self.render();
            });
            this.select_extension.options.onchange(this.select_extension.value());
            this.render();
        },

        render: function render() {
            var model = this.collection.first();
            if (model && model.get("status") == "running") {
                this.select_genome.disable();
                this.select_extension.disable();
            } else {
                this.select_genome.enable();
                this.select_extension.enable();
            }
            if (this.collection.where({
                    status: "ready"
                }).length == this.collection.length && this.collection.length > 0) {
                this.btnStart.enable();
                this.btnStart.$el.addClass("btn-primary");
            } else {
                this.btnStart.disable();
                this.btnStart.$el.removeClass("btn-primary");
            }
            this.$(".upload-table")[this.collection.length > 0 ? "show" : "hide"]();
        },

        //
        // upload events / process pipeline
        //

        /** Builds the basic ui with placeholder rows for each composite data type file */
        _eventAnnounce: function _eventAnnounce(model) {
            var upload_row = new _compositeRow2.default(this, {
                model: model
            });
            this.$(".upload-table > tbody:first").append(upload_row.$el);
            this.$(".upload-table")[this.collection.length > 0 ? "show" : "hide"]();
            upload_row.render();
        },

        /** Start upload process */
        _eventStart: function _eventStart() {
            var self = this;
            this.collection.each(function(model) {
                model.set({
                    genome: self.select_genome.value(),
                    extension: self.select_extension.value()
                });
            });
            $.uploadpost({
                url: this.app.options.nginx_upload_path,
                data: this.app.toData(this.collection.filter()),
                success: function success(message) {
                    self._eventSuccess(message);
                },
                error: function error(message) {
                    self._eventError(message);
                },
                progress: function progress(percentage) {
                    self._eventProgress(percentage);
                }
            });
        },

        /** Refresh progress state */
        _eventProgress: function _eventProgress(percentage) {
            this.collection.each(function(it) {
                it.set("percentage", percentage);
            });
        },

        /** Refresh success state */
        _eventSuccess: function _eventSuccess(message) {
            this.collection.each(function(it) {
                it.set("status", "success");
            });
            Galaxy.currHistoryPanel.refreshContents();
        },

        /** Refresh error state */
        _eventError: function _eventError(message) {
            this.collection.each(function(it) {
                it.set({
                    status: "error",
                    info: message
                });
            });
        },

        /** Load html template */
        _template: function _template() {
            return '<div class="upload-view-composite">' + '<div class="upload-top">' + '<h6 class="upload-top-info"/>' + "</div>" + '<div class="upload-box">' + '<table class="upload-table ui-table-striped" style="display: none;">' + "<thead>" + "<tr>" + "<th/>" + "<th/>" + "<th>Description</th>" + "<th>Name</th>" + "<th>Size</th>" + "<th>Settings</th>" + "<th>Status</th>" + "</tr>" + "</thead>" + "<tbody/>" + "</table>" + "</div>" + '<div class="upload-footer">' + '<span class="upload-footer-title">Composite Type:</span>' + '<span class="upload-footer-extension"/>' + '<span class="upload-footer-extension-info upload-icon-button fa fa-search"/> ' + '<span class="upload-footer-title">Genome/Build:</span>' + '<span class="upload-footer-genome"/>' + "</div>" + '<div class="upload-buttons"/>' + "</div>";
        }
    });
});
//# sourceMappingURL=../../../../maps/mvc/upload/composite/composite-view.js.map
