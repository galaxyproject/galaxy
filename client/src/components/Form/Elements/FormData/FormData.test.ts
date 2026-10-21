import "@tests/vitest/mockHelpPopovers";
import "@/composables/__mocks__/filter";

import { composeStories } from "@storybook/vue3-vite";
import { dispatchEvent, emittedArg, nth } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { useEventStore } from "@/stores/eventStore";

import * as FormDataStories from "./FormData.stories";

import FormData from "./FormData.vue";

vi.mock("@/composables/filter");

const stories = composeStories(FormDataStories);
const mountStory = useStoryMount();

const SELECT_OPTIONS = ".multiselect__element";
const SELECTED_VALUE = ".multiselect__option--selected";

/** Mounts a story; returns FormData's wrapper plus a way to change `value` as its parent would. */
function mountFormData(story: StoryOf<typeof stories>, args: Record<string, unknown> = {}) {
    const root = mountStory(story, { props: { vModel: false, ...args }, global: { stubs: { FontAwesomeIcon: true } } });
    const parent = root.findComponent(FormDataStories.FormDataWithModel);
    return {
        wrapper: root.findComponent(FormData),
        eventStore: useEventStore(),
        async setValue(value: unknown) {
            (parent.vm as unknown as { setValue: (value: unknown) => void }).setValue(value);
            await nextTick();
        },
    };
}

type FormDataWrapper = ReturnType<typeof mountFormData>["wrapper"];

/** The `input` payload FormData emits for these [src, id, map_over_type?] selections. */
function inputValue(selections: Array<[string, string, string?]>, { batch = false, product = false } = {}) {
    return {
        batch,
        product,
        values: selections.map(([src, id, mapOverType = null]) => ({ id, map_over_type: mapOverType, src })),
    };
}

// vue-multiselect only renders its option list (and thus SELECT_OPTIONS /
// SELECTED_VALUE) while its dropdown is open, so tests need to open it
// before reading those. Selecting a new value in single-select mode closes
// the dropdown again, so callers re-open as needed between assertions.
async function openMultiselect(wrapper: FormDataWrapper) {
    if (!wrapper.find(".multiselect__content-wrapper").exists()) {
        await wrapper.find(".multiselect__select").trigger("mousedown");
    }
}

async function selectedTexts(wrapper: FormDataWrapper) {
    await nextTick();
    await openMultiselect(wrapper);
    return wrapper.findAll(SELECTED_VALUE).map((selected) => selected.text());
}

