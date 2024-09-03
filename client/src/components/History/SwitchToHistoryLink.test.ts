import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";

import { type HistorySummaryExtended } from "@/api";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import SwitchToHistoryLink from "./SwitchToHistoryLink.vue";

jest.mock("@/composables/toast", () => ({
    Toast: {
        error: jest.fn(),
    },
}));
jest.mock("vue-router/composables", () => ({
    useRouter: jest.fn(() => ({
        resolve: jest.fn((route) => ({
            href: route,
        })),
    })),
}));

const localVue = getLocalVue(true);

const selectors = {
    historyLink: ".history-link",
    historyLinkClick: ".history-link > a",
} as const;

function mountSwitchToHistoryLinkForHistory(history: HistorySummaryExtended) {
    const windowSpy = jest.spyOn(window, "open");
    windowSpy.mockImplementation(() => null);
    const pinia = createTestingPinia();

    const axiosMock = new MockAdapter(axios);
    axiosMock.onGet(`/api/histories/${history.id}`).reply(200, history);

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
        tags_used: [],
        isAnonymous: false,
        total_disk_usage: 0,
    };
    return wrapper;
}

async function expectOptionForHistory(option: string, history: HistorySummaryExtended) {
    const wrapper = mountSwitchToHistoryLinkForHistory(history);

    // Wait for the history to be loaded
    await flushPromises();

    expect(wrapper.html()).toContain(option);
    expect(wrapper.text()).toContain(history.name);

    return wrapper;
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

    it("should view in new tab when the history is unowned and published", async () => {
        const history = {
            id: "unowned-history-id",
            name: "History Published",
            deleted: false,
            purged: false,
            archived: false,
            published: true,
            user_id: "other_user_id",
        } as HistorySummaryExtended;
        const wrapper = await expectOptionForHistory("View", history);

        // Wait for the history to be loaded
        await flushPromises();

        // Click on the history link
        const link = wrapper.find(selectors.historyLinkClick);
        await link.trigger("click");
        await wrapper.vm.$nextTick();

        // History opens in a new tab
        expect(Toast.error).toHaveBeenCalledTimes(0);
    });

    it("should display View option and show error on click when history is unowned and not published", async () => {
        const history = {
            id: "published-history-id",
            name: "History Unowned",
            deleted: false,
            purged: false,
            archived: false,
            user_id: "other_user_id",
        } as HistorySummaryExtended;
        const wrapper = await expectOptionForHistory("View", history);

        // Wait for the history to be loaded
        await flushPromises();

        // Click on the history link
        const link = wrapper.find(selectors.historyLinkClick);
        await link.trigger("click");
        await wrapper.vm.$nextTick();

        // History does not open in a new tab and we get a Toast error
        expect(Toast.error).toHaveBeenCalledTimes(1);
        expect(Toast.error).toHaveBeenCalledWith("You do not have permission to view this history.");
    });
});
