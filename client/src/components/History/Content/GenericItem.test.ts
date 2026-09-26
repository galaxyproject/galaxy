import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressLucideVue2Deprecation } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import VueRouter from "vue-router";

import { fetchCollectionSummary } from "@/api/datasetCollections";
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
localVue.use(VueRouter);

class VisibleIntersectionObserver {
    constructor(private callback: IntersectionObserverCallback) {}
    observe(target: Element) {
        this.callback([{ isIntersecting: true, target } as IntersectionObserverEntry], this as never);
    }
    unobserve() {}
    disconnect() {}
}

describe.each(["hda", "hdca"])("GenericItem (%s)", (itemSrc) => {
    let wrapper: Wrapper<Vue>;
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
        wrapper?.destroy();
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    function mountItem() {
        wrapper = mount(GenericItem, {
            localVue,
            router: new VueRouter(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: { itemId: item.id, itemSrc },
            stubs: { ContentOptions: true, DatasetDetails: true, StatelessTags: true },
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
