import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import store from "@/store";
import Gantt from "./Gantt.vue";
import MockCurrentUser from "components/providers/MockCurrentUser";
import MockUserHistories from "components/providers/MockUserHistories";
import moment from 'moment';

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

const getFakeAccountingArray = (num) => {
    const accountingArray = [];
    for (let i = 0; i < num; i++) {
        var startDate = moment(new Date()).format("YYYY-MM-DD HH:mm:ss");
        accountingArray.push({
            id: i.toString(),
            label: `job-${i}`,
            startTime: startDate,
            endTime: moment(startDate).add(10, "minutes").format("YYYY-MM-DD HH:mm:ss"),
        });
    }
    console.log(accountingArray);
    return accountingArray;
};

const PROPS_WITH_5_JOBS = {
    accountingArray : getFakeAccountingArray( 5 )
};

const CurrentUserMock = MockCurrentUser({ id: USER_ID });
const UserHistoriesMock = MockUserHistories({ id: CURRENT_HISTORY_ID }, getFakeHistorySummaries(COUNT, 0), false);

const localVue = getLocalVue();

describe("gantt component", () => {
    let wrapper;

    beforeEach(async () => {
        wrapper = shallowMount(Gantt, {
            store,
            pinia,
            propsData : PROPS_WITH_5_JOBS,
            stubs: {
                CurrentUser: CurrentUserMock,
                UserHistories: UserHistoriesMock,
            },
            localVue,
        });
        await flushPromises();
    });

    it("7 change view buttons should be visible", () => {
        expect(wrapper.findAll('[data-description="change view button"]').length).toBe(7);
    });

    it("chech rows", async () =>{
        console.log(wrapper.attributes());
        const row = wrapper.find('.grid-row');
        console.log(row);
        expect(wrapper.findAll('.grid-row').length).toBe(5);
    })
});
