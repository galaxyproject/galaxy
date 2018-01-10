import Deferred from "utils/deferred";
import Modal from "mvc/ui/ui-modal";
import Portlet from "mvc/ui/ui-portlet";
import Ui from "mvc/ui/ui-misc";
import Utils from "utils/utils";
import Chart from "mvc/visualization/chart/components/model";
import Editor from "mvc/visualization/chart/views/editor";
import Viewer from "mvc/visualization/chart/views/viewer";
var View = Backbone.View.extend({
    initialize: function(options) {
        this.options = options;
        this.modal = (parent.Galaxy && parent.Galaxy.modal) || new Modal.View();
        this.setElement("<div/>")
        $.ajax({
            url: `${Galaxy.root}api/datasets/${options.dataset_id}`
        })
        .done(dataset => {
            this.dataset = dataset;
            this.chart = new Chart({}, options);
            this.chart.plugin = options.visualization_plugin;
            this.deferred = new Deferred();
            this.viewer = new Viewer(this);
            this.editor = new Editor(this);
            this.$el.append(this.viewer.$el);
            this.$el.append(this.editor.$el);
            this.go(this.chart.load() ? "viewer" : "editor");
            this.render();
        })
        .fail(response => {
            let message = response.responseJSON && response.responseJSON.err_msg;
            this.errormessage = message || "Import failed for unkown reason.";
        });
    },

    /** Build client ui */
    render: function() {
        //let plugin_path = this.visualization.plugin.static_url + '/' + this.visualization.type;
        //import Plugin from plugin_path;
        /*require(["repository/build/" + chart.get("type")], function(ChartView) {
            new ChartView({ process: process, chart: chart, dataset: self.app.dataset, targets: self.targets });
        }, function(err) {
            chart.state(
                "failed",
                "Please verify that your internet connection works properly. This visualization could not be accessed in the repository. Please contact the Galaxy Team if this error persists."
            );
            console.debug(err);
            process.resolve();
        });
        */
    },

    /** Loads a view and makes sure that all others are hidden */
    go: function(view_id) {
        $(".tooltip").hide();
        this.viewer.hide();
        this.editor.hide();
        this[view_id].show();
    },

    /** Split chart type into path components */
    split: function(chart_type) {
        var path = chart_type.split(/_(.+)/);
        if (path.length >= 2) {
            return path[0] + "/" + path[1];
        } else {
            return chart_type;
        }
    }
});
export default { View: View }