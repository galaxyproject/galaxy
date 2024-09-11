import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { type HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import SwitchToHistoryLink from "./SwitchToHistoryLink.vue";

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

const selectors = {
    historyLink: ".history-link",
} as const;

function mountSwitchToHistoryLinkForHistory(history: HistorySummary) {
    const pinia = createTestingPinia();

    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => {
            return response(200).json(history);
        })
    );

    const wrapper = shallowMount(SwitchToHistoryLink as object, {
        propsData: {
            historyId: history.id,
        },
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
    return wrapper;
}

async function expectOptionForHistory(option: string, history: HistorySummary) {
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
        } as HistorySummary;
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
        } as HistorySummary;
        await expectOptionForHistory("Switch", history);
    });

    it("should display the View option when the history is purged", async () => {
        const history = {
            id: "purged-history-id",
            name: "History Purged",
            deleted: false,
            purged: true,
            archived: false,
        } as HistorySummary;
        await expectOptionForHistory("View", history);
    });

    it("should display the View option when the history is archived", async () => {
        const history = {
            id: "archived-history-id",
            name: "History Archived",
            deleted: false,
            purged: false,
            archived: true,
        } as HistorySummary;
        await expectOptionForHistory("View", history);
    });
});
