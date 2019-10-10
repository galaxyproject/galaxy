/**
 *  The charts editor holds the tabs for selecting chart types, chart configuration
 *  and data group selections.
 */
import $ from "jquery";
import Backbone from "backbone";
import Ui from "mvc/ui/ui-misc";
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
            icon: "fa fa-gear",
            tooltip: "Change settings.",
            $el: $("<div/>")
                .append("<label><b>Provide a title</b><label>")
                .append(this.title.$el)
                .append(
                    $("<div/>")
                        .addClass("form-text text-muted")
                        .html("This title will appear in the list of 'Saved Visualizations'.")
                )
                .append(new Settings(this.app).$el)
        });
        if (this.chart.plugin.groups) {
            this.tabs.add({
                id: "groups",
                icon: "fa-database",
                tooltip: "Select data.",
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
