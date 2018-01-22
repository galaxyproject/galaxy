/** This is the common wrapper for nvd3 based visualizations. */
import * as d3 from "d3";
import * as nv from "nvd3";
import "../node_modules/nvd3/build/nv.d3.css";

var Series = window.bundleEntries.chartUtilities.Series;
var Datasets = window.bundleEntries.chartUtilities.Datasets;

var CommonWrapper = Backbone.View.extend({
    initialize: function(options) {
        var self = this;
        this.options = options;
        options.render = function(canvas_id, groups) {
            return self.render(canvas_id, groups);
        };
        Datasets.requestPanels(options);
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
                d3chart.yAxis.axisLabel(chart.settings.get("y_axis_label"));
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
                d3chart.tooltip.contentGenerator(function(context) {
                    var data = context.data || context.point;
                    return "<h3>" + (data.tooltip || data.key || data.y) + "</h3>";
                });
                if ($("#" + canvas_id).length > 0) {
                    var canvas = d3.select("#" + canvas_id);
                    canvas.datum(groups).call(d3chart);
                    if (chart.plugin.specs.zoomable && chart.plugin.specs.zoomable != "native") {
                        if (d3chart.clipEdge) {
                            d3chart.clipEdge(true);
                        }
                        Series.addZoom({
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
        var categories = Series.makeCategories(groups, ["x", "y"]);
        function makeTickFormat(id) {
            Series.makeTickFormat({
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

_.extend(window.bundleEntries || {}, {
    nvd3_bar: function(options) {
        options.type = "multiBarChart";
        return new CommonWrapper(options);
    },
    nvd3_scatter: function(options) {
        options.type = 'scatterChart';
        options.makeConfig = function( nvd3_model ) {
            nvd3_model.showDistX( true )
                      .showDistY( true )
                      .color( d3.scale.category10().range() );
        };
        return new CommonWrapper(options);
    }
});
