import { mount, type Wrapper } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import type Vue from "vue";

import type { HDCASummary } from "@/api";

import CollectionDescription from "./CollectionDescription.vue";

const localVue = getLocalVue();

const defaultTestHDCA: HDCASummary = {
    id: "test_id",
    name: "Test Collection",
    hid: 1,
    collection_id: "test_collection_id",
    type: "collection",
    collection_type: "list",
    history_content_type: "dataset_collection",
    element_count: null,
    create_time: "2020-01-01T00:00:00",
    update_time: null,
    deleted: false,
    visible: true,
    elements_datatypes: [],
    history_id: "fake_history_id",
    model_class: "HistoryDatasetCollectionAssociation",
    populated_state: "ok",
    tags: [],
    url: "fake/url",
    contents_url: "fake/contents/url",
};

describe("CollectionDescription", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        wrapper = mount(CollectionDescription as object, {
            propsData: {
                hdca: defaultTestHDCA,
            },
            localVue,
        });
    });

    it("should display expected heterogeneous descriptions", async () => {
        const HETEROGENEOUS_DATATYPES = ["txt", "csv", "tabular"];
        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                collection_type: "list",
                element_count: 1,
                elements_datatypes: HETEROGENEOUS_DATATYPES,
            },
        });
        expect(wrapper.text()).toBe("a list with 1 dataset");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 2,
                collection_type: "paired",
            },
        });
        expect(wrapper.text()).toBe("a pair with 2 datasets");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list",
            },
        });
        expect(wrapper.text()).toBe("a list with 10 datasets");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:paired",
            },
        });
        expect(wrapper.text()).toBe("a list with 10 pairs");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:list",
            },
        });
        expect(wrapper.text()).toBe("a list with 10 lists");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "other",
            },
        });
        expect(wrapper.text()).toBe("a collection with 10 dataset collections");
    });

    it("should display expected homogeneous descriptions", async () => {
        const EXPECTED_HOMOGENEOUS_DATATYPE = "tabular";
        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 1,
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 1 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 2,
                collection_type: "paired",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a pair with 2 ${EXPECTED_HOMOGENEOUS_DATATYPE} datasets`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} datasets`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:paired",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} pairs`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:list",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} lists`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "paired:paired",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a nested collection with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset collections`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "other",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a collection with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset collections`);
    });
});
