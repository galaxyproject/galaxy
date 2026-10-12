import { composeStories } from "@storybook/vue3-vite";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetDetails } from "@tests/test-data/datasets";
import { suppressLucideVue2Deprecation } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { VisibleIntersectionObserver } from "@tests/vitest/visibleIntersectionObserver";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCollectionSummary } from "@/api/datasetCollections";
import { fetchDatasetDetails } from "@/api/datasets";
import { ApiError } from "@/utils/simple-error";

import * as componentStories from "./GenericItem.stories";

import CollectionDescription from "./Collection/CollectionDescription.vue";
import ContentItem from "./ContentItem.vue";

vi.mock("@/api/datasets", { spy: true });
vi.mock("@/api/datasetCollections", { spy: true });

const stories = composeStories(componentStories);
const mountStory = useStoryMount();
const dataset = getFakeDatasetDetails({ id: "item-id", name: "Alignment output", state: "running" });
const collection = getFakeCollectionSummary({
    id: "item-id",
    name: "Alignment collection",
    populated_state: "new",
    element_count: 2,
});

describe.each([
    {
        itemSrc: "hda",
        item: dataset,
        isDataset: true,
        success: stories.RunningDataset,
        denied: stories.DatasetAccessDenied,
        network: stories.DatasetNetworkFailure,
    },
    {
        itemSrc: "hdca",
        item: collection,
        isDataset: false,
        success: stories.PopulatingCollection,
        denied: stories.CollectionHistoryAccessDenied,
        network: stories.CollectionNetworkFailure,
    },
])("GenericItem ($itemSrc)", ({ itemSrc, item, isDataset, success, denied, network }) => {
    let mountedWrapper: VueWrapper | undefined;
    const fetchItem = vi.mocked(itemSrc === "hda" ? fetchDatasetDetails : fetchCollectionSummary);

    beforeEach(() => {
        suppressLucideVue2Deprecation();
        vi.stubGlobal("IntersectionObserver", VisibleIntersectionObserver);
        vi.mocked(fetchDatasetDetails).mockReset();
        vi.mocked(fetchCollectionSummary).mockReset();
    });

    afterEach(() => {
        // Stop the provider's polling while its fake timers and observer still exist.
        mountedWrapper?.unmount();
        mountedWrapper = undefined;
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    async function mountItem(story: StoryOf<typeof stories>) {
        mountedWrapper = mountStory(story);
        await flushPromises();
        await vi.waitFor(() => {
            expect(
                mountedWrapper!.findComponent(ContentItem).exists() || mountedWrapper!.find('[role="alert"]').exists(),
            ).toBe(true);
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
        // The original 429 message and browser network message test provider error handling.
        // The endpoint stories use real 403 bodies; neither GET endpoint is rate limited.
        fetchItem.mockRejectedValueOnce(error);
        const wrapper = await mountItem(error instanceof ApiError ? denied : network);

        expect(fetchItem).toHaveBeenCalledOnce();
        expectFetchError(wrapper, error.message);
    });

    it("renders a successfully fetched item", async () => {
        const wrapper = await mountItem(success);

        expect(fetchItem).toHaveBeenCalledOnce();
        expect(wrapper.find('[role="alert"]').exists()).toBe(false);
        expect(wrapper.findComponent(ContentItem).props("item")).toEqual(item);
        expect(wrapper.findComponent(ContentItem).props("isDataset")).toBe(isDataset);
        expect(wrapper.findComponent(CollectionDescription).exists()).toBe(!isDataset);
    });

    it("replaces content with the error when an automatic refresh fails", async () => {
        vi.useFakeTimers();
        const wrapper = await mountItem(success);
        expect(wrapper.findComponent(ContentItem).exists()).toBe(true);

        fetchItem.mockRejectedValueOnce(new TypeError("Failed to fetch"));
        await vi.advanceTimersByTimeAsync(3000);
        await flushPromises();

        expect(fetchItem).toHaveBeenCalledTimes(2);
        expectFetchError(wrapper, "Failed to fetch");
    });
});