describe("FormData", () => {
    it("regular data", async () => {
        const { wrapper, setValue } = mountFormData(stories.SingleDataset);
        const options = wrapper.find(".g-button-group").findAll("button");
        expect(options.length).toBe(4);
        expect(nth(options, 0).classes()).toContain("g-pressed");
        expect(nth(options, 0).attributes("title")).toBe("Single dataset");
        expect(emittedArg(wrapper, "input")).toEqual(inputValue([["dce", "dce4"]]));
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("dceName4 (as dataset)");
        await setValue(inputValue([["dce", "dce4"]]));
        expect(wrapper.emitted("input")).toHaveLength(1);
        await setValue({ values: [{ id: "hda2", src: "hda" }] });
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("2: hdaName2");
        expect(wrapper.emitted("input")).toHaveLength(1);
        await openMultiselect(wrapper);
        const elements_0 = wrapper.findAll(SELECT_OPTIONS);
        expect(elements_0.length).toEqual(6);
        await nth(elements_0, 2).find("span").trigger("click");
        expect(wrapper.emitted("input")).toHaveLength(2);
        expect(emittedArg(wrapper, "input", 1)).toEqual(inputValue([["hda", "hda1"]]));
        await setValue(inputValue([["hda", "hda4"]]));
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toContain("4: hdaName4");
    });

    it("optional dataset", async () => {
        const { wrapper } = mountFormData(stories.OptionalDataset);
        expect(emittedArg(wrapper, "input")).toEqual(null);
        expect(wrapper.emitted("input")).toHaveLength(1);
        await openMultiselect(wrapper);
        expect(wrapper.find(SELECTED_VALUE).text()).toEqual("Nothing selected");
        expect(wrapper.findAll(SELECT_OPTIONS).length).toBe(7);
    });

    it("names the collection type in the no-options alert", () => {
        const { wrapper } = mountFormData(stories.SingleDataset, {
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
        const { wrapper } = mountFormData(stories.NoDatasetsInWorkflowRun);
        const alert = wrapper.find(".form-data-no-options-alert");
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toBe("No datasets available");

        // The alert keeps the aligned styling outside of workflow runs too.
        const toolForm = mountFormData(stories.NoDatasetsInWorkflowRun, { workflowRun: false });
        expect(toolForm.wrapper.find(".form-data-no-options-alert").exists()).toBe(true);
    });

    it("multiple datasets", async () => {
        const { wrapper, setValue } = mountFormData(stories.MultipleDatasets);
        const bothSelected = inputValue([
            ["hda", "hda2"],
            ["hda", "hda3"],
        ]);
        const options = wrapper.find(".g-button-group").findAll("button");
        expect(options.length).toBe(3);
        expect(nth(options, 0).classes()).toContain("g-pressed");
        expect(nth(options, 0).attributes("title")).toBe("Multiple datasets");
        expect(emittedArg(wrapper, "input")).toEqual(bothSelected);
        expect(wrapper.emitted("input")).toHaveLength(1);
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.length).toBe(2);
        expect(nth(selectedValues, 0).text()).toContain("2: hdaName2");
        expect(nth(selectedValues, 1).text()).toContain("3: hdaName3");
        expect(emittedArg(wrapper, "input")).toEqual(bothSelected);
        await nth(selectedValues, 0).trigger("click");
        expect(emittedArg(wrapper, "input", 1)).toEqual(inputValue([["hda", "hda3"]]));
        await setValue(inputValue([["hda", "hda3"]]));
        await nth(selectedValues, 1).trigger("click");
        expect(emittedArg(wrapper, "input", 1)).toEqual(inputValue([["hda", "hda3"]]));
        await setValue(inputValue([["hda", "hda3"]]));
        expect(wrapper.emitted("input")).toHaveLength(3);
        expect(emittedArg(wrapper, "input", 2)).toEqual(null);
    });

    it("properly sorts multiple datasets", async () => {
        const { wrapper } = mountFormData(stories.MultipleDatasetsSelectedOutOfOrder);
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        // the values in the multiselect are sorted by hid ASC
        expect(selectedValues.map((selected) => selected.text())).toEqual([
            expect.stringContaining("1: hdaName1"),
            expect.stringContaining("2: hdaName2"),
            expect.stringContaining("3: hdaName3"),
        ]);
        await nth(selectedValues, 0).trigger("click");
        // the values in the emitted input are sorted by hid ASC
        expect(emittedArg(wrapper, "input", 1)).toEqual(
            inputValue([
                ["hda", "hda2"],
                ["hda", "hda3"],
            ]),
        );
    });

    it("sorts mixed dces and hdas", async () => {
        const { wrapper } = mountFormData(stories.MultipleDatasetsAndElementsIntermixed);
        await openMultiselect(wrapper);
        const selectedValues = wrapper.findAll(SELECTED_VALUE);
        expect(selectedValues.map((selected) => selected.text())).toEqual([
            expect.stringContaining("dceName4 (as dataset)"),
            expect.stringContaining("dceName3 (as dataset)"),
            expect.stringContaining("dceName2 (as dataset)"),
            expect.stringContaining("1: hdaName1"),
            expect.stringContaining("2: hdaName2"),
        ]);
        await nth(selectedValues, 0).trigger("click");
        expect(emittedArg(wrapper, "input", 1)).toEqual(
            inputValue([
                ["hda", "hda1"],
                ["dce", "dce2"],
                ["hda", "hda2"],
                ["dce", "dce3"],
            ]),
        );
    });

    it("dataset collection as hda", async () => {
        const { wrapper } = mountFormData(stories.CollectionElementThatIsADataset);
        expect(emittedArg(wrapper, "input")).toEqual(inputValue([["dce", "dce1"]]));
        expect(wrapper.emitted("input")).toHaveLength(1);
        expect(await selectedTexts(wrapper)).toEqual([expect.stringContaining("dceName1 (as dataset)")]);
    });

    it("dataset collection element as hdca without map_over_type", async () => {
        const { wrapper } = mountFormData(stories.CollectionElementThatIsACollection);
        expect(emittedArg(wrapper, "input")).toEqual(inputValue([["dce", "dce2"]], { batch: true }));
        expect(await selectedTexts(wrapper)).toEqual([expect.stringContaining("dceName2 (as dataset collection)")]);
    });

    it("dataset collection element as hdca mapped to batch field", async () => {
        const { wrapper } = mountFormData(stories.CollectionElementMappedOver);
        expect(emittedArg(wrapper, "input")).toEqual(inputValue([["dce", "dce3", "mapOverType"]], { batch: true }));
        expect(await selectedTexts(wrapper)).toEqual([expect.stringContaining("dceName3 (as dataset collection)")]);
    });

    it("dataset collection element as hdca mapped to non-batch field", async () => {
        const { wrapper } = mountFormData(stories.CollectionElementMappedOverOnCollectionInput);
        expect(emittedArg(wrapper, "input")).toEqual(inputValue([["dce", "dce3", "mapOverType"]], { batch: true }));
        expect(await selectedTexts(wrapper)).toEqual([expect.stringContaining("dceName3 (as dataset collection)")]);
    });

    it("dataset collection mapped to non-batch field", async () => {
        const { wrapper } = mountFormData(stories.CollectionOnCollectionInput);
        expect(emittedArg(wrapper, "input")).toEqual(inputValue([["hdca", "hdca5"]]));
        expect(await selectedTexts(wrapper)).toEqual([expect.stringContaining("5: hdcaName5")]);
    });

    it("multiple dataset collection elements (as hdas)", async () => {
        const { wrapper } = mountFormData(stories.TwoCollectionElementsThatAreDatasets);
        expect(emittedArg(wrapper, "input")).toEqual(
            inputValue(
                [
                    ["dce", "dce1"],
                    ["dce", "dce4"],
                ],
                { batch: true },
            ),
        );
    });

    it("dropping values", async () => {
        const { wrapper, eventStore } = mountFormData(stories.SingleDataset);
        eventStore.setDragData({ id: "hdca4", history_content_type: "dataset_collection" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(emittedArg(wrapper, "input", 1)).toEqual(inputValue([["hdca", "hdca4"]], { batch: true }));
        eventStore.setDragData({ id: "hda2", history_content_type: "dataset" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(emittedArg(wrapper, "input", 2)).toEqual(inputValue([["hda", "hda2"]]));
    });

    it("rejects hda on collection input", async () => {
        const { wrapper, eventStore } = mountFormData(stories.EmptyCollectionInput);
        eventStore.setDragData({ id: "whatever", history_content_type: "dataset" });
        dispatchEvent(wrapper, "dragenter");
        dispatchEvent(wrapper, "drop");
        expect(emittedArg(wrapper, "alert")).toEqual("dataset is not a valid input for dataset collection parameter.");
    });

    it("rejects paired collection on list collection input", async () => {
        const { wrapper, eventStore } = mountFormData(stories.EmptyListCollectionInput);
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
        const { wrapper, eventStore } = mountFormData(stories.EmptyListCollectionInput);
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
        const { wrapper, setValue } = mountFormData(stories.InWorkflowEditor);
        expect(emittedArg(wrapper, "input")).toEqual(inputValue([["dce", "dce4"]]));
        expect(wrapper.find("input[type='checkbox']").exists()).toBeFalsy();
        await wrapper.find("[title='Multiple datasets']").trigger("click");
        expect(emittedArg(wrapper, "input", 1)).toEqual(null);
        await openMultiselect(wrapper);
        const elements_0 = wrapper.findAll(SELECT_OPTIONS);
        expect(elements_0.length).toEqual(6);
        await nth(elements_0, 3).find("span").trigger("click");
        expect(emittedArg(wrapper, "input", 2)).toEqual(inputValue([["hda", "hda2"]], { batch: true }));
        await setValue(inputValue([["hda", "hda2"]], { batch: true }));
        await nth(elements_0, 0).find("span").trigger("click");
        const linked = inputValue(
            [
                ["hda", "hda2"],
                ["dce", "dce4"],
            ],
            { batch: true },
        );
        expect(emittedArg(wrapper, "input", 3)).toEqual(linked);
        await setValue(linked);
        const checkLinked = wrapper.find("input[type='checkbox']");
        expect(wrapper.find(".g-switch .g-checkbox-label").text()).toBe(
            "Linked:Datasets will be run in matched order with other datasets.",
        );
        expect((checkLinked.element as HTMLInputElement).checked).toBeTruthy();
        await checkLinked.setValue(false);
        expect(wrapper.find(".g-switch .g-checkbox-label").text()).toBe(
            "Unlinked:Dataset will be run against *all* other datasets.",
        );
        expect(emittedArg(wrapper, "input", 4)).toEqual({ ...linked, product: true });
    });

    it("match dataset collection on initial value", async () => {
        const { wrapper } = mountFormData(stories.CollectionOnMultipleDatasetsInput);
        await nextTick();
        const options = wrapper.find(".g-button-group").findAll("button");
        expect(options.length).toBe(3);
        expect(nth(options, 1).classes()).toContain("g-pressed");
        expect(nth(options, 1).attributes("title")).toBe("Dataset collection");
        for (const i of [0, 1]) {
            expect(emittedArg(wrapper, "input", i)).toEqual(inputValue([["hdca", "hdca5"]]));
        }
        expect(wrapper.emitted("input")).toHaveLength(2);
        expect(await selectedTexts(wrapper)).toEqual(["5: hdcaName5"]);
        await wrapper.find("[title='Multiple datasets']").trigger("click");
        expect(nth(options, 0).classes()).toContain("g-pressed");
        expect(emittedArg(wrapper, "input", 2)).toEqual(null);
    });

    it("renders pinned entries alongside paged options", async () => {
        // Pinned entries are forced-include items the server returned because
        // they're selected but landed outside the current page window. The
        // dropdown must show them so the user can see what's pre-selected.
        const { wrapper } = mountFormData(stories.PinnedSelectionOutsideCurrentPage);
        expect(await selectedTexts(wrapper)).toEqual([expect.stringContaining("999: OldDataset")]);
    });

    it.each([
        ["tag1", ["1: hdaName1", "2: hdaName2"]],
        ["tag2", ["2: hdaName2", "3: hdaName3"]],
        ["tag3", ["3: hdaName3"]],
    ])("tagging filter %s", async (tag, taggedDatasets) => {
        const { wrapper } = mountFormData(stories.FilteredByTag, { tag });
        await openMultiselect(wrapper);
        const options = wrapper.findAll(SELECT_OPTIONS);
        expect(options.length).toBe(2 + taggedDatasets.length);
        taggedDatasets.forEach((name, i) => expect(nth(options, 2 + i).text()).toContain(name));
    });
});

describe("FormData batch hint", () => {
    const BATCH_INFO = ".info.text-info";
    const MAPPED_OVER = /^The supplied input will be .*mapped over this tool\.$/;
    const MAPPED_OVER_PER_DATASET = /^The supplied input will be .*mapped over this tool: one job per dataset\.$/;
    const MAPPED_OVER_PER_PAIR = /^The supplied input will be .*mapped over this tool: one job per dataset pair\.$/;

    function batchInfoText(wrapper: FormDataWrapper) {
        const info = wrapper.find(BATCH_INFO);
        expect(info.exists()).toBe(true);
        return info.text().replace(/\s+/g, " ");
    }

    it("shows mapped over info for a collection selected on a data input", async () => {
        const { wrapper } = mountFormData(stories.SingleDataset, {
            value: { values: [{ id: "hdca5", src: "hdca" }] },
            options: FormDataStories.default.args.options,
        });
        await wrapper.vm.$nextTick();
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_DATASET);
    });

    it("shows no batch info for a single dataset on a data input", async () => {
        const { wrapper } = mountFormData(stories.SingleDataset, {
            value: { values: [{ id: "hda1", src: "hda" }] },
            options: FormDataStories.default.args.options,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    it("shows batch mode info for multiple datasets on a data input", async () => {
        const { wrapper } = mountFormData(stories.SingleDataset, {
            value: null,
            options: FormDataStories.default.args.options,
        });
        await wrapper.find("[title='Multiple datasets']").trigger("click");
        expect(wrapper.find(BATCH_INFO).text()).toBe(
            "This is a batch mode input field. Individual jobs will be triggered for each dataset.",
        );
    });

    it("shows no batch info for a collection directly selected on a collection input", async () => {
        const { wrapper } = mountFormData(stories.SingleDataset, {
            type: "data_collection",
            value: { values: [{ id: "hdca5", src: "hdca" }] },
            options: FormDataStories.default.args.options,
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
        const { wrapper } = mountFormData(stories.SingleDataset, {
            multiple: true,
            value: { values: [{ id: "hdca8", src: "hdca" }] },
            options: pairedOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".g-pressed").attributes("title")).toBe("Dataset collection");
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    it("shows mapped over info for a nested collection mapped over a collection input", async () => {
        const { wrapper } = mountFormData(stories.SingleDataset, {
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
        const { wrapper } = mountFormData(stories.SingleDataset, {
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
        const { wrapper, setValue } = mountFormData(stories.SingleDataset, {
            type: "data_collection",
            collectionTypes: ["paired"],
            value: { values: [{ id: "hdca8", src: "hdca" }] },
            options: pairedOptions,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
        await setValue({ values: [{ id: "hdca7", src: "hdca" }] });
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_PAIR);
        await setValue({ values: [{ id: "hdca8", src: "hdca" }] });
        expect(wrapper.find(BATCH_INFO).exists()).toBeFalsy();
    });

    it("shows mapped over info for a dropped nested collection on a collection input", async () => {
        const { wrapper, eventStore, setValue } = mountFormData(stories.SingleDataset, {
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
        await setValue(emitted);
        expect(batchInfoText(wrapper)).toMatch(MAPPED_OVER_PER_PAIR);
    });

    it("shows mapped over info when any of multiple selected collections maps over", async () => {
        const { wrapper } = mountFormData(stories.SingleDataset, {
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
        const { wrapper } = mountFormData(stories.SingleDataset, {
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
        const { wrapper } = mountFormData(stories.SingleDataset, {
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
        const { wrapper } = mountFormData(stories.SingleDataset, {
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
