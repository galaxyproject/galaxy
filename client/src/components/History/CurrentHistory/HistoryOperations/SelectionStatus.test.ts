import { mount, shallowMount, VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import HistorySelectionStatus from "./SelectionStatus.vue";

const { global } = getLocalVue();

const SELECT_ALL_BTN = '[data-test-id="select-all-btn"]';
const CLEAR_BTN = '[data-test-id="clear-btn"]';

const NOTHING_SELECTED = {
    selectionSize: 0,
};

const SOMETHING_SELECTED = {
    selectionSize: 1,
};

async function mountHistorySelectionStatusWith(props: Record<string, any>) {
    const wrapper = mount(HistorySelectionStatus as any, {
        props: props,
        global,
    });

    await flushPromises();

    return wrapper;
}

async function expectWrapperButtonToEmitEvent(wrapper: VueWrapper<any>, buttonSelector: string, expectedEvent: string) {
    expect(wrapper.emitted()).not.toHaveProperty(expectedEvent);
    await wrapper.find(buttonSelector).trigger("click");
    expect(wrapper.emitted()).toHaveProperty(expectedEvent);
}

describe("History SelectionStatus", () => {
    describe("Clear Selection Button", () => {
        it("should be only visible when there is something selected", async () => {
            const wrapper = await mountHistorySelectionStatusWith(NOTHING_SELECTED);
            expect(wrapper.find(CLEAR_BTN).exists()).toBe(false);

            await (wrapper as any).setProps({ selectionSize: 1 });
            expect(wrapper.find(CLEAR_BTN).exists()).toBe(true);
        });

        it("should emit the expected event when pressed", async () => {
            const wrapper = await mountHistorySelectionStatusWith(SOMETHING_SELECTED);
            await expectWrapperButtonToEmitEvent(wrapper, CLEAR_BTN, "reset-selection");
        });
    });

    describe("Select All Button", () => {
        it("should be only visible when there is nothing selected yet", async () => {
            const wrapper = await mountHistorySelectionStatusWith(SOMETHING_SELECTED);
            expect(wrapper.find(SELECT_ALL_BTN).exists()).toBe(false);

            await (wrapper as any).setProps(NOTHING_SELECTED);
            expect(wrapper.find(SELECT_ALL_BTN).exists()).toBe(true);
        });

        it("should emit the expected event when pressed", async () => {
            const wrapper = await mountHistorySelectionStatusWith(NOTHING_SELECTED);
            await expectWrapperButtonToEmitEvent(wrapper, SELECT_ALL_BTN, "select-all");
        });
    });
});
