/**
 *  The viewer creates and manages the dom elements used by the visualization plugins to draw the chart.
 *  This is the last class of the charts core classes before handing control over to the visualization plugins.
 */
import $ from "jquery";
import Backbone from "backbone";
import Utils from "utils/utils";
import { getAppRoot } from "onload/loadConfig";

export default Backbone.View.extend({
    initialize: function (app, options) {
        var self = this;
        this.app = app;
        this.chart = this.app.chart;
        this.options = options;
        this.$container = $("<div/>").css("height", "100%").attr("id", "charts-container");
        this.setElement(
            $("<div/>")
                .addClass("charts-viewer")
                .append(
                    $("<div/>")
                        .addClass("info")
                        .append($("<span/>").addClass("icon"))
                        .append($("<span/>").addClass("text"))
                )
                .append(this.$container)
        );
        this.$info = this.$(".info");
        this.$icon = this.$(".icon");
        this.$text = this.$(".text");
        this._fullscreen(this.$el, 20);
        this.chart.on("redraw", function (confirmed) {
            if (!self.chart.get("modified") || !self.chart.requiresConfirmation || confirmed) {
                self.app.deferred.execute(function (process) {
                    console.debug("viewer:redraw() - Redrawing...");
                    self._draw(process, self.chart);
                });
            } else {
                self.chart.state(
                    "info",
                    "Please review the chart settings in the menu to the right and select 'Confirm' to render the visualization."
                );
            }
        });
        this.chart.on("set:state", function () {
            var $container = self.$(".charts-viewer-container");
            var $info = self.$info;
            var $icon = self.$icon;
            var $text = self.$text;
            $icon.removeClass();
            $info.show();
            $text.html(self.chart.get("state_info"));
            var state = self.chart.get("state");
            switch (state) {
                case "ok":
                    $info.hide();
                    $container.show();
                    break;
                case "failed":
                    $icon.addClass("icon fa fa-warning");
                    $container.hide();
                    break;
                case "info":
                    $icon.addClass("icon fa fa-info");
                    $container.hide();
                    break;
                default:
                    $icon.addClass("icon fa fa-spinner fa-spin");
                    $container.show();
            }
        });
    },

    /** Force resize to fullscreen */
    _fullscreen: function ($el, margin) {
        $el.css("height", $(window).height() - margin);
        $(window).resize(function () {
            $el.css("height", $(window).height() - margin);
        });
    },

    /** Draws a new chart by loading and executing the corresponding chart wrapper */
    _draw: function (process, chart) {
        chart.set("date", Utils.time());
        chart.state("wait", "Please wait...");
        this.$container.empty();
        this.app.chart_load({
            process: process,
            chart: chart,
            target: "charts-container",
            dataset: this.app.dataset,
            root: getAppRoot(),
        });
    },
});
