import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { HDADetailed, HDCADetailed, HDCASummary } from "@/api";

// Mutable mock state — tests assign into these to script the stores' replies.
const datasets: Record<string, Partial<HDADetailed>> = {};
const collections: Record<string, Partial<HDCASummary | HDCADetailed>> = {};
const datasetErrors: Record<string, Error> = {};
const collectionErrors: Record<string, Error> = {};

vi.mock("@/stores/datasetStore", () => ({
    useDatasetStore: () => ({
        getDataset: (id: string) => datasets[id] ?? null,
        getDatasetError: (id: string) => datasetErrors[id] ?? null,
    }),
}));

vi.mock("@/stores/datasetCollectionStore", () => ({
    useDatasetCollectionStore: () => ({
        getCollection: (id: string) => collections[id] ?? null,
        getCollectionError: (id: string) => collectionErrors[id] ?? null,
    }),
}));

// Import after mocks.
const { useCreatingJob } = await import("./useCreatingJob");

function reset() {
    for (const k of Object.keys(datasets)) {
        delete datasets[k];
    }
    for (const k of Object.keys(collections)) {
        delete collections[k];
    }
    for (const k of Object.keys(datasetErrors)) {
        delete datasetErrors[k];
    }
    for (const k of Object.keys(collectionErrors)) {
        delete collectionErrors[k];
    }
}

describe("useCreatingJob", () => {
    describe("HDA path", () => {
        it("returns the creating_job id when the dataset has one", () => {
            reset();
            datasets["d1"] = { creating_job: "job-42" };
            const { jobId, loading, error } = useCreatingJob(ref("d1"), ref("hda"));
            expect(jobId.value).toBe("job-42");
            expect(loading.value).toBe(false);
            expect(error.value).toBeNull();
        });

        it("surfaces a friendly error when the dataset has no creating_job", () => {
            reset();
            datasets["d1"] = {} as HDADetailed;
            const { jobId, error } = useCreatingJob(ref("d1"), ref("hda"));
            expect(jobId.value).toBeNull();
            expect(error.value).toMatch(/no creating job recorded/i);
        });

        it("reports loading while the dataset is absent and no error is set", () => {
            reset();
            const { loading, jobId } = useCreatingJob(ref("d1"), ref("hda"));
            expect(loading.value).toBe(true);
            expect(jobId.value).toBeNull();
        });

        it("propagates the store error when the dataset fetch fails", () => {
            reset();
            datasetErrors["d1"] = new Error("network down");
            const { jobId, loading, error } = useCreatingJob(ref("d1"), ref("hda"));
            expect(jobId.value).toBeNull();
            expect(loading.value).toBe(false);
            expect(error.value).toMatch(/network down/);
        });
    });

    describe("HDCA path", () => {
        it("returns job_source_id when the collection was produced by a single Job", () => {
            reset();
            collections["c1"] = { job_source_type: "Job", job_source_id: "job-77" } as HDCASummary;
            const { jobId, error } = useCreatingJob(ref("c1"), ref("hdca"));
            expect(jobId.value).toBe("job-77");
            expect(error.value).toBeNull();
        });

        it("surfaces the batch/workflow message when job_source_type is not 'Job'", () => {
            reset();
            collections["c1"] = { job_source_type: "ImplicitCollectionJobs" } as HDCASummary;
            const { jobId, error } = useCreatingJob(ref("c1"), ref("hdca"));
            expect(jobId.value).toBeNull();
            expect(error.value).toMatch(/not produced by a specific identifiable job/i);
        });

        it("propagates the store error when the collection fetch fails", () => {
            reset();
            collectionErrors["c1"] = new Error("boom");
            const { jobId, error } = useCreatingJob(ref("c1"), ref("hdca"));
            expect(jobId.value).toBeNull();
            expect(error.value).toMatch(/boom/);
        });
    });

    describe("input handling", () => {
        it("returns null for an unknown src", () => {
            reset();
            const { jobId, loading, error } = useCreatingJob(ref("x"), ref("tool_request"));
            expect(jobId.value).toBeNull();
            expect(loading.value).toBe(false);
            expect(error.value).toBeNull();
        });

        it("returns null when itemId is empty", () => {
            reset();
            const { jobId, loading } = useCreatingJob(ref(null), ref("hda"));
            expect(jobId.value).toBeNull();
            expect(loading.value).toBe(false);
        });

        it("re-targets to the new id when the input ref switches mid-flow", () => {
            reset();
            datasets["d1"] = { creating_job: "job-A" };
            datasets["d2"] = { creating_job: "job-B" };
            const id = ref<string | null>("d1");
            const { jobId } = useCreatingJob(id, ref("hda"));
            expect(jobId.value).toBe("job-A");
            id.value = "d2";
            expect(jobId.value).toBe("job-B");
        });
    });
});
