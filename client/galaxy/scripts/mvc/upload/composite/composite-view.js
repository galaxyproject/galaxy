/** Renders contents of the composite uploader */
import _l from "utils/localization";
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
// import Utils from "utils/utils";
import UploadModel from "mvc/upload/upload-model";
import UploadRow from "mvc/upload/composite/composite-row";
import UploadExtension from "mvc/upload/upload-extension";
import Select from "mvc/ui/ui-select";
import Ui from "mvc/ui/ui-misc";

export default Backbone.View.extend({
    collection: new UploadModel.Collection(),
    initialize: function(app) {
        var self = this;
        this.app = app;
        this.options = app.options;
        this.list_extensions = app.list_extensions;
        this.list_genomes = app.list_genomes;
        this.ftp_upload_site = app.currentFtp();
        this.setElement(this._template());

        // create button section
        this.btnStart = new Ui.Button({
            title: _l("Start"),
            onclick: function() {
                self._eventStart();
            }
        });
        this.btnClose = new Ui.Button({
            title: _l("Close"),
            onclick: function() {
                self.app.modal.hide();
            }
        });

        // append buttons to dom
        _.each([this.btnStart, this.btnClose], button => {
            self.$(".upload-buttons").prepend(button.$el);
        });

        // select extension
        this.select_extension = new Select.View({
            css: "upload-footer-selection",
            container: this.$(".upload-footer-extension"),
            data: _.filter(this.list_extensions, ext => ext.composite_files),
            onchange: function(extension) {
                self.collection.reset();
                var details = _.findWhere(self.list_extensions, {
                    id: extension
                });
                if (details && details.composite_files) {
                    _.each(details.composite_files, item => {
                        self.collection.add({
                            id: self.collection.size(),
                            file_desc: item.description || item.name
                        });
                    });
                }
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
            value: this.options.default_genome
        });

        // listener for collection triggers on change in composite datatype and extension selection
        this.listenTo(this.collection, "add", model => {
            self._eventAnnounce(model);
        });
        this.listenTo(this.collection, "change add", () => {
            self.render();
        });
        this.select_extension.options.onchange(this.select_extension.value());
        this.render();
    },

    render: function() {
        var model = this.collection.first();
        if (model && model.get("status") == "running") {
            this.select_genome.disable();
            this.select_extension.disable();
        } else {
            this.select_genome.enable();
            this.select_extension.enable();
        }
        if (this.collection.where({ status: "ready" }).length == this.collection.length && this.collection.length > 0) {
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
    _eventAnnounce: function(model) {
        var upload_row = new UploadRow(this, { model: model });
        this.$(".upload-table > tbody:first").append(upload_row.$el);
        this.$(".upload-table")[this.collection.length > 0 ? "show" : "hide"]();
        upload_row.render();
    },

    /** Start upload process */
    _eventStart: function() {
        var self = this;
        this.collection.each(model => {
            model.set({
                genome: self.select_genome.value(),
                extension: self.select_extension.value()
            });
        });
        $.uploadpost({
            url: this.app.options.upload_path,
            data: this.app.toData(this.collection.filter()),
            success: function(message) {
                self._eventSuccess(message);
            },
            error: function(message) {
                self._eventError(message);
            },
            progress: function(percentage) {
                self._eventProgress(percentage);
            }
        });
    },

    /** Refresh progress state */
    _eventProgress: function(percentage) {
        this.collection.each(it => {
            it.set("percentage", percentage);
        });
    },

    /** Refresh success state */
    _eventSuccess: function(message) {
        let Galaxy = getGalaxyInstance();
        this.collection.each(it => {
            it.set("status", "success");
        });
        Galaxy.currHistoryPanel.refreshContents();
    },

    /** Refresh error state */
    _eventError: function(message) {
        this.collection.each(it => {
            it.set({ status: "error", info: message });
        });
    },

    /** Load html template */
    _template: function() {
        return `<div class="upload-view-composite">
                <div class="upload-top">
                    <div class="upload-top-info">&nbsp;</div>
                </div>
                <div class="upload-box">
                    <table class="upload-table ui-table-striped" style="display: none;">
                        <thead>
                            <tr>
                                <th/>
                                <th/>
                                <th>Description</th>
                                <th>Name</th>
                                <th>Size</th>
                                <th>Settings</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody/>
                    </table>
                </div>
                <div class="upload-footer">
                    <span class="upload-footer-title">Composite Type:</span>
                    <span class="upload-footer-extension"/>
                    <span class="upload-footer-extension-info upload-icon-button fa fa-search"/>
                    <span class="upload-footer-title">Genome/Build:</span>
                    <span class="upload-footer-genome"/>
                </div>
                <div class="upload-buttons"/>
            </div>`;
    }
});
