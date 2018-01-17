import * as _ from "libs/underscore";
import Client from "mvc/visualization/chart/chart-client";
import Datasets from "mvc/visualization/chart/utilities/datasets";
import Helpers from "mvc/visualization/chart/utilities/helpers";
import Jobs from "mvc/visualization/chart/utilities/jobs";

window.bundleEntries = window.bundleEntries || {};

export const bundleEntries = {
    chart: function(options) {
        return new Client(options);
    },
    chartUtilities: {
        Datasets: Datasets,
        Helpers: Helpers,
        Jobs: Jobs
    }
};

_.extend(window.bundleEntries, bundleEntries);
