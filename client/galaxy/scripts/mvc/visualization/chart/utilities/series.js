import _ from "underscore";
import * as d3 from "d3";

/** Get domain boundaries value */
function getDomains(groups, keys) {
    function _apply(operator, key) {
        let value;
        for (let group_index in groups) {
            let value_sub = d3[operator](groups[group_index].values, function(d) {
                return d[key];
            });
            value = value === undefined ? value_sub : Math[operator](value, value_sub);
        }
        return value;
    }
    var result = {};
    for (var index in keys) {
        var key = keys[index];
        result[key] = {
            min: _apply("min", key),
            max: _apply("max", key)
        };
    }
    return result;
}

/** Default series maker */
function makeSeries(groups, keys) {
    var plot_data = [];
    for (var group_index in groups) {
        var group = groups[group_index];
        var data = [];
        for (var value_index in group.values) {
            var point = [];
            if (keys) {
                for (var key_index in keys) {
                    let column_index = keys[key_index];
                    point.push(group.values[value_index][column_index]);
                }
            } else {
                for (let column_index in group.values[value_index]) {
                    point.push(group.values[value_index][column_index]);
                }
            }
            data.push(point);
        }
        plot_data.push(data);
    }
    return plot_data;
}

/** Default category maker */
function makeCategories(groups, column_keys) {
    var array = {};
    var data_columns = groups[0].__data_columns;
    _.each(column_keys, function(key) {
        if (data_columns[key].is_label) {
            array[key] = [];
        }
    });
    if (groups && groups[0]) {
        _.each(groups[0].values, function(value_dict) {
            for (var key in array) {
                array[key].push(String(value_dict[key]));
            }
        });
    }
    mapCategories(array, groups);
    return { array: array };
}

/** Apply default mapping index all values contained in label columns (for all groups) */
function mapCategories(array, groups) {
    _.each(groups, function(group) {
        _.each(group.values, function(value_dict, i) {
            for (var key in array) {
                value_dict[key] = parseInt(i);
            }
        });
    });
}

/** Category make for unique category labels */
function makeUniqueCategories(groups, with_index) {
    var categories = {};
    var array = {};
    var counter = {};
    var data_columns = groups[0].__data_columns;
    _.each(data_columns, function(column_def, key) {
        if (column_def.is_label) {
            categories[key] = {};
            array[key] = [];
            counter[key] = 0;
        }
    });
    // index all values contained in label columns (for all groups)
    for (var i in groups) {
        var group = groups[i];
        for (var j in group.values) {
            var value_dict = group.values[j];
            for (var key in categories) {
                var value = String(value_dict[key]);
                if (categories[key][value] === undefined) {
                    categories[key][value] = counter[key];
                    array[key].push(with_index ? [counter[key], value] : value);
                    counter[key]++;
                }
            }
        }
    }
    // convert group values into category indeces
    for (let i in groups) {
        let group = groups[i];
        for (let j in group.values) {
            let value_dict = group.values[j];
            for (let key in categories) {
                let value = String(value_dict[key]);
                value_dict[key] = categories[key][value];
            }
        }
    }
    return {
        categories: categories,
        array: array,
        counter: counter
    };
}

/** Make axis */
function makeTickFormat(options) {
    var type = options.type;
    var precision = options.precision;
    var categories = options.categories;
    var formatter = options.formatter;
    if (type == "hide") {
        formatter(function() {
            return "";
        });
    } else if (type == "auto") {
        if (categories) {
            formatter(function(value) {
                return categories[value] || "";
            });
        }
    } else {
        var d3format = function(d) {
            switch (type) {
                case "s":
                    var prefix = d3.formatPrefix(d);
                    return prefix.scale(d).toFixed() + prefix.symbol;
                default:
                    return d3.format("." + precision + type)(d);
            }
        };
        if (categories) {
            formatter(function(value) {
                var label = categories[value];
                if (label) {
                    if (isNaN(label)) {
                        return label;
                    } else {
                        try {
                            return d3format(label);
                        } catch (err) {
                            return label;
                        }
                    }
                } else {
                    return "";
                }
            });
        } else {
            formatter(function(value) {
                return d3format(value);
            });
        }
    }
}

/** Add zoom handler */
function addZoom(options) {
    var scaleExtent = 100;
    var yAxis = options.yAxis;
    var xAxis = options.xAxis;
    var xDomain = options.xDomain || xAxis.scale().domain;
    var yDomain = options.yDomain || yAxis.scale().domain;
    var redraw = options.redraw;
    var svg = options.svg;
    var xScale = xAxis.scale();
    var yScale = yAxis.scale();
    var x_boundary = xScale.domain().slice();
    var y_boundary = yScale.domain().slice();
    var d3zoom = d3.behavior.zoom();
    xScale.nice();
    yScale.nice();
    function fixDomain(domain, boundary) {
        domain[0] = Math.min(Math.max(domain[0], boundary[0]), boundary[1] - boundary[1] / scaleExtent);
        domain[1] = Math.max(boundary[0] + boundary[1] / scaleExtent, Math.min(domain[1], boundary[1]));
        return domain;
    }
    function zoomed() {
        yDomain(fixDomain(yScale.domain(), y_boundary));
        xDomain(fixDomain(xScale.domain(), x_boundary));
        redraw();
    }
    function unzoomed() {
        xDomain(x_boundary);
        yDomain(y_boundary);
        redraw();
        d3zoom.scale(1);
        d3zoom.translate([0, 0]);
    }
    d3zoom
        .x(xScale)
        .y(yScale)
        .scaleExtent([1, scaleExtent])
        .on("zoom", zoomed);
    svg.call(d3zoom).on("dblclick.zoom", unzoomed);
    return d3zoom;
}

export default {
    makeCategories: makeCategories,
    makeUniqueCategories: makeUniqueCategories,
    makeSeries: makeSeries,
    getDomains: getDomains,
    mapCategories: mapCategories,
    makeTickFormat: makeTickFormat,
    addZoom: addZoom
};
