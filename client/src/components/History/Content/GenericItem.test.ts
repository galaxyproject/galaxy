import { createTestingPinia } from "@pinia/testing";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { getLocalVue, suppressLucideVue2Deprecation, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import type { HDADetailed } from "@/api";
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
const dataset: HDADetailed = {
    ...getFakeDatasetSummary({ id: "item-id", name: "Test item", state: "running" }),
    accessible: true,
    annotation: null,
    api_type: "file",
    type: "file",
    creating_job: "job-id",
    data_type: "galaxy.datatypes.data.Text",
    display_apps: [],
    display_types: [],
    download_url: "/api/datasets/item-id/display",
    drs_id: "item-id",
    file_ext: "txt",
    file_size: 0,
    hashes: [],
    hda_ldda: "hda",
    meta_files: [],
    model_class: "HistoryDatasetAssociation",
    permissions: { access: [], manage: [] },
    rerunnable: false,
    resubmitted: false,
    sources: [],
    uuid: "00000000-0000-4000-8000-000000000001",
    validated_state: "unknown",
};
const collection = getFakeCollectionSummary({
    id: "item-id",
    name: "Test item",
    populated_state: "new",
    element_count: 2,
    store_times_summary: undefined,
});

class VisibleIntersectionObserver {
    constructor(private callback: IntersectionObserverCallback) {}
    observe(target: Element) {
        this.callback([{ isIntersecting: true, target } as IntersectionObserverEntry], this as never);
    }
    unobserve() {}
    disconnect() {}
}

describe.each([
    { itemSrc: "hda", item: dataset, isDataset: true },
    { itemSrc: "hdca", item: collection, isDataset: false },
])("GenericItem ($itemSrc)", ({ itemSrc, item, isDataset }) => {
    let mountedWrapper: VueWrapper | undefined;
    const fetchItem = vi.mocked(itemSrc === "hda" ? fetchDatasetDetails : fetchCollectionSummary);

    beforeEach(() => {
        suppressLucideVue2Deprecation();
        vi.stubGlobal("IntersectionObserver", VisibleIntersectionObserver);
        vi.mocked(fetchDatasetDetails).mockReset().mockResolvedValue(dataset);
        vi.mocked(fetchCollectionSummary).mockReset().mockResolvedValue(collection);
    });

    afterEach(() => {
        // Stop the provider's polling while its fake timers and observer still exist.
        mountedWrapper?.unmount();
        mountedWrapper = undefined;
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    async function mountItem() {
        const global = withPlugins(
            localVue,
            createRouter({ history: createMemoryHistory(), routes: [] }),
            createTestingPinia({ createSpy: vi.fn }),
        );
        mountedWrapper = mount(GenericItem, {
            props: { itemId: item.id, itemSrc },
            global: {
                ...global,
                stubs: { ...global.stubs, ContentOptions: true, DatasetDetails: true, StatelessTags: true },
            },
        });
        await flushPromises();
        return mountedWrapper;
    }

    function expectFetchError(wrapper: VueWrapper, message: string) {
        expect(wrapper.find('[role="alert"]').text()).toContain(message);
        expect(wrapper.findComponent(ContentItem).exists()).toBe(false);
        expect(wrapper.findComponent(CollectionDescription).exists()).toBe(false);
        expect(wrapper.text()).not.toContain("Loading dataset");
    }

    it.each([
        { failure: "HTTP 429", error: new ApiError("Too Many Requests", 429) },
        { failure: "network failure", error: new TypeError("Failed to fetch") },
    ])("shows the error and hides content after an initial $failure", async ({ error }) => {
        fetchItem.mockRejectedValue(error);
        const wrapper = await mountItem();

        expect(fetchItem).toHaveBeenCalledOnce();
        expectFetchError(wrapper, error.message);
    });

    it("renders a successfully fetched item", async () => {
        const wrapper = await mountItem();

        expect(fetchItem).toHaveBeenCalledOnce();
        expect(wrapper.find('[role="alert"]').exists()).toBe(false);
        expect(wrapper.findComponent(ContentItem).props("item")).toEqual(item);
        expect(wrapper.findComponent(ContentItem).props("isDataset")).toBe(isDataset);
        expect(wrapper.findComponent(CollectionDescription).exists()).toBe(!isDataset);
    });

    it("replaces content with the error when an automatic refresh fails", async () => {
        vi.useFakeTimers();
        const wrapper = await mountItem();
        expect(wrapper.findComponent(ContentItem).exists()).toBe(true);

        fetchItem.mockRejectedValueOnce(new TypeError("Failed to fetch"));
        await vi.advanceTimersByTimeAsync(3000);
        await flushPromises();

        expect(fetchItem).toHaveBeenCalledTimes(2);
        expectFetchError(wrapper, "Failed to fetch");
    });
});
