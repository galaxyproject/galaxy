import { createTestingPinia } from "@pinia/testing";
import { deferred } from "@tests/vitest/deferred";
import { createTestRouter, emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import * as datasetCollectionsApi from "@/api/datasetCollections";
import * as datasetsApi from "@/api/datasets";
import { updateContentFields } from "@/components/History/model/queries";
import { Toast } from "@/composables/toast";

import ContentItem from "./ContentItem.vue";
import ContentOptions from "./ContentOptions.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

vi.mock("@/components/History/model/queries");
vi.mock("@/composables/toast");

const { server, http } = useServerMock();

const localVue = getLocalVue();
const router = createTestRouter();

vi.mock("vue-router", async (importOriginal) => ({
    ...(await importOriginal()),
    useRoute: vi.fn(() => ({})),
    useRouter: vi.fn(() => ({})),
}));

const item = {
    id: "item_id",
    history_id: "history_id",
    history_content_type: "dataset",
    some_data: "some_data",
    tags: ["tag1", "tag2", "tag3"],
    deleted: false,
    visible: true,
};

const deletedCollection = {
    ...item,
    collection_type: "list",
    history_content_type: "dataset_collection",
    element_count: 2,
    elements_datatypes: [],
    elements_states: { ok: 2 },
    elements_deleted: 2,
    elements_purged: 2,
    deleted: true,
};

describe("ContentItem", () => {
    let wrapper;

    beforeEach(() => {
        vi.clearAllMocks();
        updateContentFields.mockReset().mockImplementation(async (content, fields) => ({ ...content, ...fields }));
        server.use(
            http.get("/api/object_stores", ({ response }) => {
                return response(200).json([]);
            }),

            http.get("/api/datasets/{dataset_id}", ({ response }) => {
                // We need to use untyped here because this endpoint is not
                // described in the OpenAPI spec due to its complexity for now.
                return response.untyped(HttpResponse.json(item));
            }),
        );

        wrapper = mount(ContentItem, {
            props: {
                expandDataset: true,
                item: { ...item, tags: [...item.tags] },
                id: 1,
                isDataset: true,
                isHistoryItem: true,
                name: "name",
                selected: false,
                selectable: false,
                filterable: true,
                onTagChange: (content, tags) => (content.tags = tags),
            },
            global: localVue,
            stubs: {
                DatasetDetails: true,
                vueTagsInput: false,
            },
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
            router,
        });
    });

    afterEach(() => {
        wrapper.unmount();
        vi.restoreAllMocks();
    });

    it("serializes tag saves and keeps the newest tags visible across an item refresh", async () => {
        const first = deferred();
        const second = deferred();
        updateContentFields.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
        const editor = wrapper.getComponent(StatelessTags);
        editor.vm.$emit("update:modelValue", ["first"]);
        editor.vm.$emit("update:modelValue", ["first", "group=two"]);
        await flushPromises();

        expect(updateContentFields).toHaveBeenCalledTimes(1);
        expect(updateContentFields).toHaveBeenLastCalledWith(expect.objectContaining({ id: item.id }), {
            tags: ["first"],
        });
        expect(editor.props("modelValue")).toEqual(["first", "group=two"]);
        expect(wrapper.emitted("tag-change").map((args) => args[1])).toEqual([["first"], ["first", "group=two"]]);

        await wrapper.setProps({ item: { ...item, tags: [] } });
        first.resolve({ ...item, tags: ["first"] });
        await flushPromises();
        expect(updateContentFields).toHaveBeenCalledTimes(2);
        expect(updateContentFields).toHaveBeenLastCalledWith(expect.objectContaining({ id: item.id }), {
            tags: ["first", "group=two"],
        });

        second.resolve({ ...item, tags: ["first", "group:two"] });
        await flushPromises();
        expect(editor.props("modelValue")).toEqual(["first", "group:two"]);
        expect(Toast.error).not.toHaveBeenCalled();
    });

    it("keeps the requested tags when a successful response omits them", async () => {
        updateContentFields.mockResolvedValueOnce({});
        const editor = wrapper.getComponent(StatelessTags);
        editor.vm.$emit("update:modelValue", ["saved"]);
        await flushPromises();
        expect(editor.props("modelValue")).toEqual(["saved"]);
        expect(Toast.error).not.toHaveBeenCalled();
    });

    it.each(["dataset", "dataset_collection"])(
        "reloads a %s and shows a toast after a failed tag save",
        async (type) => {
            await flushPromises();
            const isDataset = type === "dataset";
            const reload = isDataset
                ? vi.spyOn(datasetsApi, "fetchDatasetDetails")
                : vi.spyOn(datasetCollectionsApi, "fetchCollectionSummary");
            reload.mockResolvedValue({ ...item, tags: ["stored"] });
            await wrapper.setProps({
                isDataset,
                item: { ...(isDataset ? item : deletedCollection), deleted: false, tags: [] },
            });
            await flushPromises();
            reload.mockClear();
            updateContentFields.mockRejectedValueOnce(new Error("save failed"));

            wrapper.getComponent(StatelessTags).vm.$emit("update:modelValue", ["unsaved"]);
            await flushPromises();

            expect(Toast.error).toHaveBeenCalledExactlyOnceWith("Failed to save tags: save failed");
            expect(reload).toHaveBeenCalledExactlyOnceWith(isDataset ? { id: item.id } : { hdca_id: item.id });
            expect(wrapper.getComponent(StatelessTags).props("modelValue")).toEqual(["stored"]);
        },
    );

    it("keeps dataset and collection queues separate when their ids match", async () => {
        const datasetSave = deferred();
        const collectionSave = deferred();
        updateContentFields.mockReturnValueOnce(datasetSave.promise).mockReturnValueOnce(collectionSave.promise);
        wrapper.getComponent(StatelessTags).vm.$emit("update:modelValue", ["dataset"]);
        await flushPromises();

        await wrapper.setProps({ isDataset: false, item: { ...deletedCollection, deleted: false, tags: [] } });
        wrapper.getComponent(StatelessTags).vm.$emit("update:modelValue", ["collection"]);
        await flushPromises();
        expect(updateContentFields).toHaveBeenCalledTimes(2);
        expect(updateContentFields.mock.calls.map(([content]) => content.history_content_type)).toEqual([
            "dataset",
            "dataset_collection",
        ]);

        datasetSave.resolve({ ...item, tags: ["saved dataset"] });
        await flushPromises();
        expect(wrapper.getComponent(StatelessTags).props("modelValue")).toEqual(["collection"]);

        collectionSave.resolve({ ...deletedCollection, tags: ["saved collection"] });
        await flushPromises();
        expect(wrapper.getComponent(StatelessTags).props("modelValue")).toEqual(["saved collection"]);
    });

    it("does not let a failed save's reload overwrite a newer edit", async () => {
        await flushPromises();
        const reload = deferred();
        vi.spyOn(datasetsApi, "fetchDatasetDetails").mockReturnValueOnce(reload.promise);
        updateContentFields.mockRejectedValueOnce(new Error("save failed"));
        const editor = wrapper.getComponent(StatelessTags);
        editor.vm.$emit("update:modelValue", ["unsaved"]);
        await flushPromises();
        expect(datasetsApi.fetchDatasetDetails).toHaveBeenCalledWith({ id: item.id });

        editor.vm.$emit("update:modelValue", ["newer"]);
        await flushPromises();
        reload.resolve({ ...item, tags: ["old"] });
        await flushPromises();
        expect(editor.props("modelValue")).toEqual(["newer"]);
    });

    it("handles a failed reload without leaving an unhandled rejection", async () => {
        await flushPromises();
        vi.spyOn(datasetsApi, "fetchDatasetDetails").mockRejectedValueOnce(new Error("reload failed"));
        updateContentFields.mockRejectedValueOnce(new Error("save failed"));

        wrapper.getComponent(StatelessTags).vm.$emit("update:modelValue", ["unsaved"]);
        await flushPromises();

        expect(Toast.error.mock.calls.map(([message]) => message)).toEqual([
            "Failed to save tags: save failed",
            "Failed to reload tags: reload failed",
        ]);
    });

    it("names the converted-item count with its action", async () => {
        await wrapper.setProps({ item: { ...item, sub_items: [{ id: "converted-1" }, { id: "converted-2" }] } });
        const button = wrapper.get("button.display-btn");
        expect(button.attributes("aria-label")).toBe("Show converted items (2)");
        await button.trigger("click");
        await wrapper.setProps({ item: { ...item, sub_items: [{ id: "converted-1" }] } });
        expect(wrapper.get("button.display-btn").attributes("aria-label")).toBe("Show converted items (1)");
    });

    it("shows a collection as purged only when all its elements are purged", async () => {
        await wrapper.setProps({ isDataset: false, item: { ...deletedCollection, elements_purged: 1 } });
        expect(wrapper.find(".content-purged").exists()).toBe(false);

        const emptyCounts = { element_count: 0, elements_states: {}, elements_deleted: 0, elements_purged: 0 };
        await wrapper.setProps({ item: { ...deletedCollection, ...emptyCounts } });
        expect(wrapper.find(".content-purged").exists()).toBe(false);

        await wrapper.setProps({ item: deletedCollection });
        expect(wrapper.find(".content-purged").exists()).toBe(true);
        expect(wrapper.findComponent(ContentOptions).exists()).toBe(false);
    });

    it("keeps the options of a non-deleted collection whose elements are all purged", async () => {
        await wrapper.setProps({ isDataset: false, item: { ...deletedCollection, deleted: false } });
        expect(wrapper.find(".content-purged").exists()).toBe(true);
        expect(wrapper.findComponent(ContentOptions).exists()).toBe(true);
    });

    it("hides the options of a purged collection element dataset", async () => {
        await wrapper.setProps({ isHistoryItem: false, item: { id: "item_id", purged: true } });
        expect(wrapper.find(".content-purged").exists()).toBe(true);
        expect(wrapper.findComponent(ContentOptions).exists()).toBe(false);
    });

    it("exposes whether the converted items are shown", async () => {
        await wrapper.setProps({ item: { ...item, sub_items: [{ id: "converted-1" }] } });
        const button = wrapper.get("button.display-btn");
        expect(button.attributes("aria-expanded")).toBe("false");

        await button.trigger("click");
        expect(button.attributes("aria-expanded")).toBe("true");

        await button.trigger("click");
        expect(button.attributes("aria-expanded")).toBe("false");
    });

    it("check basics", async () => {
        expect(wrapper.attributes("data-hid")).toBe("1");
        expect(wrapper.find(".content-title").text()).toBe("name");
        const tags = wrapper.find(".stateless-tags").findAll(".tag");

        // verify tags
        expect(tags.length).toBe(3);

        for (let i = 0; i < 3; i++) {
            expect(tags.at(i).text()).toBe(`tag${i + 1}`);

            await tags.at(i).trigger("click");
            expect(emittedArg(wrapper, "tag-click", i)).toBe(`tag${i + 1}`);
        }

        // close all tags
        for (let i = 0; i < 3; i++) {
            const tagRemover = wrapper.find(`.tag[data-option=tag${i + 1}] button`);

            await tagRemover.trigger("click");
            expect(wrapper.emitted("tag-change").at(-1)[1]).not.toContain(`tag${i + 1}`);
        }

        await wrapper.setProps({ isHistoryItem: false, item: { tags: [] } });
        expect(wrapper.find(".stateless-tags").exists()).toBe(false);

        // expansion button
        const $el = wrapper.find(".cursor-pointer");
        $el.trigger("click");
        expect(wrapper.emitted("update:expand-dataset")).toBeDefined();

        // select and unselect
        const noSelector = wrapper.find(".selector > svg");
        expect(noSelector.exists()).toBe(false);

        await wrapper.setProps({ selectable: true });
        expect(wrapper.classes()).toEqual(expect.arrayContaining(["alert-success"]));

        const selector = wrapper.find(".selector > svg");
        expect(selector.attributes("data-icon")).toBe("square");
        selector.trigger("click");

        await nextTick();
        expect(emittedArg(wrapper, "update:selected")).toBe(true);

        await wrapper.setProps({ selected: true });
        // The icon re-renders as a new <svg>, so look it up again.
        const checkedSelector = wrapper.find(".selector > svg");
        expect(checkedSelector.attributes("data-icon")).toBe("check-square");
        checkedSelector.trigger("click");

        await nextTick();
        expect(emittedArg(wrapper, "update:selected", 1)).toBe(false);
        expect(wrapper.classes()).toEqual(expect.arrayContaining(["alert-info"]));
    });

    // A native <button> already turns Enter/Space into a click, so a keypress listener on
    // top of @click toggles twice per key press, and the two toggles cancel each other out.
    it("toggles the active highlight once per click", async () => {
        await wrapper.setProps({ highlight: "active" });
        const button = wrapper.get("button[title='Inputs/Outputs highlighted for this item']");
        await button.trigger("click");
        expect(wrapper.emitted("toggleHighlights")).toHaveLength(1);
    });

    it("leaves keyboard activation to the button's own click", async () => {
        await wrapper.setProps({ highlight: "active" });
        const button = wrapper.get("button[title='Inputs/Outputs highlighted for this item']");
        await button.trigger("keypress", { key: "Enter" });
        expect(wrapper.emitted("toggleHighlights")).toBeUndefined();
    });
});
