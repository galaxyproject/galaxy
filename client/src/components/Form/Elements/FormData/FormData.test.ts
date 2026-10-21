import "@tests/vitest/mockHelpPopovers";
import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { dispatchEvent, emittedArg, getLocalVue, nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper, typesAndMappingResponse } from "@/components/Datatypes/test_fixtures";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { useEventStore } from "@/stores/eventStore";

import MountTarget from "./FormData.vue";

vi.mock("@/composables/filter");

const { server, http } = useServerMock();

// FormData resolves its datatypes mapper on mount; stub the request so the tests
// never hit a real fetch that gets aborted at teardown and surfaces as an
// unhandled error that fails the run.
server.use(
    http.get("/api/datatypes/types_and_mapping", ({ response }) => {
        return response(200).json(typesAndMappingResponse);
    }),
);

const localVue = getLocalVue();

let eventStore: ReturnType<typeof useEventStore>;

function createTarget(propsData: Record<string, any>) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    eventStore = useEventStore();
    const datatypesStore = useDatatypesMapperStore();
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return mount(MountTarget as any, {
        global: localVue,
        props: propsData,
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

// vue-multiselect only renders its option list (and thus SELECT_OPTIONS /
// SELECTED_VALUE) while its dropdown is open, so tests need to open it
// before reading those. Selecting a new value in single-select mode closes
// the dropdown again, so callers re-open as needed between assertions.
async function openMultiselect(wrapper: ReturnType<typeof createTarget>) {
    if (!wrapper.find(".multiselect__content-wrapper").exists()) {
        await wrapper.find(".multiselect__select").trigger("mousedown");
    }
}

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
        const options = wrapper.find(".g-button-group").findAll("button");
        expect(options.length).toBe(4);
        expect(nth(options, 0).classes()).toContain("g-pressed");
        expect(nth(options, 0).attributes("title")).toBe("Single dataset");
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("dceName4 (as dataset)");
        await wrapper.setProps({ value: value_0 });
        expect(wrapper.emitted("input")).toHaveLength(1);
        await wrapper.setProps({ value: { values: [{ id: "hda2", src: "hda" }] } });
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("2: hdaName2");
        expect(wrapper.emitted("input")).toHaveLength(1);
        await openMultiselect(wrapper);
        const elements_0 = wrapper.findAll(SELECT_OPTIONS);
        expect(elements_0.length).toEqual(6);
        await nth(elements_0, 2).find("span").trigger("click");
        expect(wrapper.emitted("input")).toHaveLength(2);
        expect(emittedArg(wrapper, "input", 1)).toEqual(value_1);
        await wrapper.setProps({ value: value_2 });
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("4: hdaName4");
    });

    it("optional dataset", async () => {
        const wrapper = createTarget({
            value: null,
            optional: true,
            options: defaultOptions,
        });
        expect(emittedArg(wrapper, "input")).toEqual(null);
        expect(wrapper.emitted("input")).toHaveLength(1);
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toEqual("Nothing selected");
        expect(wrapper.findAll(SELECT_OPTIONS).length).toBe(7);
    });

    it("names the collection type in the no-options alert", () => {
        const wrapper = createTarget({
            type: "data_collection",
            value: null,
            options: {},
            collectionTypes: ["sample_sheet:paired"],
        });
        expect(wrapper.find(".form-data-no-options-alert").text()).toBe(
            "No sample sheet of pairs dataset collections available",
        );
    });

    it("styles the no-options alert to match the control height in both run and tool forms", async () => {
        const wrapper = createTarget({
            type: "data",
            value: null,
            options: {},
            workflowRun: true,
        });
        const alert = wrapper.find(".form-data-no-options-alert");
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toBe("No datasets available");

        // The alert keeps the aligned styling outside of workflow runs too.
        await wrapper.setProps({ workflowRun: false });
        expect(wrapper.find(".form-data-no-options-alert").exists()).toBe(true);
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
        const options = wrapper.find(".g-button-group").findAll("button");
        expect(options.length).toBe(3);
        expect(nth(options, 0).classes()).toContain("g-pressed");
        expect(nth(options, 0).attributes("title")).toBe("Multiple datasets");
        expect(emittedArg(wrapper, "input")).toEqual({
            batch: false,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        });
        expect(wrapper.emitted("input")).toHaveLength(1);
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(2);
        expect(nth(selectedValues, 0).text()).toContain("2: hdaName2");
        expect(nth(selectedValues, 1).text()).toContain("3: hdaName3");
        const value_0 = {
            batch: false,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        };
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
        await nth(selectedValues, 0).trigger("click");
        const value_1 = {
            batch: false,
            product: false,
            values: [{ id: "hda3", map_over_type: null, src: "hda" }],
        };
        expect(emittedArg(wrapper, "input", 1)).toEqual(value_1);
        await wrapper.setProps({ value: value_1 });
        await nth(selectedValues, 1).trigger("click");
        const value_2 = {
            batch: false,
            product: false,
            values: [{ id: "hda3", map_over_type: null, src: "hda" }],
        };
        expect(emittedArg(wrapper, "input", 1)).toEqual(value_2);
        await wrapper.setProps({ value: value_2 });
        expect(wrapper.emitted("input")).toHaveLength(3);
        expect(emittedArg(wrapper, "input", 2)).toEqual(null);
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
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(3);
        // the values in the multiselect are sorted by hid ASC
        expect(nth(selectedValues, 0).text()).toContain("1: hdaName1");
        expect(nth(selectedValues, 1).text()).toContain("2: hdaName2");
        expect(nth(selectedValues, 2).text()).toContain("3: hdaName3");
        await nth(selectedValues, 0).trigger("click");
        const value_sorted = {
            batch: false,
            product: false,
            values: [
                // the values in the emitted input are sorted by hid ASC
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "hda3", map_over_type: null, src: "hda" },
            ],
        };
        expect(emittedArg(wrapper, "input", 1)).toEqual(value_sorted);
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
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(5);
        expect(nth(selectedValues, 0).text()).toContain("dceName4 (as dataset)");
        expect(nth(selectedValues, 1).text()).toContain("dceName3 (as dataset)");
        expect(nth(selectedValues, 2).text()).toContain("dceName2 (as dataset)");
        expect(nth(selectedValues, 3).text()).toContain("1: hdaName1");
        expect(nth(selectedValues, 4).text()).toContain("2: hdaName2");
        await nth(selectedValues, 0).trigger("click");
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
        expect(emittedArg(wrapper, "input", 1)).toEqual(value_sorted);
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
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
        expect(wrapper.emitted("input")).toHaveLength(1);
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(nth(selectedValues, 0).text()).toContain("dceName1 (as dataset)");
    });

    it("dataset collection element as hdca without map_over_type", async () => {
        const wrapper = createTarget({
            value: { values: [{ id: "dce2", src: "dce" }] },
            options: defaultOptions,
        });
        const value_0 = { batch: true, product: false, values: [{ id: "dce2", map_over_type: null, src: "dce" }] };
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
        await wrapper.vm.$nextTick();
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(nth(selectedValues, 0).text()).toContain("dceName2 (as dataset collection)");
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
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
        await wrapper.vm.$nextTick();
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(nth(selectedValues, 0).text()).toContain("dceName3 (as dataset collection)");
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
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
        await wrapper.vm.$nextTick();
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(nth(selectedValues, 0).text()).toContain("dceName3 (as dataset collection)");
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
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
        await wrapper.vm.$nextTick();
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(nth(selectedValues, 0).text()).toContain("5: hdcaName5");
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
        expect(emittedArg(wrapper, "input")).toEqual(value_0);
    });

    it("dropping values", async () => {
        const wrapper = createTarget({
            value: null,
            options: defaultOptions,
        });
        eventStore.setDragData({ id: "hdca4", history_content_type: "dataset_collection" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(emittedArg(wrapper, "input", 1)).toEqual({
            batch: true,
            product: false,
            values: [{ id: "hdca4", map_over_type: null, src: "hdca" }],
        });
        eventStore.setDragData({ id: "hda2", history_content_type: "dataset" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(emittedArg(wrapper, "input", 2)).toEqual({
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
        expect(emittedArg(wrapper, "alert")).toEqual("dataset is not a valid input for dataset collection parameter.");
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
        expect(emittedArg(wrapper, "alert")).toEqual(
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
        expect(wrapper.emitted("alert")).toBeUndefined();
    });

    it("linked and unlinked batch mode handling", async () => {
        const wrapper = createTarget({
            value: null,
            flavor: "module",
            options: defaultOptions,
        });
        expect(emittedArg(wrapper, "input")).toEqual({
            batch: false,
            product: false,
            values: [{ id: "dce4", map_over_type: null, src: "dce" }],
        });
        const noCheckLinked = wrapper.find("input[type='checkbox']");
        expect(noCheckLinked.exists()).toBeFalsy();
        await wrapper.find("[title='Multiple datasets']").trigger("click");
        expect(emittedArg(wrapper, "input", 1)).toEqual(null);
        await openMultiselect(wrapper);
        const elements_0 = wrapper.findAll(SELECT_OPTIONS);
        expect(elements_0.length).toEqual(6);
        await nth(elements_0, 3).find("span").trigger("click");
        const value_0 = {
            batch: true,
            product: false,
            values: [{ id: "hda2", map_over_type: null, src: "hda" }],
        };
        expect(emittedArg(wrapper, "input", 2)).toEqual(value_0);
        await wrapper.setProps({ value: value_0 });
        await nth(elements_0, 0).find("span").trigger("click");
        const value_1 = {
            batch: true,
            product: false,
            values: [
                { id: "hda2", map_over_type: null, src: "hda" },
                { id: "dce4", map_over_type: null, src: "dce" },
            ],
        };
        expect(emittedArg(wrapper, "input", 3)).toEqual(value_1);
        await wrapper.setProps({ value: value_1 });
        const checkLinked = wrapper.find("input[type='checkbox']");
        expect(wrapper.find(".g-switch .g-checkbox-label").text()).toBe(
            "Linked:Datasets will be run in matched order with other datasets.",
        );
        expect((checkLinked.element as HTMLInputElement).checked).toBeTruthy();
        await checkLinked.setValue(false);
        expect(wrapper.find(".g-switch .g-checkbox-label").text()).toBe(
            "Unlinked:Dataset will be run against *all* other datasets.",
        );
        expect(emittedArg(wrapper, "input", 4)).toEqual({
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
        const options = wrapper.find(".g-button-group").findAll("button");
        expect(options.length).toBe(3);
        expect(nth(options, 1).classes()).toContain("g-pressed");
        expect(nth(options, 1).attributes("title")).toBe("Dataset collection");
        for (const i of [0, 1]) {
            expect(emittedArg(wrapper, "input", i)).toEqual({
                batch: false,
                product: false,
                values: [{ id: "hdca5", map_over_type: null, src: "hdca" }],
            });
        }
        expect(wrapper.emitted("input")).toHaveLength(2);
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(nth(selectedValues, 0).text()).toBe("5: hdcaName5");
        await wrapper.find("[title='Multiple datasets']").trigger("click");
        expect(nth(options, 0).classes()).toContain("g-pressed");
        expect(emittedArg(wrapper, "input", 2)).toEqual(null);
    });

    it("renders pinned entries alongside paged options", async () => {
        // Pinned entries are forced-include items the server returned because
        // they're selected but landed outside the current page window. The
        // dropdown must show them so the user can see what's pre-selected.
        const wrapper = createTarget({
            value: { values: [{ id: "hdaPinned", src: "hda" }] },
            options: { hda: defaultOptions.hda },
            pinned: {
                hda: [{ id: "hdaPinned", hid: 999, name: "OldDataset", src: "hda", keep: true, tags: [] }],
            },
        });
        await wrapper.vm.$nextTick();
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(1);
        expect(nth(selectedValues, 0).text()).toContain("999: OldDataset");
    });

    it("tagging filter", async () => {
        const wrapper_0 = createTarget({
            tag: "tag1",
            options: defaultOptions,
        });
        await openMultiselect(wrapper_0);
        const select_0 = wrapper_0.findAll(SELECT_OPTIONS);
        expect(select_0.length).toBe(4);
        expect(nth(select_0, 2).text()).toContain("1: hdaName1");
        expect(nth(select_0, 3).text()).toContain("2: hdaName2");
        const wrapper_1 = createTarget({
            tag: "tag2",
            options: defaultOptions,
        });
        await openMultiselect(wrapper_1);
        const select_1 = wrapper_1.findAll(SELECT_OPTIONS);
        expect(select_1.length).toBe(4);
        expect(nth(select_1, 2).text()).toContain("2: hdaName2");
        expect(nth(select_1, 3).text()).toContain("3: hdaName3");
        const wrapper_2 = createTarget({
            tag: "tag3",
            options: defaultOptions,
        });
        await openMultiselect(wrapper_2);
        const select_2 = wrapper_2.findAll(SELECT_OPTIONS);
        expect(select_2.length).toBe(3);
        expect(nth(select_2, 2).text()).toContain("3: hdaName3");
    });
});

describe("FormData batch hint", () => {
    const BATCH_INFO = ".info.text-info";
    const MAPPED_OVER = /^The supplied input will be .*mapped over this tool\.$/;
    const MAPPED_OVER_PER_DATASET = /^The supplied input will be .*mapped over this tool: one job per dataset\.$/;
    const MAPPED_OVER_PER_PAIR = /^The supplied input will be .*mapped over this tool: one job per dataset pair\.$/;

    function batchInfoText(wrapper: ReturnType<typeof createTarget>) {
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
        expect(wrapper.find(".g-pressed").attributes("title")).toBe("Dataset collection");
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
        expect((emittedArg(wrapper, "input") as { batch: boolean }).batch).toBe(true);
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
        expect((emittedArg(wrapper, "input") as { batch: boolean }).batch).toBe(true);
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
        const emitted = emittedArg(wrapper, "input", -1);
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
        expect(wrapper.find(".g-pressed").attributes("title")).toBe("Dataset collection");
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
