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
        //const button = wrapper.find("#minuteView");
        //console.log(button);
        //await button.trigger("click");
        //expect(wrapper.find("DateTimeModal").exists()).toBe(false);
        //await Vue.nextTick();
        expect(wrapper.vm.openModal).toBe(false);
        await wrapper.setData({ openModal: true });
        //await Vue.nextTick();
        //console.log(wrapper.vm.openModal);
        expect(wrapper.vm.openModal).toBe(true);
        //const modal = wrapper.findComponent(DateTimeModal); // => finds Bar by component instance
        expect(Modal.find("#dateTimeModal").exists()).toBe(true);
        //await Vue.nextTick();
        const mod = wrapper.findComponent(DateTimeModal);
        //console.log(mod);
        expect(mod.isVisible()).toBe(true);
        //expect(wrapper.find("#dateTimeModal").exists()).toBe(true);
    });

    it("Date Time modal should be closed when its open and clicked on confirm date", async () => {
        //const minuteViewButton = wrapper.find("#minuteView");
        //await minuteViewButton.trigger("click");
        // const confirmDateButton = modal.find("#confirmDate");
        // expect(wrapper.contains(modal)).toBe(true);
        // await confirmDateButton.trigger("click");
        // expect(wrapper.contains(modal)).toBe(false);
        //expect(wrapper.contains("#dateTimeModal")).toBe(true);
        //expect(wrapper.contains(DateTimeModal)).toBe(true);
        //await Vue.nextTick();
        //const modal = wrapper.findComponent(DateTimeModal); // => finds Bar by component instance
        //expect(modal.exists()).toBe(true);
        // const modal = wrapper.find("#dateTimeModal");

        // expect(modal.isVisible()).toBe(false);
        // await minuteViewButton.trigger("click");

        // expect(modal.isVisible()).toBe(true);
        expect(wrapper.vm.openModal).toBe(false);
        await wrapper.setData({ openModal: true });
        expect(wrapper.vm.openModal).toBe(true);
        expect(Modal.find("#dateTimeModal").exists()).toBe(true);
        const mod = wrapper.findComponent(DateTimeModal);
        //console.log(mod);
        expect(mod.isVisible()).toBe(true);
        await wrapper.setData({ openModal: false });
        expect(mod.isVisible()).toBe(false);
    });
});
