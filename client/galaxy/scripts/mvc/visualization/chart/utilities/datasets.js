/** This class handles, formats and caches datasets. */
import _ from "underscore";
import { getAppRoot } from "onload/loadConfig";
import Utils from "utils/utils";

/** Assists in assigning the viewport panels */
var requestPanels = function(options) {
    var process = options.process;
    var chart = options.chart;
    var render = options.render;
    var targets = options.targets;
    var dataset_id = options.dataset_id || options.chart.get("dataset_id");
    var dataset_groups = options.dataset_groups || options.chart.groups;
    request({
        chart: chart,
        dataset_id: dataset_id,
        dataset_groups: dataset_groups,
        success: function(result) {
            try {
                if (targets.length == result.length) {
                    var valid = true;
                    for (var group_index in result) {
                        var group = result[group_index];
                        if (!render(targets[group_index], [group])) {
                            valid = false;
                            break;
                        }
                    }
                    if (valid) {
                        chart.state("ok", "Multi-panel chart drawn.");
                    }
                } else if (targets.length == 1) {
                    if (render(targets[0], result)) {
                        chart.state("ok", "Chart drawn.");
                    }
                } else {
                    chart.state("failed", "Invalid panel count.");
                }
                process.resolve();
            } catch (err) {
                console.debug("FAILED: tabular-utilities::panelHelper() - " + err);
                chart.state("failed", err);
                process.reject();
            }
        }
    });
};

/** Fills request dictionary with data from cache/response */
var _cache = {};
var request = function(options) {
    var groups = options.dataset_groups;
    var dataset_id = options.dataset_id;
    // identify columns needed to fulfill request
    var column_list = [];
    groups.each(function(group) {
        _.each(group.get("__data_columns"), function(column_def, column_name) {
            var column = group.get(column_name);
            var block_id = _block_id(dataset_id, column);
            if (
                column_list.indexOf(column) === -1 &&
                !_cache[block_id] &&
                column != "auto" &&
                column != "zero" &&
                column !== undefined
            ) {
                column_list.push(column);
            }
        });
    });
    if (column_list.length === 0) {
        _fillFromCache(options);
        return;
    }
    // Fetch data columns into dataset object
    Utils.get({
        url: getAppRoot() + "api/datasets/" + dataset_id,
        data: {
            data_type: "raw_data",
            provider: "dataset-column",
            indeces: column_list.toString()
        },
        success: function(response) {
            var column_length = column_list.length;
            var results = new Array(column_length);
            for (let i = 0; i < results.length; i++) {
                results[i] = [];
            }
            for (let i in response.data) {
                var row = response.data[i];
                for (let j in row) {
                    var v = row[j];
                    if (v !== undefined && v != 2147483647 && j < column_length) {
                        results[j].push(v);
                    }
                }
            }
            console.debug("tabular-datasets::_fetch() - Fetching complete.");
            for (let i in results) {
                var column = column_list[i];
                var block_id = _block_id(dataset_id, column);
                _cache[block_id] = results[i];
            }
            _fillFromCache(options);
        }
    });
};

/** Fill data from cache */
var _fillFromCache = function(options) {
    var groups = options.dataset_groups;
    var dataset_id = options.dataset_id;
    console.debug("tabular-datasets::_fillFromCache() - Filling request from cache.");
    var limit = 0;
    groups.each(function(group) {
        _.each(group.get("__data_columns"), function(column_def, column_name) {
            var column = group.get(column_name);
            var block_id = _block_id(dataset_id, column);
            var column_data = _cache[block_id];
            if (column_data) {
                limit = Math.max(limit, column_data.length);
            }
        });
    });
    if (limit === 0) {
        console.debug("tabular-datasets::_fillFromCache() - No data available.");
        if (options.chart) {
            options.chart.state("failed", "No data available.");
        }
    }
    var results = [];
    groups.each(function(group, group_index) {
        var dict = Utils.merge({ key: group_index + ":" + group.get("key"), values: [] }, group.attributes);
        for (let j = 0; j < limit; j++) {
            dict.values[j] = { x: parseInt(j) };
        }
        results.push(dict);
    });
    groups.each(function(group, group_index) {
        var values = results[group_index].values;
        _.each(group.get("__data_columns"), function(column_def, column_name) {
            var column = group.get(column_name);
            switch (column) {
                case "auto":
                    for (let j = 0; j < limit; j++) {
                        values[j][column_name] = parseInt(j);
                    }
                    break;
                case "zero":
                    for (let j = 0; j < limit; j++) {
                        values[j][column_name] = 0;
                    }
                    break;
                default:
                    var block_id = _block_id(dataset_id, column);
                    var column_data = _cache[block_id];
                    for (let j = 0; j < limit; j++) {
                        var value = values[j];
                        var v = column_data[j];
                        if (isNaN(v) && !column_def.is_label) {
                            v = 0;
                        }
                        value[column_name] = v;
                    }
            }
        });
    });
    options.success(results);
};

/** Get block id */
var _block_id = function(dataset_id, column) {
    return dataset_id + "_" + "_" + column;
};

export default { request: request, requestPanels: requestPanels };
