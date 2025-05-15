import { mount, type Wrapper, type WrapperArray } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { type CleanableItem, CleanableSummary, type CleanupOperation, CleanupResult } from "./model";

import ReviewCleanupDialog from "./ReviewCleanupDialog.vue";

const localVue = getLocalVue();

const REVIEW_TABLE = '[data-test-id="review-table"]';
const DELETE_BUTTON = '[data-test-id="delete-button"]';
const SELECT_ALL_CHECKBOX = '[data-test-id="select-all-checkbox"]';
const AGREEMENT_CHECKBOX = '[data-test-id="agreement-checkbox"]';
const CONFIRMATION_MODAL = "#confirmation-modal";

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
            EXPECTED_ITEMS
        ),
};

async function mountReviewCleanupDialogWith(operation: CleanupOperation, totalItems = EXPECTED_TOTAL_ITEMS) {
    const wrapper = mount(ReviewCleanupDialog as object, {
        propsData: { operation, totalItems, show: true, modalStatic: true },
        localVue,
    });
    await flushPromises();
    return wrapper;
}

async function setAllItemsChecked(wrapper: Wrapper<Vue>) {
    await wrapper.find(SELECT_ALL_CHECKBOX).setChecked();
    await flushPromises();
}

describe("ReviewCleanupDialog.vue", () => {
    it("should display a table with items to review", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);

        expect(wrapper.find(REVIEW_TABLE).exists()).toBe(true);
        expect(wrapper.findAll("tbody > tr").wrappers.length).toBe(EXPECTED_TOTAL_ITEMS);
    });

    it("should disable the delete button if no items are selected", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        const deleteButton = wrapper.find(DELETE_BUTTON);

        expect(deleteButton.attributes().disabled).toBeTruthy();
        // TODO: explicit any because the type of the vm is not correctly inferred, remove when fixed
        expect((wrapper.vm as any).selectedItems.length).toBe(0);
        await setAllItemsChecked(wrapper);
        // TODO: explicit any because the type of the vm is not correctly inferred, remove when fixed
        expect((wrapper.vm as any).selectedItems.length).toBe(EXPECTED_TOTAL_ITEMS);
        expect(deleteButton.attributes().disabled).toBeFalsy();
    });

    it("should show a confirmation message when deleting items", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        await setAllItemsChecked(wrapper);
        const confirmationModal = wrapper.find(CONFIRMATION_MODAL);

        expect(confirmationModal.attributes("aria-hidden")).toBeTruthy();
        await wrapper.find(DELETE_BUTTON).trigger("click");
        expect(confirmationModal.attributes("aria-hidden")).toBeFalsy();
    });

    it("should disable the confirmation button until the agreement has been accepted", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        await setAllItemsChecked(wrapper);
        await wrapper.find(DELETE_BUTTON).trigger("click");
        const allButtons = wrapper.findAll(".btn");
        const permanentlyDeleteBtn = withNameFilter(allButtons).hasText("Permanently delete").at(0);

        expect(permanentlyDeleteBtn.attributes().disabled).toBeTruthy();
        await wrapper.find(AGREEMENT_CHECKBOX).setChecked();
        expect(permanentlyDeleteBtn.attributes().disabled).toBeFalsy();
    });

    it("should emit the confirmation event when the agreement and deletion has been confirmed", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION);
        await setAllItemsChecked(wrapper);
        await wrapper.find(DELETE_BUTTON).trigger("click");
        await wrapper.find(AGREEMENT_CHECKBOX).setChecked();
        const allButtons = wrapper.findAll(".btn");
        const permanentlyDeleteBtn = withNameFilter(allButtons).hasText("Permanently delete").at(0);

        expect(wrapper.emitted().onConfirmCleanupSelectedItems).toBeFalsy();
        await permanentlyDeleteBtn.trigger("click");
        expect(wrapper.emitted().onConfirmCleanupSelectedItems).toBeTruthy();
        expect(wrapper.emitted().onConfirmCleanupSelectedItems?.length).toBe(1);
    });

    // From: https://github.com/vuejs/vue-test-utils/issues/960#issuecomment-626327505
    function withNameFilter(wrapperArray: WrapperArray<Vue>) {
        return {
            childSelectorHasText: (selector: string, str: string): WrapperArray<Vue> =>
                wrapperArray.filter((i) => i.find(selector).text().match(str)),

            hasText: (str: string): WrapperArray<Vue> => wrapperArray.filter((i) => i.text().match(str)),
        };
    }
});
