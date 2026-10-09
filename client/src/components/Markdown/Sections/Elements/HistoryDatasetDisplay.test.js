import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { reactive, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { copyDataset } from "@/api/datasets";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { Toast } from "@/composables/toast";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import HistoryDatasetDisplay from "./HistoryDatasetDisplay.vue";

const SELECTORS = {
    EXPAND_BUTTON: 'button[data-title="Expand"]',
    COLLAPSE_BUTTON: 'button[data-title="Collapse"]',
    IMPORT_BUTTON: '[data-description="import dataset button"]',
};

vi.mock("@/api/datasets", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        copyDataset: vi.fn(),
    };
});

vi.mock("@/composables/toast");

// `currentHistoryId` must be a ref (not a plain string) so that `storeToRefs()` --
// which only wraps ref/reactive/computed properties of the raw store object --
// picks it up the same way it would for a real Pinia store's internal state.
const mockHistoryStore = reactive({
    currentHistoryId: ref("current_history_id"),
    loadCurrentHistory: vi.fn(),
});

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: vi.fn(() => mockHistoryStore),
}));

enableAutoUnmount(afterEach);

const { server, http } = useServerMock();

function setUpDatatypesStore() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const datatypesStore = useDatatypesMapperStore(pinia);
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return pinia;
}

describe("HistoryDatasetDisplay", () => {
    const tabularDatasetId = "someId";
    const tabular = { item_data: "29994\t-1.25\n37191\t-1.05\n36810\t2.08\n33320\t1.15" };
    const tabularMetaData = {
        metadata_columns: 2,
        metadata_data_lines: 4,
        extension: "tabular",
        name: "someName",
        state: "ok",
        peek: "needs a peek",
    };
    const tabularTableDataCounts = tabularMetaData.metadata_columns * tabularMetaData.metadata_data_lines;

    const textDatasetId = "otherId";
    const text = { item_data: "some text" };
    const textMetaData = { extension: "txt", name: "someName", state: "ok", peek: "needs a peek" };

    async function mountTarget(datasetId, metaData, content, propsData = {}) {
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) => response(200).json(metaData)),
            http.get("/api/datasets/{dataset_id}/get_content_as_text", ({ response }) => response(200).json(content)),
        );
        const localVue = getLocalVue();
        const pinia = setUpDatatypesStore();
        const wrapper = mount(HistoryDatasetDisplay, {
            global: withPlugins(localVue, pinia),
            propsData: { datasetId, ...propsData },
        });
        await flushPromises();
        return wrapper;
    }

    beforeEach(() => {
        vi.mocked(copyDataset).mockReset();
        vi.mocked(Toast.success).mockReset();
        vi.mocked(Toast.error).mockReset();
        mockHistoryStore.loadCurrentHistory.mockReset();
        mockHistoryStore.currentHistoryId = "current_history_id";
    });

    it("renders tabular content with all cells and column headers", async () => {
        const wrapper = await mountTarget(tabularDatasetId, tabularMetaData, tabular);
        expect(wrapper.find("table").exists()).toBe(true);
        expect(wrapper.findAll("td").length).toBe(tabularTableDataCounts);
        expect(wrapper.findAll("th").length).toBe(tabularMetaData.metadata_columns);
    });

    it("renders text content", async () => {
        const wrapper = await mountTarget(textDatasetId, textMetaData, text);
        const renderedText = wrapper.find(".word-wrap-normal");
        expect(renderedText.exists()).toBe(true);
        expect(renderedText.text()).toBe(text.item_data);
    });

    it("hides the dataset header when embedded becomes true", async () => {
        const wrapper = await mountTarget(textDatasetId, textMetaData, text);
        expect(wrapper.find(".card-header").exists()).toBe(true);
        await wrapper.setProps({ embedded: true });
        expect(wrapper.find(".card-header").exists()).toBe(false);
    });

    it("expands text content when the expand button is clicked", async () => {
        const wrapper = await mountTarget(textDatasetId, textMetaData, text);
        const expandButton = wrapper.find(SELECTORS.EXPAND_BUTTON);
        expect(expandButton.exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset").exists()).toBe(true);

        await expandButton.trigger("click");

        expect(wrapper.find(SELECTORS.COLLAPSE_BUTTON).exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset-expanded").exists()).toBe(true);
    });

    it("copies the dataset into the current history and shows a success toast", async () => {
        vi.mocked(copyDataset).mockResolvedValueOnce({});
        const wrapper = await mountTarget(textDatasetId, textMetaData, text);

        const importButton = wrapper.find(SELECTORS.IMPORT_BUTTON);
        expect(importButton.exists()).toBe(true);

        await importButton.trigger("click");
        await flushPromises();

        expect(copyDataset).toHaveBeenCalledWith(textDatasetId, "current_history_id");
        expect(Toast.success).toHaveBeenCalledWith(`Dataset "${textMetaData.name}" copied to current history.`);
        expect(Toast.error).not.toHaveBeenCalled();
    });

    it("shows an error toast if copying the dataset fails", async () => {
        vi.mocked(copyDataset).mockRejectedValueOnce(new Error("failed"));
        const wrapper = await mountTarget(textDatasetId, textMetaData, text);

        await wrapper.find(SELECTORS.IMPORT_BUTTON).trigger("click");
        await flushPromises();

        expect(Toast.error).toHaveBeenCalledWith("failed", "Failed to import dataset");
        expect(Toast.success).not.toHaveBeenCalled();
    });
});
