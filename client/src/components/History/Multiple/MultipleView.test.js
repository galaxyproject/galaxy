import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import MultipleView from "./MultipleView";
import MockCurrentUser from "components/providers/MockCurrentUser";
import MockUserHistories from "components/providers/MockUserHistories";
import store from "store/index";

const COUNT = 8;
const USER_ID = "test-user-id";
const CURRENT_HISTORY_ID = "test-history-id-0";

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

const CurrentUserMock = MockCurrentUser({ id: USER_ID });
const UserHistoriesMock = MockUserHistories({ id: CURRENT_HISTORY_ID }, getFakeHistorySummaries(COUNT, 0), false);

const localVue = getLocalVue();

describe("MultipleView", () => {
    let wrapper;

    beforeEach(async () => {
        wrapper = mount(MultipleView, {
            store,
            stubs: {
                CurrentUser: CurrentUserMock,
                UserHistories: UserHistoriesMock,
                HistoryPanel: true,
            },
            localVue,
        });
        await flushPromises();
    });

    it("should show the current history", async () => {
        expect(wrapper.find("button[title='Current History']").exists()).toBeTruthy();
    });
});
