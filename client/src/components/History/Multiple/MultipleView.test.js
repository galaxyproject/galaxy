import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { useHistoryStore } from "stores/historyStore";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

import MultipleView from "./MultipleView";

const USER_ID = "test-user-id";
const FIRST_HISTORY_ID = "test-history-id-0";

const getFakeHistorySummaries = (num, selectedIndex) => {
    return Array.from({ length: num }, (_, index) => ({
        id: `test-history-id-${index}`,
        name: `History-${index}`,
        tags: [],
        update_time: new Date().toISOString(),
    }));
};

const currentUser = getFakeRegisteredUser({ id: USER_ID });

describe("MultipleView", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.reset();
    });

    async function setUpWrapper(count, currentHistoryId) {
        const fakeSummaries = getFakeHistorySummaries(count, 0);
        for (const summary of fakeSummaries) {
            axiosMock.onGet(`api/histories/${summary.id}`).reply(200, summary);
        }
        const wrapper = mount(MultipleView, {
            pinia: createPinia(),
            stubs: {
                HistoryPanel: true,
                icon: { template: "<div></div>" },
            },
            localVue: getLocalVue(),
        });

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        const historyStore = useHistoryStore();
        historyStore.setHistories(fakeSummaries);
        historyStore.setCurrentHistoryId(currentHistoryId);

        await flushPromises();

        return wrapper;
    }

    it("more than 4 histories should not show the current history", async () => {
        const count = 8;
        const currentHistoryId = FIRST_HISTORY_ID;

        // Set up UserHistories and wrapper
        const wrapper = await setUpWrapper(count, currentHistoryId);

        console.log(wrapper.html());

        // Test: current (first) history should not be shown because only 4 latest are shown by default
        expect(wrapper.find("button[title='Current History']").exists()).toBeFalsy();

        expect(wrapper.find("button[title='Switch to this history']").exists()).toBeTruthy();

        expect(wrapper.find("div[title='Currently showing 4 most recently updated histories']").exists()).toBeTruthy();

        expect(wrapper.find("[data-description='open select histories modal']").exists()).toBeTruthy();
    });

    it("less than 4 histories should show the current history", async () => {
        const count = 3;
        const currentHistoryId = FIRST_HISTORY_ID;

        // Set up UserHistories and wrapper
        const wrapper = await setUpWrapper(count, currentHistoryId);

        // Test: current (first) history should be shown because only 4 latest are shown by default, and count = 3
        expect(wrapper.find("button[title='Current History']").exists()).toBeTruthy();
    });
});
