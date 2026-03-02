import { suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import assert from "assert";
import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";

import { type CollectionConfig, useUploadQueue, validateUploadItem } from "./uploadQueue";

// TUS upload is a non-HTTP protocol — mock it so tests never attempt real TUS connections.
vi.mock("@/utils/tusUpload", () => ({
    createTusUpload: vi.fn(),
    NamedBlob: class {},
}));

const { server } = useServerMock();

/** Creates a paste-content upload item, used only for validateUploadItem tests. */
function makePastedItem(overrides: Partial<NewUploadItem> = {}): NewUploadItem {
    return {
        uploadMode: "paste-content",
        name: "file.txt",
        content: "hello world",
        size: 11,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        ...overrides,
    } as NewUploadItem;
}

/** Creates a paste-links (URL) upload item. URL items use direct fetchDatasets — no TUS involved. */
function makeUrlItem(overrides: Partial<NewUploadItem> = {}): NewUploadItem {
    return {
        uploadMode: "paste-links",
        name: "file.txt",
        url: "http://example.com/file.txt",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        ...overrides,
    } as NewUploadItem;
}

/** Creates a remote-files upload item. Same shape as paste-links but with a different uploadMode. */
function makeRemoteFilesItem(overrides: Partial<NewUploadItem> = {}): NewUploadItem {
    return {
        uploadMode: "remote-files",
        name: "file.txt",
        url: "ftp://server/file.txt",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        ...overrides,
    } as NewUploadItem;
}

/** Creates a data-library upload item for testing the two-step collection path. */
function makeLibraryItem(overrides: Partial<NewUploadItem> = {}): NewUploadItem {
    return {
        uploadMode: "data-library",
        name: "library.txt",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        libraryId: "lib_1",
        folderId: "folder_1",
        lddaId: "ldda_1",
        url: "/api/libraries/lib_1/datasets/ldda_1",
        ...overrides,
    } as NewUploadItem;
}

function makeCollectionConfig(overrides: Partial<CollectionConfig> = {}): CollectionConfig {
    return {
        name: "My Collection",
        type: "list",
        historyId: "hist_1",
        hideSourceItems: false,
        ...overrides,
    };
}

describe("validateUploadItem", () => {
    it("accepts a valid paste-content item", () => {
        expect(validateUploadItem(makePastedItem())).toBeUndefined();
    });

    it("accepts a valid paste-links item", () => {
        expect(validateUploadItem(makeUrlItem())).toBeUndefined();
    });

    it("accepts a valid remote-files item", () => {
        expect(validateUploadItem(makeRemoteFilesItem())).toBeUndefined();
    });

    it("accepts a valid data-library item", () => {
        expect(validateUploadItem(makeLibraryItem())).toBeUndefined();
    });

    it("accepts a valid local-file item", () => {
        const file = new File(["content"], "test.txt");
        const item: NewUploadItem = {
            uploadMode: "local-file",
            name: "test.txt",
            size: file.size,
            targetHistoryId: "hist_1",
            dbkey: "?",
            extension: "auto",
            spaceToTab: false,
            toPosixLines: false,
            deferred: false,
            fileData: file,
        };
        expect(validateUploadItem(item)).toBeUndefined();
    });

    it("rejects paste-content with empty content", () => {
        const item = makePastedItem({ content: "   " });
        expect(validateUploadItem(item)).toMatch(/No content provided/);
    });

    it("rejects paste-links with missing URL", () => {
        expect(validateUploadItem(makeUrlItem({ url: "" }))).toMatch(/No URL provided/);
    });

    it("rejects remote-files with missing URL", () => {
        expect(validateUploadItem(makeRemoteFilesItem({ url: "  " }))).toMatch(/No URL provided/);
    });

    it("rejects data-library with no lddaId", () => {
        expect(validateUploadItem(makeLibraryItem({ lddaId: "" }))).toMatch(/No library dataset ID/);
    });

    it("rejects local-file with no file data", () => {
        const item: NewUploadItem = {
            uploadMode: "local-file",
            name: "missing.txt",
            size: 0,
            targetHistoryId: "hist_1",
            dbkey: "?",
            extension: "auto",
            spaceToTab: false,
            toPosixLines: false,
            deferred: false,
        };
        expect(validateUploadItem(item)).toMatch(/No file selected/);
    });

    it("rejects local-file with an empty file", () => {
        const emptyFile = new File([], "empty.txt");
        const item: NewUploadItem = {
            uploadMode: "local-file",
            name: "empty.txt",
            size: 0,
            targetHistoryId: "hist_1",
            dbkey: "?",
            extension: "auto",
            spaceToTab: false,
            toPosixLines: false,
            deferred: false,
            fileData: emptyFile,
        };
        expect(validateUploadItem(item)).toMatch(/is empty/);
    });

    it("rejects an unknown upload mode", () => {
        const item = { ...makePastedItem(), uploadMode: "unknown-mode" } as unknown as NewUploadItem;
        expect(validateUploadItem(item)).toMatch(/Unknown upload mode/);
    });
});

describe("useUploadQueue", () => {
    let queue: ReturnType<typeof useUploadQueue>;

    beforeEach(() => {
        // Fresh Pinia instance for each test to prevent cross-test store state.
        setActivePinia(createPinia());
        // Reset the shared upload state singleton before creating a new queue.
        useUploadState().clearAll();
        // Each call creates fresh local queue/batch state and re-runs recoverIncompleteBatches.
        queue = useUploadQueue();
    });

    describe("enqueue — single item", () => {
        it("marks the item as completed after a successful upload", async () => {
            server.use(http.post("/api/tools/fetch", () => HttpResponse.json({})));

            const [id] = queue.enqueue([makeUrlItem()]);
            await flushPromises();

            expect(queue.state.activeItems.value.find((i) => i.id === id)?.status).toBe("completed");
        });

        it("processes multiple items sequentially — all reach completed status", async () => {
            server.use(http.post("/api/tools/fetch", () => HttpResponse.json({})));

            const ids = queue.enqueue([
                makeUrlItem({ name: "a.txt" }),
                makeUrlItem({ name: "b.txt" }),
                makeUrlItem({ name: "c.txt" }),
            ]);
            await flushPromises();

            for (const id of ids) {
                expect(queue.state.activeItems.value.find((i) => i.id === id)?.status).toBe("completed");
            }
        });

        it("marks the item as error when the upload endpoint returns an error", async () => {
            server.use(
                http.post("/api/tools/fetch", () =>
                    HttpResponse.json({ err_msg: "Server unavailable" }, { status: 500 }),
                ),
            );

            const [id] = queue.enqueue([makeUrlItem()]);
            await flushPromises();

            const item = queue.state.activeItems.value.find((i) => i.id === id);
            expect(item?.status).toBe("error");
            expect(item?.error).toBeTruthy();
        });
    });

    describe("enqueue — direct collection batch", () => {
        it("marks the batch as completed after a successful collection upload", async () => {
            server.use(http.post("/api/tools/fetch", () => HttpResponse.json({})));

            queue.enqueue([makeUrlItem({ name: "a.txt" }), makeUrlItem({ name: "b.txt" })], makeCollectionConfig());
            await flushPromises();

            const batch = queue.state.activeBatches.value[0];
            expect(batch?.status).toBe("completed");
        });

        it("marks the batch as error when the upload endpoint fails", async () => {
            suppressExpectedErrorMessages(["Upload failed"]);
            server.use(
                http.post("/api/tools/fetch", () => HttpResponse.json({ err_msg: "Upload failed" }, { status: 500 })),
            );

            queue.enqueue([makeUrlItem()], makeCollectionConfig());
            await flushPromises();

            const batch = queue.state.activeBatches.value[0];
            expect(batch?.status).toBe("error");
        });
    });

    // ── Two-step collection batch (data-library items) ───────────────────────
    //
    // data-library items cannot use direct HDCA creation (they use copyDataset instead
    // of /api/tools/fetch). Each item is uploaded individually; after all items complete,
    // the collection is created via POST /api/dataset_collections.

    describe("enqueue — two-step collection batch (data-library)", () => {
        it("creates the collection after all library items are successfully copied", async () => {
            server.use(
                http.post("/api/histories/:historyId/contents/:type", () => HttpResponse.json({ id: "ds_lib_1" })),
                http.post("/api/dataset_collections", () => HttpResponse.json({ id: "col_1" })),
            );

            queue.enqueue([makeLibraryItem()], makeCollectionConfig());
            await flushPromises();

            const batch = queue.state.activeBatches.value[0];
            expect(batch?.status).toBe("completed");
            expect(batch?.collectionId).toBe("col_1");
        });

        it("marks the batch as error when collection creation fails after successful uploads", async () => {
            suppressExpectedErrorMessages(["Collection creation failed:", "Collection error"]);
            server.use(
                http.post("/api/histories/:historyId/contents/:type", () => HttpResponse.json({ id: "ds_lib_1" })),
                http.post("/api/dataset_collections", () =>
                    HttpResponse.json({ err_msg: "Collection error" }, { status: 500 }),
                ),
            );

            queue.enqueue([makeLibraryItem()], makeCollectionConfig());
            await flushPromises();

            const batch = queue.state.activeBatches.value[0];
            expect(batch?.status).toBe("error");
            expect(batch?.collectionId).toBeUndefined();
        });
    });

    describe("retryCollectionCreation", () => {
        it("re-attempts collection creation and resolves the batch after a previous failure", async () => {
            suppressExpectedErrorMessages(["Collection creation failed:", "Temporary error"]);

            // Phase 1: uploads succeed, collection creation fails.
            server.use(
                http.post("/api/histories/:historyId/contents/:type", () => HttpResponse.json({ id: "ds_lib_1" })),
                http.post("/api/dataset_collections", () =>
                    HttpResponse.json({ err_msg: "Temporary error" }, { status: 500 }),
                ),
            );

            queue.enqueue([makeLibraryItem()], makeCollectionConfig());
            await flushPromises();

            const batchId = queue.state.activeBatches.value[0]?.id;
            assert(batchId, "Expected a batch to be created");
            expect(queue.state.getBatch(batchId)?.status).toBe("error");

            // Phase 2: collection creation now succeeds.
            server.use(http.post("/api/dataset_collections", () => HttpResponse.json({ id: "col_retried" })));

            await queue.retryCollectionCreation(batchId);
            await flushPromises();

            expect(queue.state.getBatch(batchId)?.status).toBe("completed");
            expect(queue.state.getBatch(batchId)?.collectionId).toBe("col_retried");
        });
    });

    describe("clearCompleted", () => {
        it("removes completed uploads from state", async () => {
            server.use(http.post("/api/tools/fetch", () => HttpResponse.json({})));

            const [completedId] = queue.enqueue([makeUrlItem()]);
            await flushPromises();

            expect(queue.state.activeItems.value.find((i) => i.id === completedId)?.status).toBe("completed");

            queue.clearCompleted();

            expect(queue.state.activeItems.value.find((i) => i.id === completedId)).toBeUndefined();
        });
    });

    describe("clearAll", () => {
        it("empties all items, batches, and internal queue state", async () => {
            server.use(http.post("/api/tools/fetch", () => HttpResponse.json({})));

            queue.enqueue([makeUrlItem(), makeUrlItem()], makeCollectionConfig());
            await flushPromises();

            queue.clearAll();

            expect(queue.state.activeItems.value).toHaveLength(0);
            expect(queue.state.activeBatches.value).toHaveLength(0);
        });
    });

    // On initialization, the queue checks for two-step batches where uploads completed
    // in a previous session but collection creation did not finish (e.g. page was refreshed).
    describe("recoverIncompleteBatches", () => {
        it("automatically creates the collection for a two-step batch with completed uploads and dataset IDs", async () => {
            const uploadState = useUploadState();

            // Simulate state left from a previous browser session:
            // one completed upload item and a pending two-step batch with a dataset ID.
            const itemId = uploadState.addUploadItem(makeUrlItem({ name: "recovered.txt" }));
            uploadState.setStatus(itemId, "uploading");
            uploadState.updateProgress(itemId, 100); // auto-marks as completed

            const batchId = uploadState.addBatch(
                { name: "Recovery Collection", type: "list", hideSourceItems: false, historyId: "hist_1" },
                [itemId],
                false, // not directCreation — qualifies for recovery
            );
            uploadState.addBatchDatasetId(batchId, "ds_recovered");

            server.use(http.post("/api/dataset_collections", () => HttpResponse.json({ id: "col_recovered" })));

            // Creating a new queue instance triggers recoverIncompleteBatches.
            const recoveryQueue = useUploadQueue();
            await flushPromises();

            expect(recoveryQueue.state.getBatch(batchId)?.collectionId).toBe("col_recovered");
            expect(recoveryQueue.state.getBatch(batchId)?.status).toBe("completed");
        });
    });
});
