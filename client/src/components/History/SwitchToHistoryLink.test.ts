import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";

import type { HistorySummaryExtended } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import SwitchToHistoryLink from "./SwitchToHistoryLink.vue";

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

const selectors = {
    historyLink: ".history-link",
    historyLinkButton: ".history-link-click",
    tooltip: ".g-tooltip",
} as const;

// Click action mocks
const mockSetCurrentHistory = jest.fn();
const mockApplyFilters = jest.fn();
const mockWindowOpen = jest.fn(() => null);

jest.mock("vue-router/composables", () => ({
    useRouter: () => ({
        resolve: (route: string) => ({
            href: `resolved-${route}`,
        }),
    }),
}));

// Mock the history store
jest.mock("@/stores/historyStore", () => {
    const originalModule = jest.requireActual("@/stores/historyStore");
    return {
        ...originalModule,
        useHistoryStore: () => ({
            ...originalModule.useHistoryStore(),
            currentHistoryId: "current-history-id",
            setCurrentHistory: mockSetCurrentHistory,
            applyFilters: jest.fn().mockImplementation((historyId: string) => {
                // We mock what the actual method does: set the current history if not current
                if (historyId !== "current-history-id") {
                    mockSetCurrentHistory();
                }
                mockApplyFilters();
            }),
        }),
    };
});

/** Clear up and initialize all mocks for the jest. */
function initializeMocks() {
    mockSetCurrentHistory.mockClear();
    mockApplyFilters.mockClear();
    mockWindowOpen.mockClear();
    const windowSpy = jest.spyOn(window, "open");
    windowSpy.mockImplementation(() => mockWindowOpen());
}

/** Mock `<SwitchToHistoryLink>` component for testing.
 * @param history - The history to be mocked
 * @param hasFilters - Whether the component has the `filters` prop (generates sample filters)
 */
function mountSwitchToHistoryLinkForHistory(history: HistorySummaryExtended, hasFilters = false) {
    initializeMocks();

    const pinia = createTestingPinia();

    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => {
            return response(200).json(history);
        })
    );

    const filters = hasFilters ? { deleted: false, visible: true, hid: "1" } : undefined;

    const wrapper = mount(SwitchToHistoryLink as object, {
        propsData: {
            historyId: history.id,
            filters,
        },
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    const userStore = useUserStore();
    userStore.currentUser = {
        email: "email",
        id: "user_id",
        isAnonymous: false,
        total_disk_usage: 0,
        nice_total_disk_usage: "0 bytes",
        purged: false,
        deleted: false,
        is_admin: false,
        username: "user",
        preferences: {},
        quota: "abcdef",
    };
    return wrapper;
}

/**
 * This function expects a specific action to be taken based on the provided history's properties.
 * @param tooltip What tooltip text to expect
 * @param history The history object to test (with variations like `deleted`, `archived`, etc.)
 * @param opensInNewTab Whether the history should open in a new tab on click
 * @param hasFilters Whether the `SwitchToHistoryLink` has a `filters` prop
 * @param setsCurrentHistory Whether we set the current history on click
 * @param setsFilters Whether filters are applied to the current history on click
 */
async function expectActionForHistory(
    tooltip: "Switch to this history" | "This is your current history" | "View in new tab" | "Show in history",
    history: HistorySummaryExtended,
    opensInNewTab = false,
    hasFilters = false,
    setsCurrentHistory = false,
    setsFilters = false
) {
    const wrapper = mountSwitchToHistoryLinkForHistory(history, hasFilters);

    // Wait for the history to be loaded
    await flushPromises();

    expect(wrapper.find(selectors.tooltip).text()).toEqual(tooltip);
    expect(wrapper.text()).toContain(history.name);

    await wrapper.find(selectors.historyLinkButton).trigger("click");

    expect(mockSetCurrentHistory).toHaveBeenCalledTimes(setsCurrentHistory ? 1 : 0);
    expect(mockApplyFilters).toHaveBeenCalledTimes(setsFilters ? 1 : 0);
    expect(mockWindowOpen).toHaveBeenCalledTimes(opensInNewTab ? 1 : 0);
}

describe("SwitchToHistoryLink", () => {
    it("loads the history information from the store", async () => {
        const history = {
            id: "history-id-to-load",
            name: "History Name",
            deleted: false,
            archived: false,
            purged: false,
        } as HistorySummaryExtended;
        const wrapper = mountSwitchToHistoryLinkForHistory(history);

        expect(wrapper.find(selectors.historyLink).exists()).toBe(false);
        expect(wrapper.html()).toContain("Loading");

        // Wait for the history to be loaded
        await flushPromises();

        expect(wrapper.find(selectors.historyLink).exists()).toBe(true);
        expect(wrapper.text()).toContain(history.name);
    });

    it("sets current history or applies filters if the history can be switched to", async () => {
        const history = {
            id: "active-history-id",
            name: "History Active",
            deleted: false,
            purged: false,
            archived: false,
            user_id: "user_id",
        } as HistorySummaryExtended;

        // We switch to this history
        await expectActionForHistory("Switch to this history", history, false, false, true, false);

        // Since history was not current, we switch to it AND apply filters
        await expectActionForHistory("Show in history", history, false, true, true, true);
    });

    it("only applies filters when the history is the Current history", async () => {
        const history = {
            id: "current-history-id",
            name: "History Current",
            deleted: false,
            purged: false,
            archived: false,
            user_id: "user_id",
        } as HistorySummaryExtended;

        // We do nothing since the history is already current
        await expectActionForHistory("This is your current history", history);

        // Since history is already current, we only apply filters
        await expectActionForHistory("Show in history", history, false, true, false, true);
    });

    it("opens purged history in new tab or applies filters", async () => {
        const history = {
            id: "purged-history-id",
            name: "History Purged",
            deleted: false,
            purged: true,
            archived: false,
            user_id: "user_id",
        } as HistorySummaryExtended;

        // We view the purged history in a new tab
        await expectActionForHistory("View in new tab", history, true);

        // We switch to the purged history and apply filters
        await expectActionForHistory("Show in history", history, false, true, true, true);
    });

    it("opens archived history in new tab or applies filters", async () => {
        const history = {
            id: "archived-history-id",
            name: "History Archived",
            deleted: false,
            purged: false,
            archived: true,
            user_id: "user_id",
        } as HistorySummaryExtended;

        // We view the archived history in a new tab
        await expectActionForHistory("View in new tab", history, true);

        // We switch to the archived history and apply filters
        await expectActionForHistory("Show in history", history, false, true, true, true);
    });

    it("only opens an accessible unowned history in new tab", async () => {
        const history = {
            id: "public-history-id",
            name: "History Published",
            deleted: false,
            purged: false,
            archived: false,
            published: true,
            user_id: "other_user_id",
        } as HistorySummaryExtended;

        // We view the accessible (but other user's) history in a new tab
        await expectActionForHistory("View in new tab", history, true);

        // Since the history isn't owned, we can't switch to it and apply filters; so we just view it in a new tab
        await expectActionForHistory("View in new tab", history, true);
    });

    // if the history is inaccessible, the HistorySummary would never be fetched in the first place
});
