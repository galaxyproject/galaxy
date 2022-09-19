import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import CleanupOperationSummary from "./CleanupOperationSummary";
import { CleanableSummary, CleanupOperation, CleanupResult } from "./model";

const localVue = getLocalVue();

const REVIEW_ITEMS_LINK = '[data-test-id="review-link"]';
const NO_ITEMS_INDICATOR = '[data-test-id="no-items-indicator"]';

/** Operation that can clean some items */
const CLEANUP_OPERATION = new CleanupOperation({
    id: "operation-id",
    name: "operation name",
    description: "operation description",
    fetchSummary: () =>
        new CleanableSummary({
            totalSize: 1024,
            totalItems: 2,
        }),
    fetchItems: () => [],
    cleanupItems: (items) =>
        new CleanupResult({
            totalItemCount: 2,
            totalFreeBytes: 1024,
        }),
});
/** Operation without items to clean*/
const EMPTY_CLEANUP_OPERATION = new CleanupOperation({
    id: "operation-id-empty",
    name: "empty operation",
    description: "operation that has no items to clean",
    fetchSummary: () =>
        new CleanableSummary({
            totalSize: 0,
            totalItems: 0,
        }),
    fetchItems: () => [],
    cleanupItems: (items) => null,
});
/** Operation that fails on every action */
const ERROR_CLEANUP_OPERATION = new CleanupOperation({
    id: "operation-id-error",
    name: "operation with error",
    description: "operation causing errors",
    fetchSummary: () => {
        throw new Error("Cannot fetch summary");
    },
    fetchItems: () => {
        throw new Error("Cannot fetch items");
    },
    cleanupItems: (items) => {
        throw new Error("Cannot cleanup items");
    },
});

async function mountCleanupOperationSummaryWith(operation, refreshOperationId = null, refreshDelay = 0) {
    const wrapper = mount(
        CleanupOperationSummary,
        { propsData: { operation, refreshOperationId, refreshDelay } },
        localVue
    );
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
