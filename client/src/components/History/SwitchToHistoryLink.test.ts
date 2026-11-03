import { createTestingPinia } from "@pinia/testing";
import { getFakeHistorySummaryExtended, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { HistorySummaryExtended } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type * as HistoryStoreModule from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import SwitchToHistoryLink from "./SwitchToHistoryLink.vue";

enableAutoUnmount(afterEach);
afterEach(() => vi.restoreAllMocks());

const { server, http } = useServerMock();

const selectors = {
    historyLink: ".history-link",
    historyLinkButton: ".history-link-click",
    tooltip: ".g-tooltip",
} as const;

// Click action mocks
const mockSetCurrentHistory = vi.fn();
const mockApplyFilters = vi.fn();
const mockWindowOpen = vi.fn(() => null);
const mockGetHistoryLoadError = vi.fn(() => null as Error | null);

vi.mock("vue-router", () => ({
    useRouter: () => ({
        resolve: (route: string) => ({
            href: `resolved-${route}`,
        }),
    }),
}));

// Mock the history store
vi.mock("@/stores/historyStore", async () => {
    const originalModule = await vi.importActual<typeof HistoryStoreModule>("@/stores/historyStore");
    return {
        ...originalModule,
        useHistoryStore: () => ({
            ...originalModule.useHistoryStore(),
            currentHistoryId: "current-history-id",
            setCurrentHistory: mockSetCurrentHistory,
            getHistoryLoadError: mockGetHistoryLoadError,
            applyFilters: vi.fn().mockImplementation((historyId: string) => {
                // We mock what the actual method does: set the current history if not current
                if (historyId !== "current-history-id") {
                    mockSetCurrentHistory();
                }
                mockApplyFilters();
            }),
        }),
    };
});

// Mock the event store to track ctrlKey presses
vi.mock("@/stores/eventStore", () => {
    return {
        useEventStore: () => ({
            isCtrlKey: vi.fn((event: MouseEvent) => event.ctrlKey),
        }),
    };
});

beforeEach(() => {
    vi.clearAllMocks();
    mockGetHistoryLoadError.mockReturnValue(null);
    vi.spyOn(window, "open").mockImplementation(mockWindowOpen);
});

function mountHistoryLink(history: HistorySummaryExtended, filters?: Record<string, string | boolean>) {
    server.use(http.get("/api/histories/{history_id}", ({ response }) => response(200).json(history)));
    return mountLink(history.id, filters);
}

function mountLink(historyId: string, filters?: Record<string, string | boolean>) {
    const localVue = getLocalVue(true);
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    useUserStore(pinia).currentUser = getFakeRegisteredUser({
        email: "email",
        id: "user_id",
        nice_total_disk_usage: "0 bytes",
        username: "user",
        quota: "abcdef",
    });
    return mount(SwitchToHistoryLink as object, {
        props: { historyId, filters },
        global: withPlugins(localVue, pinia),
        stubs: { FontAwesomeIcon: true },
    });
}

const datasetFilters = { deleted: false, visible: true, hid: "1" };

const actionCases = [
    {
        name: "switches to an active history",
        id: "active-history-id",
        historyName: "History Active",
        tooltip: "Switch to this history",
        switches: 1,
        appliesFilters: 0,
        newTabs: 0,
    },
    {
        name: "switches to an active history and applies filters",
        id: "active-history-id",
        historyName: "History Active",
        filters: datasetFilters,
        tooltip: "Switch to history and view dataset",
        switches: 1,
        appliesFilters: 1,
        newTabs: 0,
    },
    {
        name: "leaves the current history selected",
        id: "current-history-id",
        historyName: "History Current",
        tooltip: "This is your current history",
        switches: 0,
        appliesFilters: 0,
        newTabs: 0,
    },
    {
        name: "applies filters without switching the current history",
        id: "current-history-id",
        historyName: "History Current",
        filters: datasetFilters,
        tooltip: "Switch to history and view dataset",
        switches: 0,
        appliesFilters: 1,
        newTabs: 0,
    },
    {
        name: "opens a purged history in a new tab",
        id: "purged-history-id",
        historyName: "History Purged",
        purged: true,
        tooltip: "View in new tab",
        switches: 0,
        appliesFilters: 0,
        newTabs: 1,
    },
    {
        name: "switches to a purged history and applies filters",
        id: "purged-history-id",
        historyName: "History Purged",
        purged: true,
        filters: datasetFilters,
        tooltip: "Switch to history and view dataset",
        switches: 1,
        appliesFilters: 1,
        newTabs: 0,
    },
    {
        name: "opens an archived history in a new tab",
        id: "archived-history-id",
        historyName: "History Archived",
        archived: true,
        tooltip: "View in new tab",
        switches: 0,
        appliesFilters: 0,
        newTabs: 1,
    },
    {
        name: "switches to an archived history and applies filters",
        id: "archived-history-id",
        historyName: "History Archived",
        archived: true,
        filters: datasetFilters,
        tooltip: "Switch to history and view dataset",
        switches: 1,
        appliesFilters: 1,
        newTabs: 0,
    },
    {
        name: "opens a public history owned by another user in a new tab",
        id: "public-history-id",
        historyName: "History Published",
        published: true,
        user_id: "other_user_id",
        tooltip: "View in new tab",
        switches: 0,
        appliesFilters: 0,
        newTabs: 1,
    },
    {
        name: "opens a public unowned history in a new tab even with filters",
        filters: datasetFilters,
        id: "public-history-id",
        historyName: "History Published",
        published: true,
        user_id: "other_user_id",
        tooltip: "View in new tab",
        switches: 0,
        appliesFilters: 0,
        newTabs: 1,
    },
];

describe("SwitchToHistoryLink", () => {
    it("loads the history information from the store", async () => {
        const history = getFakeHistorySummaryExtended({ id: "history-id-to-load", name: "History Name" });
        const wrapper = mountHistoryLink(history);

        expect(wrapper.find(selectors.historyLink).exists()).toBe(false);
        expect(wrapper.html()).toContain("Loading");

        // Wait for the history to be loaded
        await flushPromises();

        expect(wrapper.find(selectors.historyLink).exists()).toBe(true);
        expect(wrapper.text()).toContain(history.name);
    });

    it.each(actionCases)("$name; Ctrl-click only opens a new tab", async (scenario) => {
        const history = getFakeHistorySummaryExtended({
            id: scenario.id,
            name: scenario.historyName,
            user_id: scenario.user_id ?? "user_id",
            purged: scenario.purged ?? false,
            archived: scenario.archived ?? false,
            published: scenario.published ?? false,
        });
        const wrapper = mountHistoryLink(history, scenario.filters);
        await flushPromises();

        expect(wrapper.get(selectors.tooltip).text()).toBe(scenario.tooltip);
        expect(wrapper.text()).toContain(history.name);

        await wrapper.get(selectors.historyLinkButton).trigger("click");
        expect(mockSetCurrentHistory).toHaveBeenCalledTimes(scenario.switches);
        expect(mockApplyFilters).toHaveBeenCalledTimes(scenario.appliesFilters);
        expect(mockWindowOpen).toHaveBeenCalledTimes(scenario.newTabs);

        await wrapper.get(selectors.historyLinkButton).trigger("click", { ctrlKey: true });
        expect(mockSetCurrentHistory).toHaveBeenCalledTimes(scenario.switches);
        expect(mockApplyFilters).toHaveBeenCalledTimes(scenario.appliesFilters);
        expect(mockWindowOpen).toHaveBeenCalledTimes(scenario.newTabs + 1);
        expect(vi.mocked(window.open)).toHaveBeenLastCalledWith(`resolved-/histories/view?id=${history.id}`, "_blank");
    });

    it("shows an error badge when the history is inaccessible (backend error)", async () => {
        // The history store is fully mocked, so mockGetHistoryLoadError is used to emulate a 403
        mockGetHistoryLoadError.mockReturnValue(new Error("History is not accessible to the current user"));

        const wrapper = mountLink("inaccessible-history-id");

        await flushPromises();

        expect(wrapper.find(selectors.historyLink).exists()).toBe(false);
        expect(wrapper.html()).toContain("Error loading history");
        expect(wrapper.html()).not.toContain("Loading");
    });
});
