import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue, mockModule } from "tests/jest/helpers";
import MultipleView from "./MultipleView";
import MockUserHistories from "components/providers/MockUserHistories";
import Vuex from "vuex";
import { useUserStore } from "stores/userStore";
import { historyStore } from "store/historyStore";

const COUNT = 8;
const USER_ID = "test-user-id";
const CURRENT_HISTORY_ID = "test-history-id-0";

const pinia = createPinia();

const getFakeHistorySummaries = (num, selectedIndex = 0) => {
    const result = Array.from({ length: num }, (_, index) => ({
        id: `test-history-id-${index}`,
        name: `History-${index}`,
        tags: [],
        update_time: new Date().toISOString(),
    }));
    result[selectedIndex].id = CURRENT_HISTORY_ID;
    return result;
};
const currentUser = { id: USER_ID };
const UserHistoriesMock = MockUserHistories({ id: CURRENT_HISTORY_ID }, getFakeHistorySummaries(COUNT, 0), false);

const localVue = getLocalVue();

describe("MultipleView", () => {
    let wrapper;

    beforeEach(async () => {
        const store = new Vuex.Store({
            modules: {
                history: mockModule(historyStore, {
                    currentHistoryId: CURRENT_HISTORY_ID,
                    currentHistory: { id: CURRENT_HISTORY_ID },
                    histories: getFakeHistorySummaries(COUNT, 0).reduce((acc, curr, index) => {
                        acc[curr.id] = curr;
                        return acc;
                    }, {}),
                    historiesLoading: false,
                    handlers: {},
                }),
            },
        });

        wrapper = mount(MultipleView, {
            store,
            pinia,
            stubs: {
                UserHistories: UserHistoriesMock,
                HistoryPanel: true,
            },
            localVue,
        });

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        await flushPromises();
    });

    it("should show the current history", async () => {
        expect(wrapper.find("button[title='Current History']").exists()).toBeTruthy();
    });
});
