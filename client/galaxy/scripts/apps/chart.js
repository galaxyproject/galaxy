import * as _ from "libs/underscore";
import Client from "mvc/visualization/chart/chart-client";
import Datasets from "mvc/visualization/chart/utilities/datasets";
import Series from "mvc/visualization/chart/utilities/series";
import Jobs from "mvc/visualization/chart/utilities/jobs";

window.bundleEntries = window.bundleEntries || {};

export const bundleEntries = {
    chart: function(options) {
        return new Client(options);
    },
    chartUtilities: {
        Datasets: Datasets,
        Jobs: Jobs,
        Series: Series
    }
};

_.extend(window.bundleEntries, bundleEntries);
