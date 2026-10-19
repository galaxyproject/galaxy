import "tests/jest/mockHelpPopovers";
import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { PiniaVuePlugin } from "pinia";
import { dispatchEvent, getLocalVue } from "tests/jest/helpers";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { useEventStore } from "@/stores/eventStore";

import MountTarget from "./FormData.vue";

jest.mock("@/composables/filter");

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

let eventStore;

function createTarget(propsData) {
    const pinia = createTestingPinia({ stubActions: false });
    eventStore = useEventStore();
    const datatypesStore = useDatatypesMapperStore();
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return mount(MountTarget, {
        localVue,
        propsData,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

const defaultOptions = {
    dce: [
        { id: "dce1", name: "dceName1", src: "dce", is_dataset: true },
        { id: "dce2", name: "dceName2", src: "dce" },
        { id: "dce3", name: "dceName3", src: "dce", map_over_type: "mapOverType" },
        { id: "dce4", name: "dceName4", src: "dce", is_dataset: true },
    ],
    hda: [
        { id: "hda1", hid: 1, name: "hdaName1", src: "hda", tags: ["tag1"] },
        { id: "hda2", hid: 2, name: "hdaName2", src: "hda", tags: ["tag1", "tag2"] },
        { id: "hda3", hid: 3, name: "hdaName3", src: "hda", tags: ["tag2", "tag3"] },
        { id: "hda4", hid: 4, name: "hdaName4", src: "hda" },
    ],
    hdca: [
        { id: "hdca5", hid: 5, name: "hdcaName5", src: "hdca" },
        { id: "hdca6", hid: 6, name: "hdcaName6", src: "hdca" },
    ],
};

const SELECT_OPTIONS = ".multiselect__element";
const SELECTED_VALUE = ".multiselect__option--selected";

describe("FormData", () => {
    it("regular data", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
        });
        const value_0 = {
            batch: false,
            product: false,
            values: [{ id: "dce4", src: "dce", map_over_type: null }],
        };
        const value_1 = {
            batch: false,
            product: false,
            values: [{ id: "hda1", src: "hda", map_over_type: null }],
        };
        const value_2 = {
            batch: false,
            product: false,
            values: [{ id: "hda4", src: "hda", map_over_type: null }],
        };
        const options = wrapper.find(".btn-group").findAll("button");
        expect(options.length).toBe(4);
        expect(options.at(0).classes()).toContain("active");
        expect(options.at(0).attributes("title")).toBe("Single dataset");
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("dceName4 (as dataset)");
        await wrapper.setProps({ value: value_0 });
        expect(wrapper.emitted().input.length).toEqual(1);
        await wrapper.setProps({ value: { values: [{ id: "hda2", src: "hda" }] } });
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("2: hdaName2");
        expect(wrapper.emitted().input.length).toEqual(1);
        const elements_0 = wrapper.findAll(SELECT_OPTIONS);
        expect(elements_0.length).toEqual(6);
        await elements_0.at(2).find("span").trigger("click");
        expect(wrapper.emitted().input.length).toEqual(2);
        expect(wrapper.emitted().input[1][0]).toEqual(value_1);
        await wrapper.setProps({ value: value_2 });
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("4: hdaName4");
    });

    it("optional dataset", async () => {
        const wrapper = createTarget({
            value: null,
            optional: true,
            options: defaultOptions,
        });
        expect(wrapper.emitted().input[0][0]).toEqual(null);
        expect(wrapper.emitted().input.length).toEqual(1);
        expect(wrapper.find(SELECTED_VALUE).text()).toEqual("Nothing selected");
        expect(wrapper.findAll(SELECT_OPTIONS).length).toBe(7);
    });

    it("multiple datasets", async () => {
        const wrapper = createTarget({
            value: {
                values: [
                    { id: "hda2", src: "hda" },
                    { id: "hda3", src: "hda" },
                ],
            },
            multiple: true,
            optional: true,
            options: defaultOptions,
        });
        const options = wrapper.find(".btn-group").findAll("button");
        expect(options.length).toBe(3);
        expect(options.at(0).classes()).toContain("active");
        expect(options.at(0).attributes("title")).toBe("Multiple datasets");
        expect(wrapper.emitted().input[0][0]).toEqual({
            batch: false,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        });
        expect(wrapper.emitted().input.length).toEqual(1);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(2);
        expect(selectedValues.at(0).text()).toContain("2: hdaName2");
        expect(selectedValues.at(1).text()).toContain("3: hdaName3");
        const value_0 = {
            batch: false,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        await selectedValues.at(0).trigger("click");
        const value_1 = {
            batch: false,
            product: false,
            values: [{ id: "hda3", map_over_type: null, src: "hda" }],
        };
        expect(wrapper.emitted().input[1][0]).toEqual(value_1);
        await wrapper.setProps({ value: value_1 });
        await selectedValues.at(1).trigger("click");
        const value_2 = {
            batch: false,
            product: false,
            values: [{ id: "hda3", map_over_type: null, src: "hda" }],
        };
        expect(wrapper.emitted().input[1][0]).toEqual(value_2);
        await wrapper.setProps({ value: value_2 });
        expect(wrapper.emitted().input.length).toBe(3);
        expect(wrapper.emitted().input[2][0]).toEqual(null);
    });

    it("properly sorts multiple datasets", async () => {
        const wrapper = createTarget({
            value: {
                // the order of values does matter here
                values: [
                    { id: "hda2", src: "hda" },
                    { id: "hda3", src: "hda" },
                    { id: "hda1", src: "hda" },
                ],
            },
            multiple: true,
            optional: true,
            options: defaultOptions,
        });
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(3);
        // the values in the multiselect are sorted by hid ASC
        expect(selectedValues.at(0).text()).toContain("1: hdaName1");
        expect(selectedValues.at(1).text()).toContain("2: hdaName2");
        expect(selectedValues.at(2).text()).toContain("3: hdaName3");
        await selectedValues.at(0).trigger("click");
        const value_sorted = {
            batch: false,
            product: false,
            values: [
                // the values in the emitted input are sorted by hid ASC
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        };
        expect(wrapper.emitted().input[1][0]).toEqual(value_sorted);
    });

    it("sorts mixed dces and hdas", async () => {
        const sortOptions = {
            hda: [
                { id: "hda1", hid: 1, name: "hdaName1", src: "hda", tags: ["tag1"] },
                { id: "hda2", hid: 2, name: "hdaName2", src: "hda", tags: ["tag1", "tag2"] },
                { id: "hda3", hid: 3, name: "hdaName3", src: "hda", tags: ["tag2", "tag3"] },
                { id: "hda4", hid: 4, name: "hdaName4", src: "hda" },
            ],
            dce: [
                { id: "dce1", name: "dceName1", src: "dce", is_dataset: true },
                { id: "dce2", name: "dceName2", src: "dce", is_dataset: true },
                { id: "dce3", name: "dceName3", src: "dce", is_dataset: true },
                { id: "dce4", name: "dceName4", src: "dce", is_dataset: true },
            ],
        };
        const wrapper = createTarget({
            //intermix hdas and dces in the selected options
            value: {
                values: [
                    { id: "hda1", src: "hda" },
                    { id: "dce4", src: "dce" },
                    { id: "dce2", src: "dce" },
                    { id: "hda2", src: "hda" },
                    { id: "dce3", src: "dce" },
                ],
            },
            multiple: true,
            optional: true,
            options: sortOptions,
        });
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(5);
        expect(selectedValues.at(0).text()).toContain("dceName4 (as dataset)");
        expect(selectedValues.at(1).text()).toContain("dceName3 (as dataset)");
        expect(selectedValues.at(2).text()).toContain("dceName2 (as dataset)");
        expect(selectedValues.at(3).text()).toContain("1: hdaName1");
        expect(selectedValues.at(4).text()).toContain("2: hdaName2");
        await selectedValues.at(0).trigger("click");
        const value_sorted = {
            batch: false,
            product: false,
            values: [
                { id: "hda1", map_over_type: null, src: "hda" },
                { id: "dce2", map_over_type: null, src: "dce" },
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "dce3", map_over_type: null, src: "dce" },
            ],
        };
        expect(wrapper.emitted().input[1][0]).toEqual(value_sorted);
    });

    it("dataset collection as hda", async () => {
        const wrapper = createTarget({
            value: { values: [{ id: "dce1", src: "dce" }] },
            options: defaultOptions,
        });
        const value_0 = {
            batch: false,
            product: false,
            values: [{ id: "dce1", map_over_type: null, src: "dce" }],
        };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        expect(wrapper.emitted().input.length).toEqual(1);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(selectedValues.at(0).text()).toContain("dceName1 (as dataset)");
    });

    it("dataset collection element as hdca without map_over_type", async () => {
        const wrapper = createTarget({
            value: { values: [{ id: "dce2", src: "dce" }] },
            options: defaultOptions,
        });
        const value_0 = { batch: true, product: false, values: [{ id: "dce2", map_over_type: null, src: "dce" }] };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        await wrapper.vm.$nextTick();
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(selectedValues.at(0).text()).toContain("dceName2 (as dataset collection)");
    });

    it("dataset collection element as hdca mapped to batch field", async () => {
        const wrapper = createTarget({
            value: { values: [{ id: "dce3", src: "dce" }] },
            options: defaultOptions,
        });
        const value_0 = {
            batch: true,
            product: false,
            values: [{ id: "dce3", map_over_type: "mapOverType", src: "dce" }],
        };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        await wrapper.vm.$nextTick();
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(selectedValues.at(0).text()).toContain("dceName3 (as dataset collection)");
    });

    it("dataset collection element as hdca mapped to non-batch field", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            value: { values: [{ id: "dce3", src: "dce" }] },
            options: defaultOptions,
        });
        const value_0 = {
            batch: true,
            product: false,
            values: [{ id: "dce3", map_over_type: "mapOverType", src: "dce" }],
        };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        await wrapper.vm.$nextTick();
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(selectedValues.at(0).text()).toContain("dceName3 (as dataset collection)");
    });

    it("dataset collection mapped to non-batch field", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            value: { values: [{ id: "hdca5", src: "hdca" }] },
            options: defaultOptions,
        });
        const value_0 = {
            batch: false,
            product: false,
            values: [{ id: "hdca5", map_over_type: null, src: "hdca" }],
        };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
        await wrapper.vm.$nextTick();
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(selectedValues.at(0).text()).toContain("5: hdcaName5");
    });

    it("multiple dataset collection elements (as hdas)", async () => {
        const wrapper = createTarget({
            value: {
                values: [
                    { id: "dce1", src: "dce" },
                    { id: "dce4", src: "dce" },
                ],
            },
            options: defaultOptions,
        });
        const value_0 = {
            batch: true,
            product: false,
            values: [
                { id: "dce1", map_over_type: null, src: "dce" },
                { id: "dce4", map_over_type: null, src: "dce" },
            ],
        };
        expect(wrapper.emitted().input[0][0]).toEqual(value_0);
    });

    it("dropping values", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
        });
        eventStore.setDragData({ id: "hdca4", history_content_type: "dataset_collection" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(wrapper.emitted().input[1][0]).toEqual({
            batch: true,
            product: false,
            values: [{ id: "hdca4", map_over_type: null, src: "hdca" }],
        });
        eventStore.setDragData({ id: "hda2", history_content_type: "dataset" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(wrapper.emitted().input[2][0]).toEqual({
            batch: false,
            product: false,
            values: [{ id: "hda2", map_over_type: null, src: "hda" }],
        });
    });

    it("rejects hda on collection input", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
            type: "data_collection",
        });
        eventStore.setDragData({ id: "whatever", history_content_type: "dataset" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(wrapper.emitted().alert[0][0]).toEqual("dataset is not a valid input for dataset collection parameter.");
    });

    it("rejects paired collection on list collection input", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
            type: "data_collection",
            collectionTypes: ["list"],
        });
        eventStore.setDragData({
            id: "whatever",
            history_content_type: "dataset_collection",
            collection_type: "paired",
        });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(wrapper.emitted().alert[0][0]).toEqual(
            "dataset pair dataset collection is not a valid input for list type dataset collection parameter.",
        );
    });

    it("accepts list:list collection on list collection input", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
            type: "data_collection",
            collectionTypes: ["list"],
        });
        eventStore.setDragData({
            id: "whatever",
            history_content_type: "dataset_collection",
            collection_type: "list:list",
        });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(wrapper.emitted().alert).toBeUndefined();
    });

    it("linked and unlinked batch mode handling", async () => {
        const wrapper = createTarget({
            value: null,
            flavor: "module",
            options: defaultOptions,
        });
        expect(wrapper.emitted().input[0][0]).toEqual({
            batch: false,
            product: false,
            values: [{ id: "dce4", map_over_type: null, src: "dce" }],
        });
        const noCheckLinked = wrapper.find("input[type='checkbox']");
        expect(noCheckLinked.exists()).toBeFalsy();
        await wrapper.find("[title='Multiple datasets'").trigger("click");
        expect(wrapper.emitted().input[1][0]).toEqual(null);
        const elements_0 = wrapper.findAll(SELECT_OPTIONS);
        expect(elements_0.length).toEqual(6);
        await elements_0.at(3).find("span").trigger("click");
        const value_0 = {
            batch: true,
            product: false,
            values: [{ id: "hda2", map_over_type: null, src: "hda" }],
        };
        expect(wrapper.emitted().input[2][0]).toEqual(value_0);
        await wrapper.setProps({ value: value_0 });
        await elements_0.at(0).find("span").trigger("click");
        const value_1 = {
            batch: true,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "dce4", map_over_type: null, src: "dce" },
            ],
        };
        expect(wrapper.emitted().input[3][0]).toEqual(value_1);
        await wrapper.setProps({ value: value_1 });
        const checkLinked = wrapper.find("input[type='checkbox']");
        expect(wrapper.find(".custom-switch span").text()).toBe(
            "Linked: Datasets will be run in matched order with other datasets.",
        );
        expect(checkLinked.element.checked).toBeTruthy();
        await checkLinked.setChecked(false);
        expect(wrapper.find(".custom-switch span").text()).toBe(
            "Unlinked: Dataset will be run against *all* other datasets.",
        );
        expect(wrapper.emitted().input[4][0]).toEqual({
            batch: true,
            product: true,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "dce4", map_over_type: null, src: "dce" },
            ],
        });
    });

    it("match dataset collection on initial value", async () => {
        const wrapper = createTarget({
            value: {
                values: [{ id: "hdca5", src: "hdca" }],
            },
            multiple: true,
            options: defaultOptions,
        });
        await wrapper.vm.$nextTick();
        const options = wrapper.find(".btn-group").findAll("button");
        expect(options.length).toBe(3);
        expect(options.at(1).classes()).toContain("active");
        expect(options.at(1).attributes("title")).toBe("Dataset collection");
        for (const i of [0, 1]) {
            expect(wrapper.emitted().input[i][0]).toEqual({
                batch: false,
                product: false,
                values: [{ id: "hdca5", map_over_type: null, src: "hdca" }],
            });
        }
        expect(wrapper.emitted().input.length).toEqual(2);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(selectedValues.at(0).text()).toBe("5: hdcaName5");
        await wrapper.find("[title='Multiple datasets'").trigger("click");
        expect(options.at(0).classes()).toContain("active");
        expect(wrapper.emitted().input[2][0]).toEqual(null);
    });

    it("tagging filter", async () => {
        const wrapper_0 = createTarget({
            tag: "tag1",
            options: defaultOptions,
        });
        const select_0 = wrapper_0.findAll(SELECT_OPTIONS);
        expect(select_0.length).toBe(4);
        expect(select_0.at(2).text()).toContain("1: hdaName1");
        expect(select_0.at(3).text()).toContain("2: hdaName2");
        const wrapper_1 = createTarget({
            tag: "tag2",
            options: defaultOptions,
        });
        const select_1 = wrapper_1.findAll(SELECT_OPTIONS);
        expect(select_1.length).toBe(4);
        expect(select_1.at(2).text()).toContain("2: hdaName2");
        expect(select_1.at(3).text()).toContain("3: hdaName3");
        const wrapper_2 = createTarget({
            tag: "tag3",
            options: defaultOptions,
        });
        const select_2 = wrapper_2.findAll(SELECT_OPTIONS);
        expect(select_2.length).toBe(3);
        expect(select_2.at(2).text()).toContain("3: hdaName3");
    });
});

