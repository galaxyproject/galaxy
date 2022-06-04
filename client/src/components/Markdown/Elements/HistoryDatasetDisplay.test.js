import axios from "axios";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import MockAdapter from "axios-mock-adapter";
import HistoryDatasetDisplay from "./HistoryDatasetDisplay.vue";
import { typesAndMappingResponse } from "components/Datatypes/test_fixtures";

const localVue = getLocalVue();

const args = { history_dataset_id: "someId" };
const api_paths_map = new Map([["/api/datatypes/types_and_mapping", typesAndMappingResponse]]);

describe("History Tabular Dataset Display", () => {
    let wrapper;
    let axiosMock;

    const tabular = { item_data: "29994\t-1.25\n37191\t-1.05\n36810\t2.08\n33320\t1.15" };
    const tabularMetaData = { metadata_columns: 2, metadata_data_lines: 4 };
    const tabularDatasets = { [args.history_dataset_id]: { ext: "tabular", name: "someName" } };

    const tabularTableDataCounts = tabularMetaData.metadata_columns * tabularMetaData.metadata_data_lines;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);

        for (const [path, response] of api_paths_map.entries()) {
            axiosMock.onGet(path).reply(200, response);
        }

        axiosMock.onGet(`/api/datasets/${args.history_dataset_id}`).reply(200, tabularMetaData);
        axiosMock.onGet(`/api/datasets/${args.history_dataset_id}/get_content_as_text`).reply(200, tabular);

        wrapper = mount(HistoryDatasetDisplay, { localVue, propsData: { datasets: tabularDatasets, args } });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should render table", () => {
        expect(wrapper.find("table").exists()).toBe(true);
        expect(wrapper.findAll("td").length).toBe(tabularTableDataCounts);
        expect(wrapper.findAll("th").length).toBe(tabularMetaData.metadata_columns);
    });
});

describe("History Text Dataset Display", () => {
    let wrapper;
    let axiosMock;

    const text = { item_data: "some text" };
    const textDatasets = { [args.history_dataset_id]: { ext: "txt", name: "someName" } };

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);

        for (const [path, response] of api_paths_map.entries()) {
            axiosMock.onGet(path).reply(200, response);
        }

        axiosMock.onGet(`/api/datasets/${args.history_dataset_id}/get_content_as_text`).reply(200, text);

        wrapper = mount(HistoryDatasetDisplay, { localVue, propsData: { datasets: textDatasets, args } });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should render text", () => {
        const renderedText = wrapper.find(".text-normalwrap");
        expect(renderedText.exists()).toBe(true);
        expect(renderedText.text()).toBe(text.item_data);
    });

    it("should render header with embedded true", async () => {
        expect(wrapper.find(".card-header").exists()).toBe(true);
        await wrapper.setProps({ embedded: true });
        expect(wrapper.find(".card-header").exists()).toBe(false);
    });

    it("should expand dataset", async () => {
        const expandBTN = wrapper.find('.btn[title="Expand"]');
        expect(expandBTN.exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset").exists()).toBe(true);

        await expandBTN.trigger("click");

        expect(wrapper.find('.btn[title="Collapse"]').exists()).toBe(true);
        expect(wrapper.find(".embedded-dataset-expanded").exists()).toBe(true);
    });
});
