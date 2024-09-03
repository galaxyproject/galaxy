/** This is the common wrapper for nvd3 based visualizations. */
import * as d3 from "d3";
import * as Backbone from "backbone";
import * as _ from "underscore";

import "nvd3";

// TODO Disentangle jquery in the future
/* global $ */

import { addZoom, makeCategories, makeTickFormat } from "@galaxyproject/charts/lib/utilities/series";
import { requestPanels, request as requestDatasets } from "@galaxyproject/charts/lib/utilities/datasets";
import { requestCharts, request as requestJobs } from "@galaxyproject/charts/lib/utilities/jobs";

/** Get boolean as string */
function _asBoolean(value) {
    return String(value).toLowerCase() == "true";
}

/* Prepare containers */
function createContainers(tag, chart, target) {
    var n = _asBoolean(chart.settings.get("__use_panels")) ? chart.groups.length : 1;
    var $container = $("#" + target);
    $container.empty();
    const targets = [];
    for (var i = 0; i < n; i++) {
        var panel_id = "vis-container-id-" + i;
        var $panel = $("<" + tag + " style='float: left; height: 100%;' />").attr("id", panel_id);
        $panel.width(parseInt(100 / n) + "%");
        $container.append($panel);
        targets.push(panel_id);
    }
    return targets;
}

