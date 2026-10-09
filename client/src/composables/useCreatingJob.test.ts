import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { HDADetailed, HDCADetailed, HDCASummary } from "@/api";

import { useCreatingJob } from "./useCreatingJob";

const storeResponses = vi.hoisted(() => {
    const datasets: Record<string, Partial<HDADetailed>> = {};
    const collections: Record<string, Partial<HDCASummary | HDCADetailed>> = {};
    const datasetErrors: Record<string, Error> = {};
    const collectionErrors: Record<string, Error> = {};
    return { datasets, collections, datasetErrors, collectionErrors };
});
const { datasets, collections, datasetErrors, collectionErrors } = storeResponses;

vi.mock("@/stores/datasetStore", () => ({
    useDatasetStore: () => ({
        getDataset: (id: string) => storeResponses.datasets[id] ?? null,
        getDatasetError: (id: string) => storeResponses.datasetErrors[id] ?? null,
    }),
}));

vi.mock("@/stores/datasetCollectionStore", () => ({
    useDatasetCollectionStore: () => ({
        getCollection: (id: string) => storeResponses.collections[id] ?? null,
        getCollectionError: (id: string) => storeResponses.collectionErrors[id] ?? null,
    }),
}));

describe("useCreatingJob", () => {
    beforeEach(() => {
        for (const responses of Object.values(storeResponses)) {
            for (const id of Object.keys(responses)) {
                delete responses[id];
            }
        }
    });

    describe("datasets", () => {
        it("returns the creating_job id when the dataset has one", () => {
            datasets["dataset-1"] = { creating_job: "job-42" };
            const { jobId, loading, error } = useCreatingJob(ref("dataset-1"), ref("hda"));

            expect(jobId.value).toBe("job-42");
            expect(loading.value).toBe(false);
            expect(error.value).toBeNull();
        });

        it("surfaces a friendly error when the dataset has no creating_job", () => {
            datasets["dataset-1"] = {};
            const { jobId, error } = useCreatingJob(ref("dataset-1"), ref("hda"));
            expect(jobId.value).toBeNull();
            expect(error.value).toMatch(/no creating job recorded/i);
        });

        it("reports loading while the dataset is absent and no error is set", () => {
            const { loading, jobId } = useCreatingJob(ref("dataset-1"), ref("hda"));
            expect(loading.value).toBe(true);
            expect(jobId.value).toBeNull();
        });

        it("propagates the store error when the dataset fetch fails", () => {
            datasetErrors["dataset-1"] = new Error("network down");
            const { jobId, loading, error } = useCreatingJob(ref("dataset-1"), ref("hda"));

            expect(jobId.value).toBeNull();
            expect(loading.value).toBe(false);
            expect(error.value).toMatch(/network down/);
        });
    });

    describe("dataset collections", () => {
        it("returns job_source_id when the collection was produced by a single Job", () => {
            collections["collection-1"] = { job_source_type: "Job", job_source_id: "job-77" };
            const { jobId, error } = useCreatingJob(ref("collection-1"), ref("hdca"));
            expect(jobId.value).toBe("job-77");
            expect(error.value).toBeNull();
        });

        it("surfaces the batch/workflow message when job_source_type is not 'Job'", () => {
            collections["collection-1"] = { job_source_type: "ImplicitCollectionJobs" };
            const { jobId, error } = useCreatingJob(ref("collection-1"), ref("hdca"));
            expect(jobId.value).toBeNull();
            expect(error.value).toMatch(/not produced by a specific identifiable job/i);
        });

        it("propagates the store error when the collection fetch fails", () => {
            collectionErrors["collection-1"] = new Error("collection unavailable");
            const { jobId, error } = useCreatingJob(ref("collection-1"), ref("hdca"));
            expect(jobId.value).toBeNull();
            expect(error.value).toMatch(/collection unavailable/);
        });
    });

    describe("input handling", () => {
        it("returns null for an unknown src", () => {
            const { jobId, loading, error } = useCreatingJob(ref("x"), ref("tool_request"));
            expect(jobId.value).toBeNull();
            expect(loading.value).toBe(false);
            expect(error.value).toBeNull();
        });

        it("returns null when itemId is empty", () => {
            const { jobId, loading } = useCreatingJob(ref(null), ref("hda"));
            expect(jobId.value).toBeNull();
            expect(loading.value).toBe(false);
        });

        it("re-targets to the new id when the input ref switches mid-flow", () => {
            datasets["dataset-1"] = { creating_job: "job-A" };
            datasets["dataset-2"] = { creating_job: "job-B" };
            const id = ref<string | null>("dataset-1");
            const { jobId } = useCreatingJob(id, ref("hda"));
            expect(jobId.value).toBe("job-A");
            id.value = "dataset-2";
            expect(jobId.value).toBe("job-B");
        });
    });
});
