import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import MockUserHistories from "components/providers/MockUserHistories";
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
const currentUser = { id: USER_ID };

describe("MultipleView", () => {
    async function setUpWrapper(UserHistoriesMock, count, currentHistoryId) {
        const axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`api/histories/${FIRST_HISTORY_ID}`).reply(200, {});
        const wrapper = mount(MultipleView, {
            pinia: createPinia(),
            stubs: {
                UserHistories: UserHistoriesMock,
                HistoryPanel: true,
                icon: { template: "<div></div>" },
            },
            localVue: getLocalVue(),
        });

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        const historyStore = useHistoryStore();
        historyStore.setHistories(getFakeHistorySummaries(count, 0));
        historyStore.setCurrentHistoryId(currentHistoryId);

        await flushPromises();

        return { wrapper, axiosMock };
    }

    it("more than 4 histories should not show the current history", async () => {
        const count = 8;
        const currentHistoryId = FIRST_HISTORY_ID;

        // Set up UserHistories and wrapper
        const UserHistoriesMock = MockUserHistories({ id: currentHistoryId }, getFakeHistorySummaries(count, 0), false);
        const { wrapper, axiosMock } = await setUpWrapper(UserHistoriesMock, count, currentHistoryId);

        // Test: current (first) history should not be shown because only 4 latest are shown by default
        expect(wrapper.find("button[title='Current History']").exists()).toBeFalsy();

        expect(wrapper.find("button[title='Switch to this history']").exists()).toBeTruthy();

        expect(wrapper.find("div[title='Currently showing 4 most recently updated histories']").exists()).toBeTruthy();

        expect(wrapper.find("[data-description='open select histories modal']").exists()).toBeTruthy();

        axiosMock.reset();
    });

    it("less than or equal to 4 histories should not show the current history", async () => {
        const count = 3;
        const currentHistoryId = FIRST_HISTORY_ID;

        // Set up UserHistories and wrapper
        const UserHistoriesMock = MockUserHistories({ id: currentHistoryId }, getFakeHistorySummaries(count, 0), false);
        const { wrapper, axiosMock } = await setUpWrapper(UserHistoriesMock, count, currentHistoryId);

        // Test: current (first) history should be shown because only 4 latest are shown by default, and count = 3
        expect(wrapper.find("button[title='Current History']").exists()).toBeTruthy();

        axiosMock.reset();
    });
});
