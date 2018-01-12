/**
 *  The charts editor holds the tabs for selecting chart types, chart configuration
 *  and data group selections.
 */
import Portlet from "mvc/ui/ui-portlet";
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
        this.message = new Ui.Message({ cls: "ui-margin-bottom" });
        this.portlet = new Portlet.View({
            icon: "fa-bar-chart-o",
            title: "Editor",
            operations: {
                draw: new Ui.ButtonIcon({
                    icon: "fa-line-chart",
                    tooltip: "Render Visualization",
                    title: "Visualize",
                    onclick: () => {
                        this._drawChart();
                    }
                }),
                back: new Ui.ButtonIcon({
                    icon: "fa-caret-left",
                    tooltip: "Return to Viewer",
                    title: "Cancel",
                    onclick: () => {
                        this.app.go("viewer");
                        this.chart.load();
                    }
                })
            }
        });

        // input field for chart title
        this.title = new Ui.Input({
            placeholder: "Chart title",
            onchange: () => {
                this.chart.set("title", this.title.value());
            }
        });

        // create tabs
        this.tabs = new Tabs.View({});
        this.tabs.add({
            id: "settings",
            title: "Customize",
            icon: "fa fa-bars",
            tooltip: "Start by selecting a visualization.",
            $el: $("<div/>")
                .append(this.description.$el)
                .append(new Ui.Label({ title: "Provide a title:" }).$el)
                .append(this.title.$el)
                .append(
                    $("<div/>")
                        .addClass("ui-form-info ui-margin-bottom")
                        .html("This title will appear in the list of 'Saved Visualizations'.")
                )
                .append(new Settings(this.app).$el)
        });
        this.tabs.add({
            id: "groups",
            title: "Select data",
            icon: "fa-database",
            tooltip: "Specify data options.",
            $el: new Groups(this.app).$el
        });

        // set elements
        this.portlet.append(this.message.$el);
        this.portlet.append(this.tabs.$el.addClass("ui-margin-top-large"));
        this.portlet.hideOperation("back");
        this.setElement(this.portlet.$el);

        // chart events
        this.listenTo(this.chart, "change:title", chart => {
            this._refreshTitle();
        });
        this.listenTo(this.chart, "redraw", chart => {
            this.portlet.showOperation("back");
        });
        this.chart.reset();
    },

    /** Show editor */
    show: function() {
        this.$el.show();
    },

    /** Hide editor */
    hide: function() {
        this.$el.hide();
    },

    /** Refresh title handler */
    _refreshTitle: function() {
        var title = this.chart.get("title");
        this.portlet.title(title);
        this.title.value(title);
    },

    /** Draw chart data */
    _drawChart: function() {
        this.chart.set({
            type: this.types.value(),
            title: this.title.value(),
            date: Utils.time()
        });
        if (this.chart.groups.length === 0) {
            this.message.update({
                message: "Please specify data options before rendering the visualization.",
                persistent: false
            });
            this.tabs.show("groups");
            return;
        }
        var valid = true;
        this.chart.groups.each(group => {
            if (valid) {
                _.each(group.get("__data_columns"), (data_columns, name) => {
                    if (group.attributes[name] === null) {
                        this.message.update({
                            status: "danger",
                            message: "This visualization type requires column types not found in your tabular file.",
                            persistent: false
                        });
                        this.tabs.show("groups");
                        valid = false;
                    }
                });
            }
        });
        if (valid) {
            this.app.go("viewer");
            this.app.deferred.execute(() => {
                this.chart.trigger("redraw");
            });
        }
    }
});
