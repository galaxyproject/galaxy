import { mount } from "@vue/test-utils";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import store from "@/store";
import Gantt from "./Gantt.vue";
import DateTimeModal from "./DateTimeModal.vue";
import MockCurrentUser from "components/providers/MockCurrentUser";
import MockUserHistories from "components/providers/MockUserHistories";

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

const CurrentUserMock = MockCurrentUser({ id: USER_ID });
const UserHistoriesMock = MockUserHistories({ id: CURRENT_HISTORY_ID }, getFakeHistorySummaries(COUNT, 0), false);

const localVue = getLocalVue();

describe("gantt component", () => {
    let wrapper;
    let Modal;

    beforeEach(async () => {
        wrapper = shallowMount(Gantt, {
            store,
            pinia,
            stubs: {
                CurrentUser: CurrentUserMock,
                UserHistories: UserHistoriesMock,
            },
            localVue,
        });
        await flushPromises();
        Modal = mount(DateTimeModal);
    });

    it("7 change view buttons should be visible", () => {
        expect(wrapper.findAll('[data-description="change view button"]').length).toBe(7);
    });

    it("Date Time modal should be visible after clicking on Minute View", async () => {
        expect(wrapper.vm.openModal).toBe(false);
        await wrapper.setData({ openModal: true });
        expect(wrapper.vm.openModal).toBe(true);
        expect(Modal.find("#dateTimeModal").exists()).toBe(true);
        const mod = wrapper.findComponent(DateTimeModal);
        expect(mod.isVisible()).toBe(true);
    });

    it("Date Time modal should be closed when its open and clicked on confirm date", async () => {
        expect(wrapper.vm.openModal).toBe(false);
        await wrapper.setData({ openModal: true });
        expect(wrapper.vm.openModal).toBe(true);
        expect(Modal.find("#dateTimeModal").exists()).toBe(true);
        const mod = wrapper.findComponent(DateTimeModal);
        expect(mod.isVisible()).toBe(true);
        await wrapper.setData({ openModal: false });
        expect(mod.isVisible()).toBe(false);
    });
});
