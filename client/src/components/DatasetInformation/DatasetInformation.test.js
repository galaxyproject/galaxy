import Vuex from "vuex";
import { mount, createLocalVue } from "@vue/test-utils";
import { datasetsStore } from "store/datasetsStore";
import DatasetInformation from "./DatasetInformation";
import datasetResponse from "./testData/datasetResponse";
import flushPromises from "flush-promises";
import createCache from "vuex-cache";

const HDA_ID = "06ec17aefa2d49dd";

const localVue = createLocalVue();
localVue.use(Vuex);
const testStore = new Vuex.Store({
    plugins: [createCache()],
    modules: {
        datasetsStore,
    },
});

jest.mock("axios", () => ({
    get: async () => {
        return { response: { status: 200 } };
    },
}));

describe("DatasetInformation/DatasetInformation.vue", () => {
    let wrapper;
    let datasetInfoTable;

    beforeEach(async () => {
        const propsData = {
            hda_id: HDA_ID,
        };
        wrapper = mount(DatasetInformation, {
            store: testStore,
            propsData,
            localVue,
            computed: {
                dataset() {
                    return datasetResponse;
                },
            },
        });
        datasetInfoTable = wrapper.find("#dataset-details");
        await flushPromises();
    });

    it("dataset information should exist", async () => {
        // table should exist
        expect(datasetInfoTable).toBeTruthy();
        const rows = datasetInfoTable.findAll("tbody > tr");
        // should contain 6 rows
        expect(rows.length).toBe(6);
    });

    it("filesize should be formatted", async () => {
        const filesize = datasetInfoTable.find("#filesize > strong");
        expect(filesize.html()).toBe(`<strong>${datasetResponse.file_size}</strong>`);
    });

    it("Date should be formatted", async () => {
        const date = datasetInfoTable.find(".utc-time").text();
        expect(date).toBe("Monday Sep 28th 3:54:04 2020 UTC");
    });

    // it("Table should render data accordingly", async () => {
    //     const entries = [{ Number: "hid" }, "name", "file_ext", "metadata_dbkey"];
    // });
});