var CommonWrapper = Backbone.View.extend({
    initialize: function(options) {
        var self = this;
        options.targets = createContainers("svg", options.chart, options.target);
        this.options = options;
        options.render = function(canvas_id, groups) {
            return self.render(canvas_id, groups);
        };
        requestPanels(options);
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
                    d3chart.showLegend(_asBoolean(chart.settings.get("show_legend")));
                }
                self._makeAxes(d3chart, groups, chart.settings);
                if (makeConfig) {
                    makeConfig(d3chart);
                }
                if (_asBoolean(chart.settings.get("__use_panels"))) {
                    d3chart.options({ showControls: false });
                }
                d3chart.xAxis.showMaxMin(false);
                d3chart.yAxis.showMaxMin(false);
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
                        addZoom({
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
        var categories = makeCategories(groups, ["x", "y"]);
        function makeTick(id) {
            makeTickFormat({
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
        makeTick("x");
        makeTick("y");
    }
});

var PieWrapper = Backbone.View.extend({
    initialize: function(options) {
        var self = this;
        var chart = options.chart;
        var targets = createContainers("svg", options.chart, options.target);
        var process = options.process;
        var root = options.root;
        requestDatasets({
            root: root,
            chart: chart,
            dataset_id: chart.get("dataset_id"),
            dataset_groups: chart.groups,
            success: function(groups) {
                for (var group_index in groups) {
                    var group = groups[group_index];
                    self._drawGroup(chart, group, targets[group_index]);
                }
                chart.state("ok", "Pie chart has been drawn.");
                process.resolve();
            }
        });
    },

    /** Draw group */
    _drawGroup: function(chart, group, canvas_id) {
        try {
            var self = this;
            var canvas = d3.select("#" + canvas_id);
            var title = canvas.append("text");
            this._fixTitle(chart, canvas, title, group.key);
            var pie_data = [];
            _.each(group.values, function(value) {
                pie_data.push({ y: value.y, x: value.label });
            });
            nv.addGraph(function() {
                var legend_visible = _asBoolean(chart.settings.get("legend_visible"));
                var label_outside = _asBoolean(chart.settings.get("label|outside"));
                var label_type = chart.settings.get("label|type");
                var donut_ratio = parseFloat(chart.settings.get("donut_ratio"));
                var chart_3d = nv.models
                    .pieChart()
                    .donut(true)
                    .labelThreshold(0.05)
                    .showLegend(legend_visible)
                    .labelType(label_type)
                    .donutRatio(donut_ratio)
                    .donutLabelsOutside(label_outside);
                canvas.datum(pie_data).call(chart_3d);
                nv.utils.windowResize(function() {
                    chart_3d.update();
                    self._fixTitle(chart, canvas, title, group.key);
                });
            });
        } catch (err) {
            console.log(err);
        }
    },

    /** Fix title */
    _fixTitle: function(chart, canvas, title_element, title_text) {
        var width = parseInt(canvas.style("width"));
        var height = parseInt(canvas.style("height"));
        title_element
            .attr("x", width / 2)
            .attr("y", height - 10)
            .attr("text-anchor", "middle")
            .text(title_text);
    }
});

_.extend(window.bundleEntries || {}, {
    nvd3_bar: function(options) {
        options.type = "multiBarChart";
        return new CommonWrapper(options);
    },
    nvd3_bar_stacked: function(options) {
        options.type = "multiBarChart";
        options.makeConfig = function(nvd3_model) {
            nvd3_model.stacked(true);
        };
        return new CommonWrapper(options);
    },
    nvd3_horizontal: function(options) {
        options.type = "multiBarHorizontalChart";
        return new CommonWrapper(options);
    },
    nvd3_horizontal_stacked: function(options) {
        options.type = "multiBarHorizontalChart";
        options.makeConfig = function(nvd3_model) {
            nvd3_model.stacked(true);
        };
        return new CommonWrapper(options);
    },
    nvd3_histogram: function(options) {
        requestJobs(
            options.root,
            options.chart,
            requestCharts(options.chart, "histogram"),
            function(dataset) {
                var dataset_groups = new Backbone.Collection();
                options.chart.groups.each(function(group, index) {
                    dataset_groups.add({
                        __data_columns: { x: { is_numeric: true }, y: { is_numeric: true } },
                        x: 0,
                        y: index + 1,
                        key: group.get("key")
                    });
                });
                options.dataset_id = dataset.id;
                options.dataset_groups = dataset_groups;
                options.type = "multiBarChart";
                options.makeConfig = function(nvd3_model) {
                    nvd3_model.options({ showControls: true });
                };
                new CommonWrapper(options);
            },
            function() {
                options.process.reject();
            }
        );
    },
    nvd3_histogram_discrete: function(options) {
        requestJobs(
            options.root,
            options.chart,
            requestCharts(options.chart, "histogramdiscrete"),
            function(dataset) {
                var dataset_groups = new Backbone.Collection();
                options.chart.groups.each(function(group, index) {
                    dataset_groups.add({
                        __data_columns: { x: { is_label: true }, y: { is_numeric: true } },
                        x: 0,
                        y: index + 1,
                        key: group.get("key")
                    });
                });
                options.dataset_id = dataset.id;
                options.dataset_groups = dataset_groups;
                options.type = "multiBarChart";
                options.makeConfig = function(nvd3_model) {
                    nvd3_model.options({ showControls: true });
                };
                new CommonWrapper(options);
            },
            function() {
                options.process.reject();
            }
        );
    },
    nvd3_line: function(options) {
        options.type = "lineChart";
        return new CommonWrapper(options);
    },
    nvd3_line_focus: function(options) {
        options.type = "lineWithFocusChart";
        return new CommonWrapper(options);
    },
    nvd3_pie: function(options) {
        return new PieWrapper(options);
    },
    nvd3_scatter: function(options) {
        options.type = "scatterChart";
        options.makeConfig = function(nvd3_model) {
            nvd3_model
                .showDistX(true)
                .showDistY(true)
                .color(d3.scale.category10().range());
        };
        return new CommonWrapper(options);
    },
    nvd3_stackedarea: function(options) {
        options.type = "stackedAreaChart";
        return new CommonWrapper(options);
    },
    nvd3_stackedarea_full: function(options) {
        options.type = "stackedAreaChart";
        options.makeConfig = function(nvd3_model) {
            nvd3_model.style("expand");
        };
        return new CommonWrapper(options);
    },
    nvd3_stackedarea_stream: function(options) {
        options.type = "stackedAreaChart";
        options.makeConfig = function(nvd3_model) {
            nvd3_model.style("stream");
        };
        return new CommonWrapper(options);
    }
});
