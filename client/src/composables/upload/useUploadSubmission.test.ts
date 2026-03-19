import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { defineComponent, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import type { UploadCollectionConfig } from "@/composables/upload/collectionTypes";
import type { LibraryDatasetUploadItem, UrlUploadItem } from "@/composables/upload/uploadItemTypes";
import { buildPreparedUpload } from "@/utils/upload";

import { useUploadSubmission } from "./useUploadSubmission";

const SELECTORS = {
    RUN: "[data-test-id='run']",
    RESULT: "[data-test-id='result']",
    ERROR: "[data-test-id='error']",
};

const localVue = getLocalVue();
const { server } = useServerMock();

function makeUrlItem(overrides: Partial<UrlUploadItem> = {}): UrlUploadItem {
    return {
        uploadMode: "paste-links",
        name: "remote.txt",
        url: "https://example.org/remote.txt",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        deferred: false,
        ...overrides,
    };
}

function makeLibraryItem(overrides: Partial<LibraryDatasetUploadItem> = {}): LibraryDatasetUploadItem {
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
        url: "/api/libraries/datasets/ldda_1",
        ...overrides,
    };
}

function mountHarness(prepared: PreparedUpload) {
    const Harness = defineComponent({
        setup() {
            const { submitPreparedUpload } = useUploadSubmission();
            const result = ref("");
            const error = ref("");

            async function run() {
                try {
                    const uploaded = await submitPreparedUpload("hist_1", prepared);
                    result.value = JSON.stringify(uploaded);
                } catch (err) {
                    error.value = String(err);
                }
            }

            return { error, result, run };
        },
        template: `
            <div>
                <button data-test-id="run" @click="run">run</button>
                <div data-test-id="result">{{ result }}</div>
                <div data-test-id="error">{{ error }}</div>
            </div>
        `,
    });

    return mount(Harness, { localVue, pinia: createPinia() });
}

function makeCollectionConfig(overrides: Partial<UploadCollectionConfig> = {}): UploadCollectionConfig {
    return {
        name: "Uploaded Collection",
        type: "list",
        hideSourceItems: true,
        historyId: "hist_1",
        ...overrides,
    };
}

describe("useUploadSubmission", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        useUploadState().clearAll();

        server.use(http.get("/api/configuration", () => HttpResponse.json({ chunk_upload_size: 42 })));
    });

    afterEach(() => {
        useUploadState().clearAll();
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

        const apiItem = makeUrlItem();
        const apiPrepared = buildPreparedUpload([apiItem]);
        const wrapper = mountHarness({
            apiItems: apiPrepared.apiItems,
            uploadItems: [apiItem, makeLibraryItem()],
        });
        await flushPromises();

        await wrapper.find(SELECTORS.RUN).trigger("click");
        await flushPromises();

        expect(wrapper.find(SELECTORS.RESULT).text()).toContain('"id":"hda_1"');
        expect(wrapper.find(SELECTORS.RESULT).text()).toContain('"id":"hdca_1"');
        expect(wrapper.find(SELECTORS.RESULT).text()).toContain('"id":"hda_2"');

        const state = useUploadState();
        const pastedEntry = state.activeItems.value.find((item) => item.name === "remote.txt");
        const libraryEntry = state.activeItems.value.find((item) => item.name === "library.txt");

        expect(pastedEntry?.status).toBe("completed");
        expect(pastedEntry?.progress).toBe(100);
        expect(libraryEntry?.status).toBe("completed");
        expect(libraryEntry?.progress).toBe(100);
    });

    it("marks all tracked uploads as errored when the fetch request fails", async () => {
        server.use(
            http.post("/api/tools/fetch", () => HttpResponse.json({ err_msg: "upload failed" }, { status: 500 })),
        );

        const apiItem = makeUrlItem({ url: "https://example.org/broken.txt" });
        const apiPrepared = buildPreparedUpload([apiItem]);
        const wrapper = mountHarness({
            apiItems: apiPrepared.apiItems,
            uploadItems: [apiItem, makeLibraryItem()],
        });
        await flushPromises();

        await wrapper.find(SELECTORS.RUN).trigger("click");
        await flushPromises();

        expect(wrapper.find(SELECTORS.ERROR).text()).toContain("upload failed");

        const state = useUploadState();
        expect(state.activeItems.value).toHaveLength(2);
        for (const item of state.activeItems.value) {
            expect(item.status).toBe("error");
            expect(item.error).toBe("upload failed");
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

        const wrapper = mountHarness({
            apiItems: [],
            uploadItems: [makeLibraryItem({ name: "fallback-name.txt", lddaId: "ldda_3" })],
        });
        await flushPromises();

        await wrapper.find(SELECTORS.RUN).trigger("click");
        await flushPromises();

        expect(wrapper.find(SELECTORS.RESULT).text()).toContain('"name":"fallback-name.txt"');
        expect(wrapper.find(SELECTORS.RESULT).text()).toContain('"id":"hda_3"');
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
                    outputs: [{ id: "hdca_2", name: "Uploaded Collection", src: "hdca" }],
                });
            }),
        );

        const firstItem = makeUrlItem({ name: "1.bed", url: "https://example.org/1.bed" });
        const secondItem = makeUrlItem({ name: "2.bed", url: "https://example.org/2.bed" });
        const prepared = buildPreparedUpload([firstItem, secondItem], makeCollectionConfig());
        const wrapper = mountHarness(prepared);
        await flushPromises();

        await wrapper.find(SELECTORS.RUN).trigger("click");
        await flushPromises();

        expect(wrapper.find(SELECTORS.RESULT).text()).toContain('"id":"hdca_2"');

        const state = useUploadState();
        const batch = state.activeBatches.value[0];

        expect(batch?.name).toBe("Uploaded Collection");
        expect(batch?.status).toBe("completed");
        expect(batch?.collectionId).toBe("hdca_2");
        expect(batch?.uploadIds).toHaveLength(2);
        expect(state.standaloneUploads.value).toHaveLength(0);
        expect(state.orderedUploadItems.value[0]?.type).toBe("batch");
        expect(state.activeItems.value.every((item) => item.batchId === batch?.id)).toBe(true);
    });
});
