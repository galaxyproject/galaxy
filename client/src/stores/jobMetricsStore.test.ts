import { createPinia, setActivePinia } from "pinia";

import { useJobMetricsStore } from "./jobMetricsStore";

describe("stores/jobMetricsStore", () => {
    const testPlugin = { plugin: "core", value: "123", title: "foo", name: "bar", raw_value: "raw-chicken" };

    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("returns an empty list for unfetched job and dataset IDs.", () => {
        const jobMetricsStore = useJobMetricsStore();

        jobMetricsStore.$state = {
            jobMetricsByJobId: {},
            jobMetricsByHdaId: {},
            jobMetricsByLddaId: {},
        };

        expect(jobMetricsStore.getJobMetricsByJobId("123").length).toBe(0);
        expect(jobMetricsStore.getJobMetricsByDatasetId("123").length).toBe(0);
        expect(jobMetricsStore.getJobMetricsByDatasetId("123", "not-hda").length).toBe(0);
    });

    it("returns metrics for job ID.", () => {
        const jobMetricsStore = useJobMetricsStore();

        jobMetricsStore.$state = {
            jobMetricsByJobId: { 123: [testPlugin] },
            jobMetricsByHdaId: {},
            jobMetricsByLddaId: {},
        };

        const metrics = jobMetricsStore.getJobMetricsByJobId("123");

        expect(metrics.length).toBe(1);
        expect(metrics[0]).toEqual(testPlugin);
    });

    it("returns metrics by hda ID for dataset ID by default.", () => {
        const jobMetricsStore = useJobMetricsStore();

        jobMetricsStore.$state = {
            jobMetricsByJobId: {},
            jobMetricsByHdaId: { 123: [testPlugin] },
            jobMetricsByLddaId: {},
        };

        const metrics = jobMetricsStore.getJobMetricsByDatasetId("123");

        expect(metrics.length).toBe(1);
        expect(metrics[0]).toEqual(testPlugin);
    });

    it("returns metrics by Ldda ID for dataset ID when dataset type is not hda.", () => {
        const jobMetricsStore = useJobMetricsStore();

        jobMetricsStore.$state = {
            jobMetricsByJobId: {},
            jobMetricsByHdaId: {},
            jobMetricsByLddaId: { 123: [testPlugin] },
        };

        const metrics = jobMetricsStore.getJobMetricsByDatasetId("123", "not-hda");

        expect(metrics.length).toBe(1);
        expect(metrics[0]).toEqual(testPlugin);
    });
});
