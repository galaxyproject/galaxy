/**
 *  The charts editor holds the tabs for selecting chart types, chart configuration
 *  and data group selections.
 */
import Ui from "mvc/ui/ui-misc";
import Utils from "utils/utils";
import Tabs from "mvc/ui/ui-tabs";
import Groups from "mvc/visualization/chart/views/groups";
import Settings from "mvc/visualization/chart/views/settings";
import Description from "mvc/visualization/chart/views/description";

export default Backbone.View.extend({
    initialize: function(app, options) {
        this.app = app;
        this.chart = this.app.chart;
        this.description = new Description(this.app);
        this.title = new Ui.Input({
            onchange: () => {
                this.chart.set("title", this.title.value());
            }
        });
        this.tabs = new Tabs.View({});
        this.tabs.add({
            id: "settings",
            title: "Customize",
            icon: "fa fa-bars",
            tooltip: "Customize options.",
            $el: $("<div/>")
                .append(new Ui.Label({ title: "Provide a title:" }).$el)
                .append(this.title.$el)
                .append(
                    $("<div/>")
                        .addClass("ui-form-info ui-margin-bottom")
                        .html("This title will appear in the list of 'Saved Visualizations'.")
                )
                .append(new Settings(this.app).$el)
        });
        if (this.chart.plugin.groups) {
            this.tabs.add({
                id: "groups",
                title: "Select data",
                icon: "fa-database",
                tooltip: "Specify data options.",
                $el: new Groups(this.app).$el
            });
        }
        this.setElement("<div class='charts-editor'/>");
        this.$el.append(this.description.$el);
        this.$el.append(this.tabs.$el);
        this.listenTo(this.chart, "load", () => {
            this.title.value(this.chart.get("title"));
        });
    }
});
