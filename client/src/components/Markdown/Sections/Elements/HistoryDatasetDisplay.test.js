import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import HistoryDatasetDisplay from "./HistoryDatasetDisplay.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

function setUpDatatypesStore() {
    const pinia = createTestingPinia({ stubActions: false });
    const datatypesStore = useDatatypesMapperStore();
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return pinia;
}

describe("History Tabular Dataset Display", () => {
    let wrapper;
    const datasetId = "someId";
    const tabular = { item_data: "29994\t-1.25\n37191\t-1.05\n36810\t2.08\n33320\t1.15" };
    const tabularMetaData = {
        metadata_columns: 2,
        metadata_data_lines: 4,
        extension: "tabular",
        name: "someName",
        state: "ok",
    };
    const tabularTableDataCounts = tabularMetaData.metadata_columns * tabularMetaData.metadata_data_lines;

    async function mountTarget() {
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) => response(200).json(tabularMetaData)),
            http.get("/api/datasets/{dataset_id}/get_content_as_text", ({ response }) => response(200).json(tabular))
        );
        wrapper = mount(HistoryDatasetDisplay, {
            localVue,
            propsData: { datasetId },
            pinia: setUpDatatypesStore(),
        });
        await flushPromises();
    }

    it("should render table", async () => {
        await mountTarget();
        expect(wrapper.find("table").exists()).toBe(true);
        expect(wrapper.findAll("td").length).toBe(tabularTableDataCounts);
        expect(wrapper.findAll("th").length).toBe(tabularMetaData.metadata_columns);
    });
});

describe("History Text Dataset Display", () => {
    let wrapper;
    const datasetId = "otherId";
    const text = { item_data: "some text" };
    const textMetaData = { extension: "txt", name: "someName", state: "ok" };

    async function mountTarget() {
        server.resetHandlers();
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) => response(200).json(textMetaData)),
            http.get("/api/datasets/{dataset_id}/get_content_as_text", ({ response }) => response(200).json(text))
        );
        wrapper = mount(HistoryDatasetDisplay, {
            localVue,
            propsData: { datasetId },
            pinia: setUpDatatypesStore(),
        });
        await flushPromises();
    }

    it("should render text", async () => {
        await mountTarget();
        const renderedText = wrapper.find(".word-wrap-normal");
        expect(renderedText.exists()).toBe(true);
        expect(renderedText.text()).toBe(text.item_data);
    });

    it("should render header with embedded true", async () => {
        await mountTarget();
        expect(wrapper.find(".card-header").exists()).toBe(true);
        await wrapper.setProps({ embedded: true });
        expect(wrapper.find(".card-header").exists()).toBe(false);
    });

    it("should expand dataset", async () => {
        await mountTarget();
        const expandBTN = wrapper.find('.btn[title="Expand"]');
        expect(expandBTN.exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset").exists()).toBe(true);

        await expandBTN.trigger("click");

        expect(wrapper.find('.btn[title="Collapse"]').exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset-expanded").exists()).toBe(true);
    });
});
