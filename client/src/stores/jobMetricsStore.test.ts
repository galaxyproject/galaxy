import { beforeEach, describe, expect, it } from "vitest";

import { useJobMetricsStore } from "./jobMetricsStore";
import { setupTestPinia } from "./testUtils";

describe("stores/jobMetricsStore", () => {
    const testPlugin = { plugin: "core", value: "123", title: "foo", name: "bar", raw_value: "raw-chicken" };

    beforeEach(setupTestPinia);

    it("returns an empty list for unfetched job and dataset IDs.", () => {
        const jobMetricsStore = useJobMetricsStore();

        expect(jobMetricsStore.getJobMetricsByJobId("123")).toEqual([]);
        expect(jobMetricsStore.getJobMetricsByDatasetId("123")).toEqual([]);
        expect(jobMetricsStore.getJobMetricsByDatasetId("123", "not-hda")).toEqual([]);
    });

    it("returns metrics for job ID.", () => {
        const jobMetricsStore = useJobMetricsStore();

        jobMetricsStore.jobMetricsByJobId["123"] = [testPlugin];

        const metrics = jobMetricsStore.getJobMetricsByJobId("123");

        expect(metrics.length).toBe(1);
        expect(metrics[0]).toEqual(testPlugin);
    });

    it("returns metrics by hda ID for dataset ID by default.", () => {
        const jobMetricsStore = useJobMetricsStore();

        jobMetricsStore.jobMetricsByHdaId["123"] = [testPlugin];

        const metrics = jobMetricsStore.getJobMetricsByDatasetId("123");

        expect(metrics.length).toBe(1);
        expect(metrics[0]).toEqual(testPlugin);
    });

    it("returns metrics by Ldda ID for dataset ID when dataset type is not hda.", () => {
        const jobMetricsStore = useJobMetricsStore();

        jobMetricsStore.jobMetricsByLddaId["123"] = [testPlugin];

        const metrics = jobMetricsStore.getJobMetricsByDatasetId("123", "not-hda");

        expect(metrics.length).toBe(1);
        expect(metrics[0]).toEqual(testPlugin);
    });
});
