import { jobMetricsStore } from "./jobMetricsStore";

describe("store/jobMetricsStore.js", () => {
    it("getter should return empty list for unfetched job IDs", () => {
        const state = {
            jobMetricsByJobId: {},
        };
        let metrics = jobMetricsStore.getters.getJobMetricsByJobId(state)("123");
        assert(metrics.length == 0);
    });

    it("should simply return fetched metrics list for job ID", () => {
        const state = {
            jobMetricsByJobId: { "123": [{ plugin: "core", value: 123 }] },
        };
        let metrics = jobMetricsStore.getters.getJobMetricsByJobId(state)("123");
        assert(metrics.length == 1);
    });
});
