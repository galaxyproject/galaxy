/**
 * shared functionality between default-row and collection-row.
 */
import Backbone from "backbone";
export default Backbone.View.extend({
    /** Dictionary of upload states and associated icons */
    status_classes: {
        init: "upload-icon-button fa fa-trash-o",
        queued: "upload-icon fa fa-spinner fa-spin",
        running: "upload-icon fa fa-spinner fa-spin",
        success: "upload-icon-button fa fa-check",
        error: "upload-icon-button fa fa-exclamation-triangle"
    },

    _renderStatusType: function(status) {
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
    }
});