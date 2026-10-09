import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import type GModal from "@/components/BaseComponents/GModal.vue";

import { CleanableSummary, type CleanupOperation, CleanupResult } from "./model";
import { getFakeCleanableItem, getFakeCleanupOperation } from "./test-utils";

import ReviewCleanupDialog from "./ReviewCleanupDialog.vue";

enableAutoUnmount(afterEach);

const REVIEW_TABLE = '[data-test-id="review-table"]';
const DELETE_BUTTON = '[data-test-id="delete-button"]';
const SELECT_ALL_CHECKBOX = '[data-test-id="select-all-checkbox"]';
const AGREEMENT_CHECKBOX = '[data-test-id="agreement-checkbox"]';

const EXPECTED_ITEMS = [
    getFakeCleanableItem({ id: "1", name: "Item 1" }),
    getFakeCleanableItem({ id: "2", name: "Item 2" }),
];
const EXPECTED_TOTAL_ITEMS = 2;
function getReviewOperation() {
    return getFakeCleanupOperation({
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
    });
}

async function mountReviewCleanupDialogWith(operation: CleanupOperation, totalItems = EXPECTED_TOTAL_ITEMS) {
    const wrapper = mount(ReviewCleanupDialog, {
        props: { operation, totalItems },
        global: getLocalVue(),
    });
    await flushPromises();
    return wrapper;
}

async function selectAllItems(wrapper: Awaited<ReturnType<typeof mountReviewCleanupDialogWith>>) {
    await wrapper.find(SELECT_ALL_CHECKBOX).setValue(true);
    await flushPromises();
}

describe("ReviewCleanupDialog.vue", () => {
    it("loads the review table when the dialog opens", async () => {
        const wrapper = await mountReviewCleanupDialogWith(getReviewOperation());

        wrapper.vm.openModal();
        await flushPromises();

        expect(wrapper.find(REVIEW_TABLE).exists()).toBe(true);
        expect(wrapper.findAll("tbody > tr")).toHaveLength(EXPECTED_TOTAL_ITEMS);
    });

    it("enables deletion after selecting items", async () => {
        const wrapper = await mountReviewCleanupDialogWith(getReviewOperation());
        const deleteButton = wrapper.find(DELETE_BUTTON);

        expect(deleteButton.classes()).toContain("g-disabled");
        await selectAllItems(wrapper);
        expect(deleteButton.classes()).not.toContain("g-disabled");
    });

    it("opens confirmation when selected items are deleted", async () => {
        const wrapper = await mountReviewCleanupDialogWith(getReviewOperation());
        await selectAllItems(wrapper);

        const confirmationModal = wrapper.getComponent<typeof GModal>("#confirmation-modal");
        expect(confirmationModal.props("show")).toBeFalsy();
        await wrapper.find(DELETE_BUTTON).trigger("click");
        expect(confirmationModal.props("show")).toBeTruthy();
    });

    it("requires the deletion agreement before confirmation", async () => {
        const wrapper = await mountReviewCleanupDialogWith(getReviewOperation());
        await selectAllItems(wrapper);
        await wrapper.find(DELETE_BUTTON).trigger("click");

        const confirmationModal = wrapper.getComponent<typeof GModal>("#confirmation-modal");
        expect(confirmationModal.props("okDisabled")).toBe(true);
        await wrapper.find(AGREEMENT_CHECKBOX).setValue(true);
        await flushPromises();
        expect(confirmationModal.props("okDisabled")).toBe(false);
    });

    it("emits the selected items once after accepting the agreement and confirming", async () => {
        const wrapper = await mountReviewCleanupDialogWith(getReviewOperation());
        await selectAllItems(wrapper);
        await wrapper.find(DELETE_BUTTON).trigger("click");
        await wrapper.find(AGREEMENT_CHECKBOX).setValue(true);

        const confirmationModal = wrapper.getComponent<typeof GModal>("#confirmation-modal");
        expect(wrapper.emitted("onConfirmCleanupSelectedItems")).toBeFalsy();
        confirmationModal.vm.$emit("ok");
        await flushPromises();
        expect(wrapper.emitted("onConfirmCleanupSelectedItems")).toEqual([[EXPECTED_ITEMS]]);
    });
});
