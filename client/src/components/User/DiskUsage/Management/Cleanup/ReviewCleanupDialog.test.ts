import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { type CleanableItem, CleanableSummary, type CleanupOperation, CleanupResult } from "./model";

import ReviewCleanupDialog from "./ReviewCleanupDialog.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const localVue = getLocalVue();

const REVIEW_TABLE = '[data-test-id="review-table"]';
const DELETE_BUTTON = '[data-test-id="delete-button"]';
const SELECT_ALL_CHECKBOX = '[data-test-id="select-all-checkbox"]';
const AGREEMENT_CHECKBOX = '[data-test-id="agreement-checkbox"]';

const EXPECTED_ITEMS: CleanableItem[] = [
    { id: "1", name: "Item 1", size: 512, type: "dataset", update_time: new Date().toISOString() },
    { id: "2", name: "Item 2", size: 512, type: "dataset", update_time: new Date().toISOString() },
];
const EXPECTED_TOTAL_ITEMS = EXPECTED_ITEMS.length;
const FAKE_OPERATION: CleanupOperation = {
    id: "operation-id",
    name: "operation name",
    description: "operation description",
    fetchSummary: async () =>
        new CleanableSummary({
            total_size: 1024,
            total_items: EXPECTED_TOTAL_ITEMS,
        }),
    fetchItems: async () => EXPECTED_ITEMS,
    cleanupItems: async () =>
        new CleanupResult(
            {
                total_item_count: EXPECTED_TOTAL_ITEMS,
                success_item_count: EXPECTED_TOTAL_ITEMS,
                total_free_bytes: 1024,
                errors: [],
            },
            EXPECTED_ITEMS,
        ),
};

async function mountReviewCleanupDialogWith(operation: CleanupOperation, totalItems = EXPECTED_TOTAL_ITEMS) {
    const wrapper = mount(ReviewCleanupDialog as object, {
        propsData: { operation, totalItems, modalStatic: true },
        localVue,
    });
    await flushPromises();
    return wrapper;
}

async function setAllItemsChecked(wrapper: Wrapper<any>) {
    await wrapper.find(SELECT_ALL_CHECKBOX).setChecked();
    await flushPromises();
}

describe("ReviewCleanupDialog.vue", () => {
    it("should display a table with items to review", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);

        (wrapper.vm as any).openModal();
        await flushPromises();

        expect(wrapper.find(REVIEW_TABLE).exists()).toBe(true);
        expect(wrapper.findAll("tbody > tr").length).toBe(EXPECTED_TOTAL_ITEMS);
    });

    it("should disable the delete button if no items are selected", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        const deleteButton = wrapper.find(DELETE_BUTTON);

        expect(deleteButton.classes()).toContain("g-disabled");
        await setAllItemsChecked(wrapper);
        expect(deleteButton.classes()).not.toContain("g-disabled");
    });

    it("should show a confirmation message when deleting items", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        await setAllItemsChecked(wrapper);

        const confirmationModal = wrapper.findAllComponents(GModal).at(1);
        expect(confirmationModal.props("show")).toBeFalsy();
        await wrapper.find(DELETE_BUTTON).trigger("click");
        expect(confirmationModal.props("show")).toBeTruthy();
    });

    it("should disable the confirmation button until the agreement has been accepted", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        await setAllItemsChecked(wrapper);
        await wrapper.find(DELETE_BUTTON).trigger("click");

        const confirmationModal = wrapper.findAllComponents(GModal).at(1);
        expect(confirmationModal.props("okDisabled")).toBe(true);
        await wrapper.find(AGREEMENT_CHECKBOX).setChecked();
        await flushPromises();
        expect(confirmationModal.props("okDisabled")).toBe(false);
    });

    it("should emit the confirmation event when the agreement and deletion has been confirmed", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        await setAllItemsChecked(wrapper);
        await wrapper.find(DELETE_BUTTON).trigger("click");
        await wrapper.find(AGREEMENT_CHECKBOX).setChecked();

        const confirmationModal = wrapper.findAllComponents(GModal).at(1);
        expect(wrapper.emitted().onConfirmCleanupSelectedItems).toBeFalsy();
        confirmationModal.vm.$emit("ok");
        await flushPromises();
        expect(wrapper.emitted().onConfirmCleanupSelectedItems).toBeTruthy();
        expect(wrapper.emitted().onConfirmCleanupSelectedItems?.length).toBe(1);
    });
});
