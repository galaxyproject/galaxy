import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { type CleanableItem, CleanableSummary, type CleanupOperation, CleanupResult } from "./model";

import CleanupOperationSummary from "./CleanupOperationSummary.vue";

const localVue = getLocalVue();

const REVIEW_ITEMS_LINK = '[data-test-id="review-link"]';
const NO_ITEMS_INDICATOR = '[data-test-id="no-items-indicator"]';

const EXPECTED_ITEMS: CleanableItem[] = [
    { id: "1", name: "Item 1", size: 512, type: "dataset", update_time: new Date().toISOString() },
    { id: "2", name: "Item 2", size: 512, type: "dataset", update_time: new Date().toISOString() },
];

/** Operation that can clean some items */
const CLEANUP_OPERATION: CleanupOperation = {
    id: "operation-id",
    name: "operation name",
    description: "operation description",
    fetchSummary: async () =>
        new CleanableSummary({
            total_size: 1024,
            total_items: 2,
        }),
    fetchItems: async () => [],
    cleanupItems: async () =>
        new CleanupResult(
            {
                total_item_count: 2,
                success_item_count: 2,
                total_free_bytes: 1024,
                errors: [],
            },
            EXPECTED_ITEMS
        ),
};
/** Operation without items to clean*/
const EMPTY_CLEANUP_OPERATION: CleanupOperation = {
    id: "operation-id-empty",
    name: "empty operation",
    description: "operation that has no items to clean",
    fetchSummary: async () =>
        new CleanableSummary({
            total_size: 0,
            total_items: 0,
        }),
    fetchItems: async () => [],
    cleanupItems: async () => new CleanupResult(),
};
/** Operation that fails on every action */
const ERROR_CLEANUP_OPERATION: CleanupOperation = {
    id: "operation-id-error",
    name: "operation with error",
    description: "operation causing errors",
    fetchSummary: () => {
        throw new Error("Cannot fetch summary");
    },
    fetchItems: () => {
        throw new Error("Cannot fetch items");
    },
    cleanupItems: () => {
        throw new Error("Cannot cleanup items");
    },
};

async function mountCleanupOperationSummaryWith(
    operation: CleanupOperation,
    refreshOperationId = null,
    refreshDelay = 0
) {
    const wrapper = mount(CleanupOperationSummary as object, {
        propsData: { operation, refreshOperationId, refreshDelay },
        localVue,
    });
    await flushPromises();
    await flushPromises();
    return wrapper;
}

describe("CleanupOperationSummary.vue", () => {
    it("should display the operation information", async () => {
        const wrapper = await mountCleanupOperationSummaryWith(CLEANUP_OPERATION);

        expect(wrapper.html()).toContain(CLEANUP_OPERATION.name);
        expect(wrapper.html()).toContain(CLEANUP_OPERATION.description);
    });

    it("should display a link to review items if there are items to be cleaned", async () => {
        const wrapper = await mountCleanupOperationSummaryWith(CLEANUP_OPERATION);

        expect(wrapper.find(REVIEW_ITEMS_LINK).exists()).toBe(true);
    });

    it("should display an indicator when there are no items to review", async () => {
        const wrapper = await mountCleanupOperationSummaryWith(EMPTY_CLEANUP_OPERATION);

        expect(wrapper.find(NO_ITEMS_INDICATOR).exists()).toBe(true);
        expect(wrapper.find(REVIEW_ITEMS_LINK).exists()).toBe(false);
    });

    it("should display an error if the summary information cannot be retrieved", async () => {
        const wrapper = await mountCleanupOperationSummaryWith(ERROR_CLEANUP_OPERATION);

        expect(wrapper.find(REVIEW_ITEMS_LINK).exists()).toBe(false);
        expect(wrapper.html()).toContain("Cannot fetch summary");
    });
});
