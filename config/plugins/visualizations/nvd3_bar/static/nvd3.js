/** This is the common wrapper for nvd3 based visualizations. */
import Utilities from "./utilities/tabular-utilities";
import * as nv from "nvd3";
import * as d3 from "d3";
//import "nvd3/build/nv.d3.css";

var CommonWrapper = Backbone.View.extend({
    initialize: function(options) {
        var self = this;
        this.options = options;
        options.render = function(canvas_id, groups) {
            return self.render(canvas_id, groups);
        };
        Utilities.panelHelper(options);
    },
    render: function(canvas_id, groups) {
        var self = this;
        var chart = this.options.chart;
        var type = this.options.type;
        var makeConfig = this.options.makeConfig;
        var d3chart = nv.models[type]();
        nv.addGraph(function() {
            try {
                d3chart.xAxis.axisLabel(chart.settings.get("x_axis_label"));
                d3chart.yAxis.axisLabel(chart.settings.get("y_axis_label")).axisLabelDistance(30);
                d3chart.options({ showControls: false });
                if (d3chart.showLegend) {
                    d3chart.showLegend(chart.settings.get("show_legend") == "true");
                }
                self._makeAxes(d3chart, groups, chart.settings);
                if (makeConfig) {
                    makeConfig(d3chart);
                }
                if (chart.settings.get("__use_panels") === "true") {
                    d3chart.options({ showControls: false });
                }
                d3chart.xAxis.showMaxMin(false);
                d3chart.yAxis.showMaxMin(chart.definition.showmaxmin);
                d3chart.tooltipContent(function(key, x, y, graph) {
                    return "<h3>" + (graph.point.tooltip || key) + "</h3>";
                });
                if ($("#" + canvas_id).length > 0) {
                    var canvas = d3.select("#" + canvas_id);
                    canvas.datum(groups).call(d3chart);
                    if (chart.definition.zoomable && chart.definition.zoomable != "native") {
                        if (d3chart.clipEdge) {
                            d3chart.clipEdge(true);
                        }
                        Utilities.addZoom({
                            xAxis: d3chart.xAxis,
                            yAxis: d3chart.yAxis,
                            yDomain: d3chart.yDomain,
                            xDomain: d3chart.xDomain,
                            redraw: function() {
                                d3chart.update();
                            },
                            svg: canvas
                        });
                    }
                    nv.utils.windowResize(d3chart.update);
                }
            } catch (err) {
                chart.state("failed", err);
            }
        });
        return true;
    },

    /** Format axes ticks */
    _makeAxes: function(d3chart, groups, settings) {
        var categories = Utilities.makeCategories(groups, ["x", "y"]);
        function makeTickFormat(id) {
            Utilities.makeTickFormat({
                categories: categories.array[id],
                type: settings.get(id + "_axis_type|type"),
                precision: settings.get(id + "_axis_type|precision"),
                formatter: function(formatter) {
                    if (formatter) {
                        d3chart[id + "Axis"].tickFormat(function(value) {
                            return formatter(value);
                        });
                    }
                }
            });
        }
        makeTickFormat("x");
        makeTickFormat("y");
    }
});

export default {
    nvd3_bar: function(options) {
        options.type = "multiBarChart";
        new CommonWrapper(options);
    }
};
