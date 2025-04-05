import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { type HistorySummaryExtended } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import SwitchToHistoryLink from "./SwitchToHistoryLink.vue";

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

const selectors = {
    historyLink: ".history-link",
} as const;

// Mock the history store to always return the same current history id
jest.mock("@/stores/historyStore", () => {
    const originalModule = jest.requireActual("@/stores/historyStore");
    return {
        ...originalModule,
        useHistoryStore: () => ({
            ...originalModule.useHistoryStore(),
            currentHistoryId: "current-history-id",
        }),
    };
});

function mountSwitchToHistoryLinkForHistory(history: HistorySummaryExtended) {
    const pinia = createTestingPinia();

    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => {
            return response(200).json(history);
        })
    );

    const wrapper = mount(SwitchToHistoryLink as object, {
        propsData: {
            historyId: history.id,
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

async function expectOptionForHistory(option: string, history: HistorySummaryExtended) {
    const wrapper = mountSwitchToHistoryLinkForHistory(history);

    // Wait for the history to be loaded
    await flushPromises();

    expect(wrapper.html()).toContain(option);
    expect(wrapper.text()).toContain(history.name);
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

    it("should display the Switch option when the history can be switched to", async () => {
        const history = {
            id: "active-history-id",
            name: "History Active",
            deleted: false,
            purged: false,
            archived: false,
            user_id: "user_id",
        } as HistorySummaryExtended;
        await expectOptionForHistory("Switch", history);
    });

    it("should display the appropriate text when the history is the Current history", async () => {
        const history = {
            id: "current-history-id",
            name: "History Current",
            deleted: false,
            purged: false,
            archived: false,
            user_id: "user_id",
        } as HistorySummaryExtended;
        await expectOptionForHistory("This is your current history", history);
    });

    it("should display the View option when the history is purged", async () => {
        const history = {
            id: "purged-history-id",
            name: "History Purged",
            deleted: false,
            purged: true,
            archived: false,
            user_id: "user_id",
        } as HistorySummaryExtended;
        await expectOptionForHistory("View", history);
    });

    it("should display the View option when the history is archived", async () => {
        const history = {
            id: "archived-history-id",
            name: "History Archived",
            deleted: false,
            purged: false,
            archived: true,
            user_id: "user_id",
        } as HistorySummaryExtended;
        await expectOptionForHistory("View", history);
    });

    it("should view in new tab when the history is accessible", async () => {
        const history = {
            id: "public-history-id",
            name: "History Published",
            deleted: false,
            purged: false,
            archived: false,
            published: true,
            user_id: "other_user_id",
        } as HistorySummaryExtended;
        await expectOptionForHistory("View", history);
    });

    // if the history is inaccessible, the HistorySummary would never be fetched in the first place
});
