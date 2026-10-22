import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDADetailed } from "@/api";
import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useDatasetStore } from "@/stores/datasetStore";

import DatasetDisplay from "./DatasetDisplay.vue";

vi.mock("@/components/Dataset/Tabular/TabularChunkedView.vue", () => ({
    default: {
        name: "TabularChunkedView",
        props: ["options"],
        render: (h: (tag: string, data: object) => unknown) => h("div", { class: "tabular-chunked-view" }),
    },
}));

const DATASET_ID = "dataset_id";
const PREVIEW_BLOB_URL = "blob:http://localhost/test-preview";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const okDataset = {
    id: DATASET_ID,
    name: "Test Dataset",
    state: "ok",
    deleted: false,
    file_ext: "txt",
    file_size: 100,
    peek: "Needs a peek",
    update_time: "2026-01-01T00:00:00",
} as unknown as HDADetailed;

function usePreviewHeaders(headers: Record<string, string> = {}) {
    server.use(
        mswHttp.get("http://localhost/datasets/:dataset_id/display/", () => {
            return HttpResponse.text("preview data", { headers: { "content-type": "text/plain", ...headers } });
        }),
    );
}

async function mountDatasetDisplay(dataset: HDADetailed = okDataset) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: { datasetStore: { storedDatasets: { [DATASET_ID]: dataset } } },
    });
    setActivePinia(pinia);

    const wrapper = mount(DatasetDisplay as object, {
        propsData: { datasetId: DATASET_ID, isBinary: false },
        localVue,
        pinia,
        stubs: { FontAwesomeIcon: true },
    });
    await flushPromises();
    return wrapper;
}

describe("DatasetDisplay", () => {
    beforeEach(() => {
        global.URL.createObjectURL = vi.fn(() => PREVIEW_BLOB_URL);
        global.URL.revokeObjectURL = vi.fn();
        server.use(http.get("/api/datatypes/{datatype}", ({ response }) => response(200).json({} as never)));
    });

    it("shows the dataset preview in a frame", async () => {
        usePreviewHeaders();
        const wrapper = await mountDatasetDisplay();
        expect(wrapper.find(".dataset-display").exists()).toBe(true);
        expect(wrapper.find("iframe").attributes("src")).toBe(PREVIEW_BLOB_URL);
        expect(wrapper.find(".tabular-chunked-view").exists()).toBe(false);
    });

    it("shows chunked datasets in the tabular view", async () => {
        usePreviewHeaders({ "x-content-chunked": "true" });
        const wrapper = await mountDatasetDisplay();
        expect(wrapper.find(".tabular-chunked-view").exists()).toBe(true);
        expect(wrapper.find("iframe").exists()).toBe(false);
    });

    it("warns when the preview is truncated", async () => {
        usePreviewHeaders({ "x-content-truncated": "1024" });
        const wrapper = await mountDatasetDisplay();
        expect(wrapper.find(".warningmessagelarge").text()).toContain("only the first");
    });

    it("waits for pending datasets", async () => {
        usePreviewHeaders();
        const wrapper = await mountDatasetDisplay({ ...okDataset, state: "running" });
        expect(wrapper.text()).toContain("Waiting for dataset to become available.");
        expect(wrapper.find(".dataset-display").exists()).toBe(false);
    });

    it("reports unavailable datasets", async () => {
        usePreviewHeaders();
        const wrapper = await mountDatasetDisplay({ ...okDataset, state: "error" });
        expect(wrapper.text()).toContain("Dataset is unavailable.");
        expect(wrapper.find(".dataset-display").exists()).toBe(false);
    });

    it("shows a loading message until the dataset is stored", async () => {
        usePreviewHeaders();
        let releaseFetch: () => void = () => {};
        const fetchReleased = new Promise<void>((resolve) => {
            releaseFetch = resolve;
        });
        server.use(
            http.untyped.get("/api/datasets/:dataset_id", async () => {
                await fetchReleased;
                return HttpResponse.json(okDataset);
            }),
        );
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
        const wrapper = mount(DatasetDisplay as object, {
            propsData: { datasetId: DATASET_ID, isBinary: false },
            localVue,
            pinia,
        });
        await flushPromises();
        expect(wrapper.text()).toContain("Loading dataset content");

        releaseFetch();
        await flushPromises();
        expect(wrapper.find(".dataset-display").exists()).toBe(true);
        expect(useDatasetStore().getDataset(DATASET_ID)?.name).toBe("Test Dataset");
    });
});
