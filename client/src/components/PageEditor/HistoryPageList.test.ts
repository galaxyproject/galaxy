import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { setupMockHistoryBreadcrumbs } from "@tests/vitest/mockHistoryBreadcrumbs";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HistoryPageSummary } from "@/api/pages";

import { FAKE_PAGE_SUMMARY, FAKE_PAGE_UNTITLED } from "./testData";

import HistoryPageList from "./HistoryPageList.vue";

const localVue = getLocalVue();

const SELECTORS = {
    NEW_BUTTON: "[data-description='create page button']",
    EMPTY_STATE: ".empty-state",
    PAGE_ITEMS: ".page-items",
    PAGE_ITEM: "[data-description='page item']",
    UNOWNED_ALERT: "balert-stub",
};

setupMockHistoryBreadcrumbs();

// Mocks for store methods
const mockGetHistoryById = vi.fn();
const mockMatchesCurrentUserId = vi.fn();

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: vi.fn(() => ({
        getHistoryById: mockGetHistoryById,
    })),
}));

vi.mock("@/stores/userStore", () => ({
    useUserStore: vi.fn(() => ({
        matchesCurrentUserId: mockMatchesCurrentUserId,
    })),
}));

async function mountComponent(propsData: { pages: HistoryPageSummary[]; invocationId?: string }) {
    const wrapper = shallowMount(HistoryPageList as object, {
        localVue,
        propsData: { ...propsData, historyId: "history-1" },
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryPageList", () => {
    beforeEach(() => {
        // Default: history is owned by the current user, no alert shown
        mockGetHistoryById.mockReturnValue({ id: "history-1", name: "Test History", user_id: "user-1" });
        mockMatchesCurrentUserId.mockReturnValue(true);
    });

    describe("Header", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({ pages: [] });
        });

        it("always shows 'New Notebook' button", () => {
            const button = wrapper.find(SELECTORS.NEW_BUTTON);
            expect(button.exists()).toBe(true);
            expect(button.text()).toContain("New Notebook");
        });
    });

    describe("Empty state", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({ pages: [] });
        });

        it("shows 'No notebooks yet' when pages prop is empty array", () => {
            const emptyState = wrapper.find(SELECTORS.EMPTY_STATE);
            expect(emptyState.exists()).toBe(true);
            expect(emptyState.text()).toContain("No notebooks yet");
        });

        it("shows create guidance text when no pages", () => {
            const emptyState = wrapper.find(SELECTORS.EMPTY_STATE);
            expect(emptyState.text()).toContain("Create a notebook to document your analysis");
        });

        it("does NOT show page items when empty", () => {
            expect(wrapper.find(SELECTORS.PAGE_ITEMS).exists()).toBe(false);
        });
    });

    describe("Page list", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({
                pages: [FAKE_PAGE_SUMMARY, FAKE_PAGE_UNTITLED],
            });
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
            const wrapper = await mountComponent({ pages: [] });
            expect(wrapper.find(SELECTORS.UNOWNED_ALERT).exists()).toBe(false);
        });

        it("shows alert when current user does not own the history", async () => {
            mockMatchesCurrentUserId.mockReturnValue(false);
            const wrapper = await mountComponent({ pages: [] });
            const alert = wrapper.find(SELECTORS.UNOWNED_ALERT);
            expect(alert.exists()).toBe(true);
            expect(alert.text()).toContain("You do not own this history");
        });

        it("does not show invocation span in alert when no invocationId", async () => {
            mockMatchesCurrentUserId.mockReturnValue(false);
            const wrapper = await mountComponent({ pages: [] });
            expect(wrapper.find(SELECTORS.UNOWNED_ALERT).text()).not.toContain("associated with the invocation");
        });

        it("shows invocation qualifier in alert when invocationId is set", async () => {
            mockMatchesCurrentUserId.mockReturnValue(false);
            const wrapper = await mountComponent({ pages: [], invocationId: "inv-1" });
            expect(wrapper.find(SELECTORS.UNOWNED_ALERT).text()).toContain("associated with the invocation");
        });

        it("does not show alert when history has no user_id field", async () => {
            mockGetHistoryById.mockReturnValue({ id: "history-1", name: "Test History" });
            const wrapper = await mountComponent({ pages: [] });
            expect(wrapper.find(SELECTORS.UNOWNED_ALERT).exists()).toBe(false);
        });
    });
});
