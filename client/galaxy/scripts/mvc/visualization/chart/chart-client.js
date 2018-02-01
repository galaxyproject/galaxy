import Deferred from "utils/deferred";
import Modal from "mvc/ui/ui-modal";
import Chart from "mvc/visualization/chart/components/model";
import Editor from "mvc/visualization/chart/views/editor";
import Viewer from "mvc/visualization/chart/views/viewport";

export default Backbone.View.extend({
    initialize: function(options) {
        this.modal = (window.parent.Galaxy && window.parent.Galaxy.modal) || new Modal.View();
        this.setElement($("<div/>").append($("<div/>").addClass("charts-center"))
                                   .append($("<div/>").addClass("charts-right")));
        this.chart = new Chart({}, options);
        this.chart.plugin = options.visualization_plugin;
        this.chart.plugin.specs = this.chart.plugin.specs || {};
        this.chart_load = options.chart_load;
        this.deferred = new Deferred();
        this.viewer = new Viewer(this);
        this.editor = new Editor(this);
        this.$(".charts-center").append(this.viewer.$el);
        this.$(".charts-right").append(this.editor.$el);
        $.ajax({
            url: `${Galaxy.root}api/datasets/${options.dataset_id}`
        }).done(dataset => {
            this.dataset = dataset;
            this.chart.load();
            this.chart.trigger("redraw");
        }).fail(response => {
            let message = response.responseJSON && response.responseJSON.err_msg;
            this.errormessage = message || "Import failed for unkown reason.";
        });
    }
});
