import * as _ from "libs/underscore";
import ChartClient from "mvc/visualization/chart/chart-client";

window.bundleEntries = window.bundleEntries || {};

export const bundleEntries = {
    chart: function chartEntry(options) {
        return new ChartClient.View(options);
    }
};

_.extend(window.bundleEntries, bundleEntries);
