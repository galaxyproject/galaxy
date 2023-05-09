import axios from "axios";
import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import MockAdapter from "axios-mock-adapter";
import { getLocalVue } from "tests/jest/helpers";
import MultipleView from "./MultipleView";
import MockUserHistories from "components/providers/MockUserHistories";
import { useUserStore } from "stores/userStore";
import { useHistoryStore } from "stores/historyStore";

const COUNT = 8;
const USER_ID = "test-user-id";
const CURRENT_HISTORY_ID = "test-history-id-0";

const pinia = createPinia();

const getFakeHistorySummaries = (num, selectedIndex) => {
    return Array.from({ length: num }, (_, index) => ({
        id: selectedIndex === index ? CURRENT_HISTORY_ID : `test-history-id-${index}`,
        name: `History-${index}`,
        tags: [],
        update_time: new Date().toISOString(),
    }));
};
const currentUser = { id: USER_ID };
const UserHistoriesMock = MockUserHistories({ id: CURRENT_HISTORY_ID }, getFakeHistorySummaries(COUNT, 0), false);

const localVue = getLocalVue();

describe("MultipleView", () => {
    let wrapper;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = mount(MultipleView, {
            pinia,
            stubs: {
                UserHistories: UserHistoriesMock,
                HistoryPanel: true,
            },
            localVue,
        });

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        const historyStore = useHistoryStore();
        historyStore.setHistories(getFakeHistorySummaries(COUNT, 0));
        historyStore.setCurrentHistoryId(CURRENT_HISTORY_ID);

        await flushPromises();
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("should show the current history", async () => {
        expect(wrapper.find("button[title='Current History']").exists()).toBeTruthy();
    });
});
