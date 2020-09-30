import Vuex from "vuex";
import { mount, createLocalVue } from "@vue/test-utils";
import { createStore } from "../../store";
import DatasetInformation from "./DatasetInformation";
import datasetResponse from "./testData/datasetResponse";
import flushPromises from "flush-promises";

const HDA_ID = "06ec17aefa2d49dd";

describe("JobDestinationParams/JobDestinationParams.vue", () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);

    let testStore;
    let wrapper;
    let datasetInfoTable;

    beforeEach(async () => {
        testStore = createStore();
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
        datasetInfoTable = wrapper.find("#dataset_information");
        await flushPromises();
    });

    it("dataset information should exist", async () => {
        // table should exist
        expect(datasetInfoTable).toBeTruthy();
        const rows = datasetInfoTable.findAll("tbody > tr");
        // should contain 6 rows
        expect(rows.length).toBe(6);
    });

    it("should be formatted", async () => {
        // filesize should be formatted
        const filesize = datasetInfoTable.find("#filesize > strong");
        expect(filesize.html()).toBe("<strong>93</strong>");

        // Date should be formatted
        const date = datasetInfoTable.find(".utc-time").text();
        expect(date).toBe("Monday Sep 28th 3:54:04 2020 UTC");
    });
});
