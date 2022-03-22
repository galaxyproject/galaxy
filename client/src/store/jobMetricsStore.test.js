import { jobMetricsStore } from "./jobMetricsStore";

describe("store/jobMetricsStore.js", () => {
    test("getter should return empty list for unfetched job IDs", () => {
        const state = {
            jobMetricsByJobId: {},
        };
        const metrics = jobMetricsStore.getters.getJobMetricsByJobId(state)("123");
        expect(metrics.length == 0).toBeTruthy();
    });

    test("should simply return fetched metrics list for job ID", () => {
        const state = {
            jobMetricsByJobId: { 123: [{ plugin: "core", value: 123 }] },
        };
        const metrics = jobMetricsStore.getters.getJobMetricsByJobId(state)("123");
        expect(metrics.length == 1).toBeTruthy();
    });
});
