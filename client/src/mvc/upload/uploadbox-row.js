/**
 * shared functionality between default-row and collection-row.
 */
import _l from "utils/localization";
import Backbone from "backbone";
import Utils from "utils/utils";
import Popover from "mvc/ui/ui-popover";
import UploadSettings from "mvc/upload/upload-settings";
export default Backbone.View.extend({
    /** Dictionary of upload states and associated icons */
    status_classes: {
        init: "upload-icon-button fa fa-trash-o",
        queued: "upload-icon fa fa-spinner fa-spin",
        running: "upload-icon fa fa-spinner fa-spin",
        success: "upload-icon-button fa fa-check",
        error: "upload-icon-button fa fa-exclamation-triangle",
    },

    _setupSettings: function () {
        // append popup to settings icon
        this.settings = new Popover({
            title: _l("Upload configuration"),
            container: this.$(".upload-settings"),
            placement: "bottom",
        });
    },

    _renderStatusType: function (status) {
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

    _setupUploadBoxListeners: function () {
        this.listenTo(this.model, "change:percentage", () => {
            this._refreshPercentage();
        });
        this.listenTo(this.model, "change:status", () => {
            this._refreshStatus();
        });
        this.listenTo(this.model, "change:info", () => {
            this._refreshInfo();
        });
        this.listenTo(this.model, "change:file_size", () => {
            this._refreshFileSize();
        });
    },

    _refreshInfo: function () {
        var info = this.model.get("info");
        if (info) {
            this.$info_text.html(`<strong>Warning: </strong>${info}`).show();
        } else {
            this.$info_text.hide();
        }
    },

    _refreshPercentage: function () {
        var percentage = parseInt(this.model.get("percentage"));
        this.$progress_bar.css({ width: `${percentage}%` });
        this.$percentage.html(percentage != 100 ? `${percentage}%` : "Adding to history...");
    },

    _refreshFileSize: function () {
        this.$size.html(Utils.bytesToString(this.model.get("file_size")));
    },

    _removeRow: function () {
        if (["init", "success", "error"].indexOf(this.model.get("status")) !== -1) {
            this.app.collection.remove(this.model);
        }
    },

    _showSettings: function () {
        this.settings.show(new UploadSettings(this).$el);
    },
});
