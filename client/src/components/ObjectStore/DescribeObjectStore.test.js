import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { BSpinner } from "bootstrap-vue";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

import * as DescribeObjectStoreStories from "./DescribeObjectStore.stories";

import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";
import ObjectStoreBadges from "./ObjectStoreBadges.vue";
import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const stories = composeStories(DescribeObjectStoreStories);
const mountStory = useStoryMount();

const SELECTORS = {
    BY_NAME: ".display-os-by-name",
    BY_ID: ".display-os-by-id",
    DEFAULT: ".display-os-default",
};

function countDescriptionSpans(wrapper) {
    return Object.fromEntries(
        Object.entries(SELECTORS).map(([key, selector]) => [key, wrapper.findAll(selector).length]),
    );
}

function mountQuotaStorage() {
    return mountStory(stories.StorageWithId, {
        props: {
            storageInfo: { ...stories.StorageWithId.args.storageInfo, quota: { enabled: true, source: "lab" } },
        },
        pinia: { stubActions: true },
    });
}

describe("DescribeObjectStore.vue", () => {
    it.each([
        ["the default storage when it has no id", stories.DefaultStorage, { BY_NAME: 0, BY_ID: 0, DEFAULT: 1 }, false],
        [
            "the storage id when it has an id but no name",
            stories.StorageWithId,
            { BY_NAME: 0, BY_ID: 1, DEFAULT: 0 },
            false,
        ],
        ["the storage name when it has one", stories.NamedPrivateStorage, { BY_NAME: 1, BY_ID: 0, DEFAULT: 0 }, true],
    ])("describes %s", (_description, story, expectedSpans, isPrivate) => {
        const wrapper = mountStory(story);

        expect(countDescriptionSpans(wrapper)).toEqual(expectedSpans);
        expect(wrapper.findComponent(ObjectStoreRestrictionSpan).props("isPrivate")).toBe(isPrivate);
    });

    it.each([
        ["no id", stories.DefaultStorage],
        ["an id", stories.StorageWithId],
        ["a name", stories.NamedPrivateStorage],
    ])("says no quota is configured, without a usage spinner, for storage with %s", (_description, story) => {
        const wrapper = mountStory(story);

        expect(wrapper.text()).toContain("Galaxy has no quota configured for this storage.");
        expect(wrapper.findComponent(BSpinner).exists()).toBe(false);
    });

    it("shows the storage id in bold", () => {
        const wrapper = mountStory(stories.StorageWithId);

        expect(wrapper.find(`${SELECTORS.BY_ID} b`).text()).toBe("fast_scratch");
    });

    it("shows the storage name instead of its id", () => {
        const wrapper = mountStory(stories.NamedPrivateStorage);

        expect(wrapper.find(`${SELECTORS.BY_NAME} b`).text()).toBe("Fast scratch");
        expect(wrapper.text()).not.toContain("fast_scratch");
    });

    it("renders the storage description as markdown", () => {
        const wrapper = mountStory(stories.NamedPrivateStorage);

        expect(wrapper.findComponent(ConfigurationMarkdown).props("markdown")).toBe(
            stories.NamedPrivateStorage.args.storageInfo.description,
        );
    });

    it("shows a spinner while the quota usage of its source is loading", async () => {
        const wrapper = mountQuotaStorage();
        useQuotaUsageStore().loadingBySource = { lab: true };
        await nextTick();
        expect(wrapper.findAllComponents(LoadingSpan)).toHaveLength(1);
        expect(wrapper.text()).not.toContain("Galaxy has no quota configured");
    });

    it("hides the spinner once the quota usage of its source has loaded", async () => {
        const wrapper = mountQuotaStorage();
        useQuotaUsageStore().loadingBySource = { lab: false };
        await nextTick();
        expect(wrapper.findAllComponents(LoadingSpan)).toHaveLength(0);
        expect(wrapper.text()).not.toContain("Galaxy has no quota configured");
    });

    it("lets badges open interactive popovers unless told otherwise", async () => {
        const wrapper = mountStory(stories.StorageWithId);
        expect(wrapper.findComponent(ObjectStoreBadges).props("interactive")).toBe(true);
        const nonInteractiveWrapper = mountStory(stories.StorageWithId, { props: { interactive: false } });
        expect(nonInteractiveWrapper.findComponent(ObjectStoreBadges).props("interactive")).toBe(false);
    });
});
