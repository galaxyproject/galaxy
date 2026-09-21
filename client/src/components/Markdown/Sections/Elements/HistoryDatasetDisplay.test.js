import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

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

vi.mock("@/composables/toast", () => ({
    Toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const mockHistoryStore = reactive({
    currentHistoryId: "current_history_id",
    loadCurrentHistory: vi.fn(),
});

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: vi.fn(() => mockHistoryStore),
}));

const localVue = getLocalVue();

const { server, http } = useServerMock();

function setUpDatatypesStore() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const datatypesStore = useDatatypesMapperStore();
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return pinia;
}

describe("HistoryDatasetDisplay", () => {
    let wrapper;

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
        server.resetHandlers();
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) => response(200).json(metaData)),
            http.get("/api/datasets/{dataset_id}/get_content_as_text", ({ response }) => response(200).json(content)),
        );
        wrapper = mount(HistoryDatasetDisplay, {
            localVue,
            propsData: { datasetId, ...propsData },
            pinia: setUpDatatypesStore(),
        });
        await flushPromises();
    }

    beforeEach(() => {
        vi.mocked(copyDataset).mockReset();
        vi.mocked(Toast.success).mockReset();
        vi.mocked(Toast.error).mockReset();
        mockHistoryStore.currentHistoryId = "current_history_id";
    });

    it("should render table", async () => {
        await mountTarget(tabularDatasetId, tabularMetaData, tabular);
        expect(wrapper.find("table").exists()).toBe(true);
        expect(wrapper.findAll("td").length).toBe(tabularTableDataCounts);
        expect(wrapper.findAll("th").length).toBe(tabularMetaData.metadata_columns);
    });

    it("should render text", async () => {
        await mountTarget(textDatasetId, textMetaData, text);
        const renderedText = wrapper.find(".word-wrap-normal");
        expect(renderedText.exists()).toBe(true);
        expect(renderedText.text()).toBe(text.item_data);
    });

    it("should render header with embedded true", async () => {
        await mountTarget(textDatasetId, textMetaData, text);
        expect(wrapper.find(".card-header").exists()).toBe(true);
        await wrapper.setProps({ embedded: true });
        expect(wrapper.find(".card-header").exists()).toBe(false);
    });

    it("should expand dataset", async () => {
        await mountTarget(textDatasetId, textMetaData, text);
        const expandBTN = wrapper.find(SELECTORS.EXPAND_BUTTON);
        expect(expandBTN.exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset").exists()).toBe(true);

        await expandBTN.trigger("click");

        expect(wrapper.find(SELECTORS.COLLAPSE_BUTTON).exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset-expanded").exists()).toBe(true);
    });

    it("copies the dataset into the current history and shows a success toast", async () => {
        vi.mocked(copyDataset).mockResolvedValueOnce({});
        await mountTarget(textDatasetId, textMetaData, text);

        const importBtn = wrapper.find(SELECTORS.IMPORT_BUTTON);
        expect(importBtn.exists()).toBe(true);

        await importBtn.trigger("click");
        await flushPromises();

        expect(copyDataset).toHaveBeenCalledWith(textDatasetId, "current_history_id");
        expect(Toast.success).toHaveBeenCalledWith(`Dataset "${textMetaData.name}" copied to current history.`);
        expect(Toast.error).not.toHaveBeenCalled();
    });

    it("shows an error toast if copying the dataset fails", async () => {
        vi.mocked(copyDataset).mockRejectedValueOnce(new Error("failed"));
        await mountTarget(textDatasetId, textMetaData, text);

        await wrapper.find(SELECTORS.IMPORT_BUTTON).trigger("click");
        await flushPromises();

        expect(Toast.error).toHaveBeenCalledWith("failed", "Failed to import dataset");
        expect(Toast.success).not.toHaveBeenCalled();
    });
});