describe("FormData batch hint", () => {
    const BATCH_INFO = ".info.text-info";
    const MAPPED_OVER = /^The supplied input will be .*mapped over this tool\.$/;
    const MAPPED_OVER_PER_DATASET = /^The supplied input will be .*mapped over this tool: one job per dataset\.$/;
    const MAPPED_OVER_PER_PAIR = /^The supplied input will be .*mapped over this tool: one job per dataset pair\.$/;

    function batchInfoText(wrapper) {
        const info = wrapper.find(BATCH_INFO);
        expect(info.exists()).toBe(true);
        return info.text().replace(/\s+/g, " ");
    }

    it("shows mapped over info for a collection selected on a data input", async () => {
        const wrapper = createTarget({
            value: { values: [{ id: "hdca5", src: "hdca" }] },
            options: defaultOptions,
        });
        await wrapper.vm.$nextTick();
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_DATASET);
    });

    it("shows no batch info for a single dataset on a data input", async () => {
        const wrapper = createTarget({
            value: { values: [{ id: "hda1", src: "hda" }] },
            options: defaultOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    it("shows batch mode info for multiple datasets on a data input", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
        });
        await wrapper.find("[title='Multiple datasets']").trigger("click");
        expect(wrapper.find(BATCH_INFO).text()).toBe(
            "This is a batch mode input field. Individual jobs will be triggered for each dataset.",
        );
    });

    it("shows no batch info for a collection directly selected on a collection input", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            value: { values: [{ id: "hdca5", src: "hdca" }] },
            options: defaultOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    const pairedOptions = {
        hdca: [
            {
                id: "hdca7",
                hid: 7,
                name: "listPaired",
                src: "hdca",
                collection_type: "list:paired",
                map_over_type: "paired",
            },
            { id: "hdca8", hid: 8, name: "pair", src: "hdca", collection_type: "paired" },
        ],
    };

    it("shows no batch info for multiple directly selected collections", async () => {
        const wrapper = createTarget({
            multiple: true,
            value: { values: [{ id: "hdca8", src: "hdca" }] },
            options: pairedOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".btn-group .active").attributes("title")).toBe("Dataset collection");
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    it("shows mapped over info for a nested collection mapped over a collection input", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            collectionTypes: ["paired"],
            value: { values: [{ id: "hdca7", src: "hdca" }] },
            options: pairedOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted().input[0][0].batch).toBe(true);
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_PAIR);
        expect(wrapper.find("input[type='checkbox']").exists()).toBeFalsy();
    });

    it("shows no mapped over info for a nested collection in a workflow run form", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            flavor: "module",
            collectionTypes: ["paired"],
            value: { values: [{ id: "hdca7", src: "hdca" }] },
            options: pairedOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted().input[0][0].batch).toBe(true);
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    it("toggles mapped over info when switching collection input selection", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            collectionTypes: ["paired"],
            value: { values: [{ id: "hdca8", src: "hdca" }] },
            options: pairedOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
        await wrapper.setProps({ value: { values: [{ id: "hdca7", src: "hdca" }] } });
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_PAIR);
        await wrapper.setProps({ value: { values: [{ id: "hdca8", src: "hdca" }] } });
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    it("shows mapped over info for a dropped nested collection on a collection input", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            collectionTypes: ["paired"],
            value: null,
            optional: true,
            options: pairedOptions,
        });
        eventStore.setDragData({
            id: "hdca9",
            hid: 9,
            name: "droppedListPaired",
            history_content_type: "dataset_collection",
            collection_type: "list:paired",
        });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        const emitted = wrapper.emitted().input.at(-1)[0];
        expect(emitted).toEqual({
            batch: true,
            product: false,
            values: [{ id: "hdca9", map_over_type: "paired", src: "hdca" }],
        });
        await wrapper.setProps({ value: emitted });
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_PAIR);
    });

    it("shows mapped over info when any of multiple selected collections maps over", async () => {
        const wrapper = createTarget({
            multiple: true,
            value: {
                values: [
                    { id: "hdca8", src: "hdca" },
                    { id: "hdca7", src: "hdca" },
                ],
            },
            options: pairedOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".btn-group .active").attributes("title")).toBe("Dataset collection");
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER);
    });

    it("names dataset as the job unit for a collection mapped over as single datasets", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            collectionTypes: ["paired_or_unpaired"],
            value: { values: [{ id: "hdca10", src: "hdca" }] },
            options: {
                hdca: [
                    {
                        id: "hdca10",
                        hid: 10,
                        name: "list",
                        src: "hdca",
                        collection_type: "list",
                        map_over_type: "single_datasets",
                    },
                ],
            },
        });
        await wrapper.vm.$nextTick();
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_DATASET);
    });

    it("names the raw type as the job unit for a collection type without a label", async () => {
        const wrapper = createTarget({
            type: "data_collection",
            collectionTypes: ["paired_or_unpaired"],
            value: { values: [{ id: "hdca12", src: "hdca" }] },
            options: {
                hdca: [
                    {
                        id: "hdca12",
                        hid: 12,
                        name: "mixedList",
                        src: "hdca",
                        collection_type: "list:paired_or_unpaired",
                        map_over_type: "paired_or_unpaired",
                    },
                ],
            },
        });
        await wrapper.vm.$nextTick();
        expect(batchInfoText(wrapper)).toMatch(
            /^The supplied input will be .*mapped over this tool: one job per paired_or_unpaired collection\.$/,
        );
        expect(wrapper.find(`${BATCH_INFO} code`).text()).toBe("paired_or_unpaired");
    });

    it("names no job unit when several selected collections map over", async () => {
        const wrapper = createTarget({
            multiple: true,
            value: {
                values: [
                    { id: "hdca7", src: "hdca" },
                    { id: "hdca11", src: "hdca" },
                ],
            },
            options: {
                hdca: [
                    ...pairedOptions.hdca,
                    {
                        id: "hdca11",
                        hid: 11,
                        name: "listPaired2",
                        src: "hdca",
                        collection_type: "list:paired",
                        map_over_type: "paired",
                    },
                ],
            },
        });
        await wrapper.vm.$nextTick();
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER);
    });
});
