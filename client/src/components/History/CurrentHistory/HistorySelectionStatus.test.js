import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import HistorySelectionStatus from "./HistorySelectionStatus.vue";

const localVue = getLocalVue();

const SELECT_ALL_BTN = '[data-test-id="select-all-btn"]';
const CLEAR_BTN = '[data-test-id="clear-btn"]';
const EMPTY_SELECTION_STATUS = '[data-test-id="empty-selection"]';
const ALL_IN_FILTER_SELECTED_STATUS = '[data-test-id="all-filter-selected"]';
const ALL_ACTIVE_SELECTED_STATUS = '[data-test-id="all-active-selected"]';
const NUM_IN_FILTER_SELECTED_STATUS = '[data-test-id="num-filter-selected"]';
const NUM_ACTIVE_SELECTED_STATUS = '[data-test-id="num-active-selected"]';

const NOTHING_SELECTED = {
    hasFilters: false,
    selectionSize: 0,
    totalItemsInQuery: 0,
};

const ONE_ITEM_SELECTED = {
    hasFilters: false,
    selectionSize: 1,
    totalItemsInQuery: 0,
};

const NO_ITEMS_TO_SELECT = {
    hasFilters: false,
    selectionSize: 0,
    totalItemsInQuery: 0,
};

const ALL_ITEMS_SELECTED = {
    hasFilters: false,
    selectionSize: 10,
    totalItemsInQuery: 10,
};

const SOME_ITEMS_IN_QUERY_SELECTED = {
    hasFilters: false,
    selectionSize: 5,
    totalItemsInQuery: 10,
};

async function mountHistorySelectionStatusWith(props) {
    const wrapper = mount(HistorySelectionStatus, { propsData: props }, localVue);
    await flushPromises();
    return wrapper;
}

describe("HistorySelectionStatus", () => {
    describe("Clear Selection Button", () => {
        it("should be only visible when there is something selected", async () => {
            const wrapper = await mountHistorySelectionStatusWith(NOTHING_SELECTED);
            expect(wrapper.find(CLEAR_BTN).exists()).toBe(false);

            await wrapper.setProps({ selectionSize: 1 });
            expect(wrapper.find(CLEAR_BTN).exists()).toBe(true);
        });

        it("should emit the expected event when pressed", async () => {
            const wrapper = await mountHistorySelectionStatusWith(ONE_ITEM_SELECTED);
            await expectWrapperButtonToEmitEvent(wrapper, CLEAR_BTN, "clear-selection");
        });
    });

    describe("Select All Button", () => {
        it("should be only visible when there are items in the current query that are not selected yet", async () => {
            const wrapper = await mountHistorySelectionStatusWith(NO_ITEMS_TO_SELECT);
            expect(wrapper.find(SELECT_ALL_BTN).exists()).toBe(false);

            await wrapper.setProps({ totalItemsInQuery: 1000 });
            expect(wrapper.find(SELECT_ALL_BTN).exists()).toBe(true);
        });

        it("should emit the expected event when pressed", async () => {
            const wrapper = await mountHistorySelectionStatusWith(ONE_ITEM_SELECTED);
            await expectWrapperButtonToEmitEvent(wrapper, SELECT_ALL_BTN, "select-all");
        });
    });

    describe("Selection Status", () => {
        it("should display empty selection status when nothing is selected", async () => {
            const wrapper = await mountHistorySelectionStatusWith(NOTHING_SELECTED);
            expect(wrapper.find(EMPTY_SELECTION_STATUS).exists()).toBe(true);
            expect(wrapper.find(ALL_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);
        });

        it("should display all items selected status when all items in query are selected", async () => {
            const wrapper = await mountHistorySelectionStatusWith(ALL_ITEMS_SELECTED);
            expect(wrapper.find(EMPTY_SELECTION_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_ACTIVE_SELECTED_STATUS).exists()).toBe(true);
            expect(wrapper.find(ALL_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);

            await wrapper.setProps({ hasFilters: true });
            expect(wrapper.find(EMPTY_SELECTION_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_IN_FILTER_SELECTED_STATUS).exists()).toBe(true);
            expect(wrapper.find(NUM_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);
        });

        it("should display number of items selected when some items in query are selected", async () => {
            const wrapper = await mountHistorySelectionStatusWith(SOME_ITEMS_IN_QUERY_SELECTED);
            expect(wrapper.find(EMPTY_SELECTION_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_ACTIVE_SELECTED_STATUS).exists()).toBe(true);
            expect(wrapper.find(NUM_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);

            await wrapper.setProps({ hasFilters: true });
            expect(wrapper.find(EMPTY_SELECTION_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(ALL_IN_FILTER_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_ACTIVE_SELECTED_STATUS).exists()).toBe(false);
            expect(wrapper.find(NUM_IN_FILTER_SELECTED_STATUS).exists()).toBe(true);
        });
    });
});

async function expectWrapperButtonToEmitEvent(wrapper, buttonSelector, expectedEvent) {
    expect(wrapper.emitted()).not.toHaveProperty(expectedEvent);
    await wrapper.find(buttonSelector).trigger("click");
    expect(wrapper.emitted()).toHaveProperty(expectedEvent);
}
