import ChartClient from "mvc/visualization/chart/chart-client";
export const bundleEntries = {
    chart: function chartEntry(options) {
        return new ChartClient.View(options);
    }
};
window.bundleEntries = bundleEntries;