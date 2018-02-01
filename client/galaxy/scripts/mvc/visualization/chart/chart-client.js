import Deferred from "utils/deferred";
import Utils from "utils/utils";
import Modal from "mvc/ui/ui-modal";
import Ui from "mvc/ui/ui-misc";
import Chart from "mvc/visualization/chart/components/model";
import Editor from "mvc/visualization/chart/views/editor";
import Viewer from "mvc/visualization/chart/views/viewport";

export default Backbone.View.extend({
    initialize: function(options) {
        this.modal = (window.parent.Galaxy && window.parent.Galaxy.modal) || new Modal.View();
        this.setElement($("<div/>").addClass("charts-client")
                                   .append($("<div/>").addClass("charts-buttons"))
                                   .append($("<div/>").addClass("charts-center"))
                                   .append($("<div/>").addClass("charts-right")));
        this.$center = this.$(".charts-center");
        this.$right = this.$(".charts-right");
        this.$buttons = this.$(".charts-buttons");
        this.chart = new Chart({}, options);
        this.chart.plugin = options.visualization_plugin;
        this.chart.plugin.specs = this.chart.plugin.specs || {};
        this.chart_load = options.chart_load;
        this.deferred = new Deferred();
        this.viewer = new Viewer(this);
        this.editor = new Editor(this);
        this.buttons =[{
            icon: "fa-angle-double-left",
            tooltip: "Show",
            cls: "ui-button-icon charts-fullscreen-button",
            onclick: () => {
                this.$el.removeClass("charts-fullscreen");
                window.dispatchEvent(new Event("resize"));
            }
        },{
            icon: "fa-angle-double-right",
            tooltip: "Hide",
            onclick: () => {
                this.$el.addClass("charts-fullscreen");
                window.dispatchEvent(new Event("resize"));
            }
        },{
            icon: "fa-line-chart",
            tooltip: "Visualize",
            onclick: () => {
                this.chart.set({
                    date: Utils.time()
                });
                this.chart.trigger("redraw");
            }
        },{
            icon: "fa-save",
            tooltip: "Save",
            onclick: () => {
                this.chart.set({
                    date: Utils.time()
                });
                this.chart.trigger("redraw");
            }
        }];
        for(let b of this.buttons) {
            this.$buttons.append((new Ui.ButtonIcon(b)).$el);
        }
        this.$center.append(this.viewer.$el);
        this.$right.append(this.editor.$el);
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
