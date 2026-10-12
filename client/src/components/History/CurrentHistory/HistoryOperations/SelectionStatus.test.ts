import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import HistorySelectionStatus from "./SelectionStatus.vue";

const localVue = getLocalVue();

const SELECT_ALL_BTN = '[data-test-id="select-all-btn"]';
const CLEAR_BTN = '[data-test-id="clear-btn"]';

function mountSelectionStatus(selectionSize: number) {
    return mount(HistorySelectionStatus, {
        props: { selectionSize },
        global: localVue,
    });
}

enableAutoUnmount(afterEach);

describe("History SelectionStatus", () => {
    describe("Clear selection", () => {
        it("appears when the selection changes from empty to one item", async () => {
            const wrapper = mountSelectionStatus(0);
            expect(wrapper.find(CLEAR_BTN).exists()).toBe(false);

            await wrapper.setProps({ selectionSize: 1 });
            expect(wrapper.find(CLEAR_BTN).exists()).toBe(true);
        });

        it("emits reset-selection when clicked with one item selected", async () => {
            const wrapper = mountSelectionStatus(1);
            expect(wrapper.emitted()).not.toHaveProperty("reset-selection");

            await wrapper.get(CLEAR_BTN).trigger("click");

            expect(wrapper.emitted()).toHaveProperty("reset-selection");
        });
    });

    describe("Select all", () => {
        it("appears when the selection changes from one item to empty", async () => {
            const wrapper = mountSelectionStatus(1);
            expect(wrapper.find(SELECT_ALL_BTN).exists()).toBe(false);

            await wrapper.setProps({ selectionSize: 0 });
            expect(wrapper.find(SELECT_ALL_BTN).exists()).toBe(true);
        });

        it("emits select-all when clicked with an empty selection", async () => {
            const wrapper = mountSelectionStatus(0);
            expect(wrapper.emitted()).not.toHaveProperty("select-all");

            await wrapper.get(SELECT_ALL_BTN).trigger("click");

            expect(wrapper.emitted()).toHaveProperty("select-all");
        });
    });
});
