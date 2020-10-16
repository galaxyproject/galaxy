/**
 * These props are being exported with extended.js now since
 * extended is exposing its props on window via the expose-loader
 */

import Client from "mvc/visualization/chart/chart-client";
import Datasets from "mvc/visualization/chart/utilities/datasets";
import Series from "mvc/visualization/chart/utilities/series";
import Jobs from "mvc/visualization/chart/utilities/jobs";

export function chart(options) {
    return new Client(options);
}

export let chartUtilities = {
    Datasets: Datasets,
    Jobs: Jobs,
    Series: Series
};
