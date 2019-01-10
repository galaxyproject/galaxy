/**
 *  The viewer creates and manages the dom elements used by the visualization plugins to draw the chart.
 *  This is the last class of the charts core classes before handing control over to the visualization plugins.
 */
import $ from "jquery";
import Backbone from "backbone";
import Utils from "utils/utils";

export default Backbone.View.extend({
    initialize: function(app, options) {
        var self = this;
        this.app = app;
        this.chart = this.app.chart;
        this.options = options;
        this.setElement(
            $("<div/>")
                .addClass("charts-viewer")
                .append(
                    $("<div/>")
                        .addClass("info")
                        .append($("<span/>").addClass("icon"))
                        .append($("<span/>").addClass("text"))
                )
        );
        this.$info = this.$(".info");
        this.$icon = this.$(".icon");
        this.$text = this.$(".text");
        this._fullscreen(this.$el, 20);
        this._createContainer("div");
        this.chart.on("redraw", function(confirmed) {
            if (!self.chart.get("modified") || !self.chart.plugin.specs.confirm || confirmed) {
                self.app.deferred.execute(function(process) {
                    console.debug("viewer:redraw() - Redrawing...");
                    self._draw(process, self.chart);
                });
            } else {
                self.chart.state("info", "Please confirm the settings before rendering the results.");
            }
        });
        this.chart.on("set:state", function() {
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
    _fullscreen: function($el, margin) {
        $el.css("height", $(window).height() - margin);
        $(window).resize(function() {
            $el.css("height", $(window).height() - margin);
        });
    },

    /** A chart may contain multiple sub charts/containers which are created here */
    _createContainer: function(tag, n) {
        tag = tag || "div";
        n = n || 1;
        this.$(".charts-viewer-container").remove();
        this.targets = [];
        for (var i = 0; i < n; i++) {
            var container_id = Utils.uid();
            var container_el = $("<div/>")
                .addClass("charts-viewer-container")
                .width(parseInt(100 / n) + "%")
                .append($("<" + tag + " class='charts-viewer-canvas' />").attr("id", container_id));
            this.$el.append(container_el);
            this.targets.push(container_id);
        }
    },

    /** Draws a new chart by loading and executing the corresponding chart wrapper */
    _draw: function(process, chart) {
        var n_panels = chart.settings.get("__use_panels") == "true" ? chart.groups.length : 1;
        this._createContainer(chart.plugin.specs.tag, n_panels);
        chart.set("date", Utils.time());
        chart.state("wait", "Please wait...");
        this.app.chart_load({ process: process, chart: chart, dataset: this.app.dataset, targets: this.targets });
    }
});
