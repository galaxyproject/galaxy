import { getLocalVue, suppressExpectedErrorMessages, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";

import { GALAXY_RESPONSE_HEADERS, useServerMock } from "@/api/client/__mocks__";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { makeCollectionConfig, makeLibraryItem, makeUrlItem } from "@/composables/upload/testHelpers/uploadFixtures";
import { useUploadBatchOperations } from "@/composables/upload/useUploadBatchOperations";
import { setupTestPinia } from "@/stores/testUtils";
import * as uploadUtils from "@/utils/upload";
import { buildPreparedUpload } from "@/utils/upload";

import { useUploadSubmission } from "./useUploadSubmission";

enableAutoUnmount(afterEach);
const { server } = useServerMock();

async function mountSubmission(prepared: PreparedUpload, targetObjectStoreId?: string) {
    let submission: ReturnType<typeof useUploadSubmission> | undefined;
    // useConfig loads configuration on mount, so the composable needs a component context.
    const Harness = defineComponent({
        setup() {
            submission = useUploadSubmission();
        },
        template: "<div />",
    });
    mount(Harness, { global: withPlugins(getLocalVue(), createPinia()) });
    await flushPromises();
    if (!submission) {
        throw new Error("Upload submission harness did not initialize");
    }
    const { submitPreparedUpload } = submission;
    return () => submitPreparedUpload("hist_1", prepared, undefined, targetObjectStoreId);
}

function makeSubmissionCollectionConfig() {
    return makeCollectionConfig({
        name: "Uploaded Collection",
        hideSourceItems: true,
    });
}

describe("useUploadSubmission", () => {
    beforeEach(() => {
        setupTestPinia();
        useUploadState().clearAll();

        server.use(http.get("/api/configuration", () => HttpResponse.json({ chunk_upload_size: 42 })));
    });

    afterEach(() => {
        useUploadState().clearAll();
        vi.restoreAllMocks();
    });

    it("submits mixed uploads, tracks completion, and flattens nested fetch outputs", async () => {
        server.use(
            http.post("/api/tools/fetch", () =>
                HttpResponse.json({
                    jobs: [{ id: "job_1" }],
                    outputs: {
                        first: { id: "hda_1", name: "api dataset", hid: 1, src: "hda" },
                        nested: [
                            { duplicate: { id: "hda_1", name: "duplicate", hid: 1, src: "hda" } },
                            { id: "hdca_1", name: "api collection", src: "hdca" },
                        ],
                    },
                }),
            ),
            http.post("/api/histories/hist_1/contents/datasets", async ({ request }) => {
                const body = await request.json();
                expect(body).toMatchObject({
                    content: "ldda_1",
                    source: "library",
                    type: "dataset",
                });
                return HttpResponse.json({ id: "hda_2", name: "copied library", hid: 2 });
            }),
        );

        const apiItem = makeUrlItem({ name: "remote.txt", url: "https://example.org/remote.txt" });
        const apiPrepared = buildPreparedUpload([apiItem]);
        const submit = await mountSubmission({
            apiItems: apiPrepared.apiItems,
            uploadItems: [apiItem, makeLibraryItem()],
        });
        const datasets = await submit();

        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_1" }));
        expect(datasets).toContainEqual(expect.objectContaining({ id: "hdca_1" }));
        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_2" }));

        const state = useUploadState();
        const pastedEntry = state.activeItems.value.find((item) => item.name === "remote.txt");
        const libraryEntry = state.activeItems.value.find((item) => item.name === "library.txt");

        expect(pastedEntry?.status).toBe("processing");
        expect(pastedEntry?.progress).toBe(100);
        expect(pastedEntry?.datasetIds).toEqual(["hda_1"]);
        expect(libraryEntry?.status).toBe("processing");
        expect(libraryEntry?.progress).toBe(100);
        expect(libraryEntry?.datasetIds).toEqual(["hda_2"]);
    });

    it("preserves every dataset from standalone URL uploads", async () => {
        let requestCount = 0;
        server.use(
            http.post("/api/tools/fetch", () => {
                requestCount += 1;
                return HttpResponse.json({
                    outputs: [{ id: `hda_url_${requestCount}`, name: `url-${requestCount}.txt`, src: "hda" }],
                });
            }),
        );

        const firstItem = makeUrlItem({ name: "first.txt", url: "https://example.org/first.txt" });
        const secondItem = makeUrlItem({ name: "second.txt", url: "https://example.org/second.txt" });
        const submit = await mountSubmission(buildPreparedUpload([firstItem, secondItem]));
        const datasets = await submit();

        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_url_1" }));
        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_url_2" }));
        expect(useUploadState().activeItems.value.every((item) => item.status === "processing")).toBe(true);
        expect(useUploadState().activeItems.value.every((item) => item.datasetIds.length === 1)).toBe(true);
    });

    it("marks only the fetched uploads as errored when the fetch request fails", async () => {
        server.use(
            http.post("/api/tools/fetch", async () => {
                // Fail the fetch only once the library copy running beside it has succeeded.
                await vi.waitFor(() => {
                    expect(useUploadState().activeItems.value[1]?.status).toBe("processing");
                });
                return HttpResponse.json(
                    { err_msg: "upload failed" },
                    { status: 500, headers: GALAXY_RESPONSE_HEADERS },
                );
            }),
            http.post("/api/histories/hist_1/contents/datasets", () =>
                HttpResponse.json({ id: "hda_2", name: "copied library", hid: 2 }),
            ),
        );

        const apiItem = makeUrlItem({ name: "remote.txt", url: "https://example.org/broken.txt" });
        const apiPrepared = buildPreparedUpload([apiItem]);
        const submit = await mountSubmission({
            apiItems: apiPrepared.apiItems,
            uploadItems: [apiItem, makeLibraryItem()],
        });
        await expect(submit()).rejects.toThrow("upload failed");

        const [apiUpload, libraryUpload] = useUploadState().activeItems.value;
        expect(apiUpload?.status).toBe("error");
        expect(apiUpload?.error).toBe("upload failed");
        expect(libraryUpload?.status).toBe("processing");
        expect(libraryUpload?.datasetIds).toEqual(["hda_2"]);
    });

    it("marks the failed and remaining library copies as errored when a copy request fails", async () => {
        server.use(
            http.post("/api/histories/hist_1/contents/datasets", () =>
                HttpResponse.json(
                    { err_msg: "Action requires account activation." },
                    { status: 403, headers: GALAXY_RESPONSE_HEADERS },
                ),
            ),
        );

        const submit = await mountSubmission({
            apiItems: [],
            uploadItems: [
                makeLibraryItem({ name: "first.txt", lddaId: "ldda_1" }),
                makeLibraryItem({ name: "second.txt", lddaId: "ldda_2" }),
            ],
        });
        await expect(submit()).rejects.toThrow("Action requires account activation.");

        const state = useUploadState();
        expect(state.activeItems.value).toHaveLength(2);
        for (const item of state.activeItems.value) {
            expect(item.status).toBe("error");
            expect(item.error).toBe("Action requires account activation.");
        }
    });

    it("falls back to the staged library item name when the copy response omits metadata", async () => {
        server.use(
            http.post("/api/histories/hist_1/contents/datasets", async ({ request }) => {
                const body = await request.json();
                expect(body).toMatchObject({
                    content: "ldda_3",
                    source: "library",
                    type: "dataset",
                });
                return HttpResponse.json({ id: "hda_3" });
            }),
        );

        const submit = await mountSubmission({
            apiItems: [],
            uploadItems: [makeLibraryItem({ name: "fallback-name.txt", lddaId: "ldda_3" })],
        });
        const datasets = await submit();

        expect(datasets).toContainEqual(expect.objectContaining({ name: "fallback-name.txt" }));
        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_3" }));
    });

    it("resolves the submission promise while a cancelled fetch response is still pending", async () => {
        let releaseFetch = () => {};
        const fetchReleased = new Promise<void>((resolve) => {
            releaseFetch = resolve;
        });
        let markFetchStarted = () => {};
        const fetchStarted = new Promise<void>((resolve) => {
            markFetchStarted = resolve;
        });
        server.use(
            http.post("/api/tools/fetch", async () => {
                markFetchStarted();
                await fetchReleased;
                return HttpResponse.json({
                    jobs: [{ id: "job_cancelled" }],
                    outputs: [{ id: "hda_cancelled", name: "cancelled.txt", hid: 1, src: "hda" }],
                });
            }),
        );

        const apiItem = makeUrlItem({ name: "cancelled.txt", url: "https://example.org/cancelled.txt" });
        const submit = await mountSubmission(buildPreparedUpload([apiItem]));
        const pendingSubmission = submit();

        try {
            await fetchStarted;
            const itemId = useUploadState().activeItems.value[0]?.id;
            expect(itemId).toBeDefined();
            useUploadBatchOperations({ autoRecover: false }).cancelUpload(itemId!);

            await expect(pendingSubmission).resolves.toEqual([]);
            expect(useUploadState().activeItems.value[0]?.status).toBe("cancelled");
            expect(useUploadState().activeItems.value[0]?.datasetIds).toEqual([]);
        } finally {
            releaseFetch();
        }
    });

    it("groups direct collection uploads into a batch in upload state", async () => {
        server.use(
            http.post("/api/tools/fetch", async ({ request }) => {
                const body = await request.json();

                expect(body).toMatchObject({
                    history_id: "hist_1",
                    targets: [
                        {
                            destination: { type: "hdca" },
                            collection_type: "list",
                            name: "Uploaded Collection",
                        },
                    ],
                });

                return HttpResponse.json({
                    jobs: [{ id: "job_1" }],
                    outputs: [],
                    output_collections: [{ id: "hdca_2", name: "Uploaded Collection" }],
                });
            }),
        );

        const firstItem = makeUrlItem({ name: "1.bed", url: "https://example.org/1.bed" });
        const secondItem = makeUrlItem({ name: "2.bed", url: "https://example.org/2.bed" });
        const prepared = buildPreparedUpload([firstItem, secondItem], makeSubmissionCollectionConfig());
        const submit = await mountSubmission(prepared);
        const datasets = await submit();

        expect(datasets).toContainEqual(expect.objectContaining({ id: "hdca_2" }));

        const state = useUploadState();
        const batch = state.activeBatches.value[0];

        expect(batch?.name).toBe("Uploaded Collection");
        expect(batch?.status).toBe("processing");
        expect(batch?.collectionId).toBe("hdca_2");
        expect(batch?.uploadIds).toHaveLength(2);
        expect(state.standaloneUploads.value).toHaveLength(0);
        expect(state.orderedUploadItems.value[0]?.type).toBe("batch");
        expect(state.activeItems.value.every((item) => item.batchId === batch?.id)).toBe(true);
    });

    it("forwards the selected preferred object store id to fetch uploads", async () => {
        server.use(
            http.post("/api/tools/fetch", async ({ request }) => {
                const body = await request.json();
                expect(body).toMatchObject({
                    history_id: "hist_1",
                    preferred_object_store_id: "object_store_2",
                });

                return HttpResponse.json({
                    jobs: [{ id: "job_1" }],
                    outputs: [{ id: "hda_store_1", name: "stored.txt", hid: 1, src: "hda" }],
                });
            }),
        );

        const apiItem = makeUrlItem({ name: "stored.txt", url: "https://example.org/stored.txt" });
        const submit = await mountSubmission(buildPreparedUpload([apiItem]), "object_store_2");
        const datasets = await submit();

        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_store_1" }));
    });

    it("creates a two-step collection for library-only uploads", async () => {
        server.use(
            http.post("/api/histories/hist_1/contents/datasets", () => HttpResponse.json({ id: "hda_lib_1", hid: 3 })),
            http.post("/api/dataset_collections", async ({ request }) => {
                const body = await request.json();
                expect(body).toMatchObject({
                    history_id: "hist_1",
                    collection_type: "list",
                    name: "Uploaded Collection",
                    element_identifiers: [{ id: "hda_lib_1", src: "hda" }],
                });
                return HttpResponse.json({ id: "hdca_lib_1" });
            }),
        );

        const prepared = buildPreparedUpload([makeLibraryItem()], makeSubmissionCollectionConfig());
        const submit = await mountSubmission(prepared);
        const datasets = await submit();

        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_lib_1" }));

        const batch = useUploadState().activeBatches.value[0];
        expect(batch?.status).toBe("processing");
        expect(batch?.collectionId).toBe("hdca_lib_1");
        expect(batch?.datasetIds).toEqual(["hda_lib_1"]);
    });

    it("fails the collection batch when a library copy fails", async () => {
        suppressExpectedErrorMessages(["Action requires account activation."]);
        server.use(
            http.post("/api/histories/hist_1/contents/datasets", () =>
                HttpResponse.json(
                    { err_msg: "Action requires account activation." },
                    { status: 403, headers: GALAXY_RESPONSE_HEADERS },
                ),
            ),
        );

        const prepared = buildPreparedUpload([makeLibraryItem()], makeSubmissionCollectionConfig());
        const submit = await mountSubmission(prepared);
        await expect(submit()).rejects.toThrow("Action requires account activation.");

        const batch = useUploadState().activeBatches.value[0];
        expect(batch?.status).toBe("error");
        expect(batch?.error).toBe("Action requires account activation.");
        expect(batch?.collectionId).toBeUndefined();
    });

    it("creates a two-step collection for mixed api and library uploads", async () => {
        server.use(
            http.post("/api/tools/fetch", () =>
                HttpResponse.json({
                    outputs: [{ id: "hda_api_1", name: "api dataset", hid: 1, src: "hda" }],
                }),
            ),
            http.post("/api/histories/hist_1/contents/datasets", () => HttpResponse.json({ id: "hda_lib_2", hid: 2 })),
            http.post("/api/dataset_collections", async ({ request }) => {
                const body = await request.json();
                expect(body).toMatchObject({
                    history_id: "hist_1",
                    collection_type: "list",
                    name: "Uploaded Collection",
                    element_identifiers: [
                        { id: "hda_api_1", src: "hda" },
                        { id: "hda_lib_2", src: "hda" },
                    ],
                });
                return HttpResponse.json({ id: "hdca_mixed_1" });
            }),
        );

        const apiItem = makeUrlItem({ name: "api-first.txt" });
        const libraryItem = makeLibraryItem({ name: "library-second.txt", lddaId: "ldda_2" });
        const submit = await mountSubmission(
            buildPreparedUpload([apiItem, libraryItem], makeSubmissionCollectionConfig()),
        );
        const datasets = await submit();

        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_api_1" }));
        expect(datasets).toContainEqual(expect.objectContaining({ id: "hda_lib_2" }));

        const batch = useUploadState().activeBatches.value[0];
        expect(batch?.status).toBe("processing");
        expect(batch?.collectionId).toBe("hdca_mixed_1");
        expect(batch?.datasetIds).toEqual(["hda_api_1", "hda_lib_2"]);
    });

    it("surfaces two-step collection creation failures after uploads succeed", async () => {
        suppressExpectedErrorMessages(["Collection error"]);
        server.use(
            http.post("/api/histories/hist_1/contents/datasets", () => HttpResponse.json({ id: "hda_lib_3", hid: 4 })),
            http.post("/api/dataset_collections", () =>
                HttpResponse.json({ err_msg: "Collection error" }, { status: 500, headers: GALAXY_RESPONSE_HEADERS }),
            ),
        );

        const submit = await mountSubmission(
            buildPreparedUpload([makeLibraryItem({ lddaId: "ldda_3" })], makeSubmissionCollectionConfig()),
        );
        await expect(submit()).rejects.toThrow("Collection error");

        const batch = useUploadState().activeBatches.value[0];
        expect(batch?.status).toBe("error");
        expect(batch?.collectionId).toBeUndefined();
    });

    it("falls back to the default chunk size when the server config reports 0", async () => {
        server.use(http.get("/api/configuration", () => HttpResponse.json({ chunk_upload_size: 0 })));

        const uploadDatasetsSpy = vi.spyOn(uploadUtils, "uploadDatasets").mockResolvedValue(undefined);
        const apiItem = makeUrlItem({ name: "remote.txt", url: "https://example.org/remote.txt" });
        const submit = await mountSubmission({
            apiItems: buildPreparedUpload([apiItem]).apiItems,
            uploadItems: [apiItem],
        });
        await submit();

        expect(uploadDatasetsSpy).toHaveBeenCalledOnce();
        expect(uploadDatasetsSpy.mock.calls[0]?.[1]).toMatchObject({
            chunkSize: 10485760,
        });
    });

    it("gives each standalone upload its own AbortSignal", async () => {
        const uploadDatasetsSpy = vi.spyOn(uploadUtils, "uploadDatasets").mockResolvedValue(undefined);
        const firstItem = makeUrlItem({ name: "1.txt", url: "https://example.org/1.txt" });
        const secondItem = makeUrlItem({ name: "2.txt", url: "https://example.org/2.txt" });
        const submit = await mountSubmission(buildPreparedUpload([firstItem, secondItem]));

        await submit();

        expect(uploadDatasetsSpy).toHaveBeenCalledOnce();
        const standaloneConfig = uploadDatasetsSpy.mock.calls[0]?.[1];
        expect(standaloneConfig?.signal).toBeUndefined();
        expect(standaloneConfig?.signals).toHaveLength(2);
        expect(standaloneConfig?.signals?.[0]).toBeInstanceOf(AbortSignal);
        expect(standaloneConfig?.signals?.[1]).toBeInstanceOf(AbortSignal);
        expect(standaloneConfig?.signals?.[0]).not.toBe(standaloneConfig?.signals?.[1]);
    });

    it("shares one AbortSignal across a direct collection batch", async () => {
        const uploadCollectionDatasetsSpy = vi
            .spyOn(uploadUtils, "uploadCollectionDatasets")
            .mockResolvedValue(undefined);
        const firstItem = makeUrlItem({ name: "1.bed", url: "https://example.org/1.bed" });
        const secondItem = makeUrlItem({ name: "2.bed", url: "https://example.org/2.bed" });
        const submit = await mountSubmission(
            buildPreparedUpload([firstItem, secondItem], makeSubmissionCollectionConfig()),
        );

        await submit();

        expect(uploadCollectionDatasetsSpy).toHaveBeenCalledOnce();
        const batchConfig = uploadCollectionDatasetsSpy.mock.calls[0]?.[2];
        expect(batchConfig?.signal).toBeInstanceOf(AbortSignal);
        expect(batchConfig?.signals).toBeUndefined();
    });
});
