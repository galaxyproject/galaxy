import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useHistoryStore } from "@/stores/historyStore";

import * as HistoryPageListStories from "./HistoryPageList.stories";

import GAlert from "@/components/BaseComponents/GAlert.vue";

const stories = composeStories(HistoryPageListStories);
const mountStory = useStoryMount();

const SELECTORS = {
    NEW_BUTTON: "[data-description='create page button']",
    EMPTY_STATE: ".empty-state",
    PAGE_ITEMS: ".page-items",
    PAGE_ITEM: "[data-description='page item']",
};

/** Mounts a story once its history is in the history store, so whether the user owns it is settled. */
async function mountComponent(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    const historyId = story.args.historyId!;
    await vi.waitFor(() => expect(useHistoryStore().getHistoryById(historyId, false)).not.toBeNull());
    await flushPromises();
    return wrapper;
}

type HistoryPageListWrapper = Awaited<ReturnType<typeof mountComponent>>;

describe("HistoryPageList", () => {
    describe("Header", () => {
        let wrapper: HistoryPageListWrapper;

        beforeEach(async () => {
            wrapper = await mountComponent(stories.NoNotebooks);
        });

        it("always shows 'New Notebook' button", () => {
            const button = wrapper.find(SELECTORS.NEW_BUTTON);
            expect(button.exists()).toBe(true);
            expect(button.text()).toContain("New Notebook");
        });
    });

    describe("Empty state", () => {
        let wrapper: HistoryPageListWrapper;

        beforeEach(async () => {
            wrapper = await mountComponent(stories.NoNotebooks);
        });

        it("shows 'No notebooks yet' when pages prop is empty array", () => {
            const emptyState = wrapper.find(SELECTORS.EMPTY_STATE);
            expect(emptyState.exists()).toBe(true);
            expect(emptyState.text()).toContain("No notebooks yet");
        });

        it("shows create guidance text when no pages", () => {
            const emptyState = wrapper.get(SELECTORS.EMPTY_STATE);
            expect(emptyState.text()).toContain("Create a notebook to document your analysis");
        });

        it("does NOT show page items when empty", () => {
            expect(wrapper.find(SELECTORS.PAGE_ITEMS).exists()).toBe(false);
        });
    });

    describe("Page list", () => {
        let wrapper: HistoryPageListWrapper;

        beforeEach(async () => {
            wrapper = await mountComponent(stories.WithNotebooks);
        });

        it("renders each page as a card", () => {
            expect(wrapper.find(SELECTORS.PAGE_ITEMS).exists()).toBe(true);

            const items = wrapper.findAll(SELECTORS.PAGE_ITEM);
            expect(items.length).toBe(2);
        });

        it("does NOT show empty state when pages exist", () => {
            expect(wrapper.find(SELECTORS.EMPTY_STATE).exists()).toBe(false);
        });
    });

    describe("Unowned history alert", () => {
        it("does not show alert when current user owns the history", async () => {
            const wrapper = await mountComponent(stories.NoNotebooks);
            expect(wrapper.findComponent(GAlert).exists()).toBe(false);
        });

        it("shows alert when current user does not own the history", async () => {
            const wrapper = await mountComponent(stories.OtherUsersHistory);
            const alert = wrapper.findComponent(GAlert);
            expect(alert.exists()).toBe(true);
            expect(alert.text()).toContain("You do not own this history");
        });

        it("does not show invocation span in alert when no invocationId", async () => {
            const wrapper = await mountComponent(stories.OtherUsersHistory);
            expect(wrapper.getComponent(GAlert).text()).not.toContain("associated with the invocation");
        });

        it("shows invocation qualifier in alert when invocationId is set", async () => {
            const wrapper = await mountComponent(stories.OtherUsersInvocation);
            expect(wrapper.getComponent(GAlert).text()).toContain("associated with the invocation");
        });

        it("does not show alert when history has no user_id field", async () => {
            const wrapper = await mountComponent(stories.ListedHistory);
            expect(useHistoryStore().getHistoryById(stories.ListedHistory.args.historyId!, false)).not.toHaveProperty(
                "user_id",
            );
            expect(wrapper.findComponent(GAlert).exists()).toBe(false);
        });
    });
});
