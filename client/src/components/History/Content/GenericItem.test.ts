import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressLucideVue2Deprecation } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { fetchCollectionDetails, fetchCollectionSummary } from "@/api/datasetCollections";
import { fetchDatasetDetails } from "@/api/datasets";
import { setupSelectableMock } from "@/components/ObjectStore/mockServices";
import { ApiError } from "@/utils/simple-error";

import CollectionDescription from "./Collection/CollectionDescription.vue";
import ContentItem from "./ContentItem.vue";
import GenericItem from "./GenericItem.vue";

vi.mock("@/api/datasets");
vi.mock("@/api/datasetCollections");

setupSelectableMock();

const localVue = getLocalVue();

class VisibleIntersectionObserver {
    constructor(private callback: IntersectionObserverCallback) {}
    observe(target: Element) {
        this.callback([{ isIntersecting: true, target } as IntersectionObserverEntry], this as never);
    }
    unobserve() {}
    disconnect() {}
}

describe.each(["hda", "hdca"])("GenericItem (%s)", (itemSrc) => {
    let wrapper: VueWrapper;
    const fetchItem = vi.mocked(itemSrc === "hda" ? fetchDatasetDetails : fetchCollectionSummary);
    const item = {
        id: "item-id",
        hid: 1,
        name: "Test item",
        history_content_type: itemSrc === "hda" ? "dataset" : "dataset_collection",
        state: "running",
        populated_state: "new",
        collection_type: "list",
        element_count: 2,
        elements_datatypes: ["txt"],
        tags: [],
    };

    beforeEach(() => {
        suppressLucideVue2Deprecation();
        vi.stubGlobal("IntersectionObserver", VisibleIntersectionObserver);
        fetchItem.mockReset();
    });

    afterEach(() => {
        wrapper?.unmount();
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    function mountItem(expanded?: boolean) {
        wrapper = mount(GenericItem as object, {
            localVue,
            router: createRouter({ history: createMemoryHistory(), routes: [] }),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: { itemId: item.id, itemSrc, expanded },
            stubs: { ContentOptions: true, DatasetDetails: true, StatelessTags: true, GenericElement: true },
        });
    }

    function expectFetchError(message: string) {
        expect(wrapper.find('[role="alert"]').text()).toContain(message);
        expect(wrapper.findComponent(ContentItem).exists()).toBe(false);
        expect(wrapper.findComponent(CollectionDescription).exists()).toBe(false);
        expect(wrapper.text()).not.toContain("Loading dataset");
    }

    it.each([new ApiError("Too Many Requests", 429), new TypeError("Failed to fetch")])(
        "shows an initial fetch error: %s",
        async (error) => {
            fetchItem.mockRejectedValue(error);
            mountItem();
            await flushPromises();

            expect(fetchItem).toHaveBeenCalledOnce();
            expectFetchError(error.message);
        },
    );

    it("renders a successfully fetched item", async () => {
        fetchItem.mockResolvedValue(item as never);
        mountItem();
        await flushPromises();

        expect(wrapper.find('[role="alert"]').exists()).toBe(false);
        expect(wrapper.findComponent(ContentItem).props("item")).toEqual(item);
        expect(wrapper.findComponent(ContentItem).props("isDataset")).toBe(itemSrc === "hda");
        expect(wrapper.findComponent(CollectionDescription).exists()).toBe(itemSrc === "hdca");
    });

    it("supports controlled expansion changes and emits user expansion without resetting embedded items", async () => {
        fetchItem.mockResolvedValue(item as never);
        vi.mocked(fetchCollectionDetails).mockResolvedValue({ data: item } as never);
        mountItem(false);
        await flushPromises();
        await wrapper.setProps({ expanded: true });
        await flushPromises();
        if (itemSrc === "hda") {
            expect(wrapper.findComponent(ContentItem).props("expandDataset")).toBe(true);
        } else {
            expect(wrapper.findComponent({ name: "GenericElement" }).exists()).toBe(true);
        }
        await wrapper.setProps({ expanded: false });
        if (itemSrc === "hda") {
            expect(wrapper.findComponent(ContentItem).props("expandDataset")).toBe(false);
        } else {
            expect(wrapper.findComponent({ name: "GenericElement" }).exists()).toBe(false);
        }
        wrapper.unmount();
        mountItem();
        await flushPromises();
        const content = wrapper.findComponent(ContentItem);
        if (itemSrc === "hda") {
            content.vm.$emit("update:expand-dataset", true);
            await flushPromises();
            expect(content.props("expandDataset")).toBe(true);
        } else {
            content.vm.$emit("view-collection", { model_class: "HistoryDatasetCollectionAssociation" });
            await flushPromises();
            expect(wrapper.findComponent({ name: "GenericElement" }).exists()).toBe(true);
        }
        expect(wrapper.emitted("update:expanded")).toEqual([[true]]);
    });

    it("replaces content with the error when an automatic refresh fails", async () => {
        vi.useFakeTimers();
        fetchItem.mockResolvedValueOnce(item as never).mockRejectedValueOnce(new TypeError("Failed to fetch"));
        mountItem();
        await flushPromises();
        expect(wrapper.findComponent(ContentItem).exists()).toBe(true);

        await vi.advanceTimersByTimeAsync(3000);
        await flushPromises();

        expect(fetchItem).toHaveBeenCalledTimes(2);
        expectFetchError("Failed to fetch");
    });
});

describe("GenericItem dataset collection elements", () => {
    it("keeps embedded dataset element expansion in ContentItem", async () => {
        vi.stubGlobal("IntersectionObserver", VisibleIntersectionObserver);
        const get = vi.spyOn(axios, "get").mockResolvedValue({
            data: {
                element_index: 0,
                element_type: "hda",
                element_identifier: "element",
                object: { id: "dataset", history_content_type: "dataset" },
            },
        });
        const wrapper = mount(GenericItem, {
            props: { itemId: "element-id", itemSrc: "dce" },
            global: {
                plugins: [createTestingPinia({ createSpy: vi.fn })],
                stubs: {
                    ContentItem: true,
                    GenericElement: true,
                },
            },
        });
        await flushPromises();
        const content = wrapper.findComponent(ContentItem);
        expect(content.props("isDataset")).toBe(true);
        content.vm.$emit("update:expand-dataset", true);
        await flushPromises();
        expect(content.props("expandDataset")).toBe(true);
        expect(wrapper.findComponent({ name: "GenericElement" }).exists()).toBe(false);
        expect(wrapper.emitted("update:expanded")).toEqual([[true]]);
        wrapper.unmount();
        get.mockRestore();
        vi.unstubAllGlobals();
    });
});
