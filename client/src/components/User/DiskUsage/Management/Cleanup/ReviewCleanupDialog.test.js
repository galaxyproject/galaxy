import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import { CleanableSummary, CleanupOperation, CleanupResult } from "./model";
import ReviewCleanupDialog from "./ReviewCleanupDialog";

const localVue = getLocalVue();

const REVIEW_TABLE = '[data-test-id="review-table"]';
const DELETE_BUTTON = '[data-test-id="delete-button"]';
const SELECT_ALL_CHECKBOX = '[data-test-id="select-all-checkbox"]';
const AGREEMENT_CHECKBOX = '[data-test-id="agreement-checkbox"]';
const CONFIRMATION_MODAL = "#confirmation-modal";

const EXPECTED_TOTAL_ITEMS = 2;
const FAKE_OPERATION = () => {
    return new CleanupOperation({
        id: "operation-id",
        name: "operation name",
        description: "operation description",
        fetchSummary: () =>
            new CleanableSummary({
                totalSize: 1024,
                totalItems: EXPECTED_TOTAL_ITEMS,
            }),
        fetchItems: () => [
            { id: "1", name: "Item 1", size: 512, update_time: new Date().toISOString(), hda_ldda: "hda" },
            { id: "2", name: "Item 2", size: 512, update_time: new Date().toISOString(), hda_ldda: "hda" },
        ],
        cleanupItems: (items) =>
            new CleanupResult({
                totalItemCount: EXPECTED_TOTAL_ITEMS,
                totalFreeBytes: 1024,
            }),
    });
};

async function mountReviewCleanupDialogWith(operation, totalItems = EXPECTED_TOTAL_ITEMS) {
    const wrapper = mount(ReviewCleanupDialog, { propsData: { operation, totalItems, show: true } }, localVue);
    await flushPromises();
    return wrapper;
}

describe("ReviewCleanupDialog.vue", () => {
    it("should display a table with items to review", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION());

        expect(wrapper.find(REVIEW_TABLE).exists()).toBe(true);
        expect(wrapper.findAll("tbody > tr").wrappers.length).toBe(EXPECTED_TOTAL_ITEMS);
    });

    it("should disable the delete button if no items are selected", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION());
        const deleteButton = wrapper.find(DELETE_BUTTON);
        const selectAllCheckbox = wrapper.find(SELECT_ALL_CHECKBOX);

        expect(deleteButton.element.disabled).toBeTruthy();
        expect(wrapper.vm.selectedItems.length).toBe(0);
        await selectAllCheckbox.setChecked();
        expect(wrapper.vm.selectedItems.length).toBe(EXPECTED_TOTAL_ITEMS);
        expect(deleteButton.element.disabled).toBeFalsy();
    });

    it("should show a confirmation message when deleting items", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION());
        await wrapper.find(SELECT_ALL_CHECKBOX).setChecked();
        const confirmationModal = wrapper.find(CONFIRMATION_MODAL);

        expect(confirmationModal.attributes("aria-hidden")).toBeTruthy();
        await wrapper.find(DELETE_BUTTON).trigger("click");
        expect(confirmationModal.attributes("aria-hidden")).toBeFalsy();
    });

    it("should disable the confirmation button until the agreement has been accepted", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION());
        await wrapper.find(SELECT_ALL_CHECKBOX).setChecked();
        await wrapper.find(DELETE_BUTTON).trigger("click");
        const permanentlyDeleteBtn = findByText(wrapper, "button", /Permanently delete/);

        expect(permanentlyDeleteBtn.element.disabled).toBeTruthy();
        await wrapper.find(AGREEMENT_CHECKBOX).setChecked();
        expect(permanentlyDeleteBtn.element.disabled).toBeFalsy();
    });

    it("should emit the confirmation event when the agreement and deletion has been confirmed", async () => {
        const wrapper = await mountReviewCleanupDialogWith(FAKE_OPERATION());
        await wrapper.find(SELECT_ALL_CHECKBOX).setChecked();
        await wrapper.find(DELETE_BUTTON).trigger("click");
        const permanentlyDeleteBtn = findByText(wrapper, "button", /Permanently delete/);
        await wrapper.find(AGREEMENT_CHECKBOX).setChecked();

        expect(wrapper.emitted().onConfirmCleanupSelectedItems).toBeFalsy();
        await permanentlyDeleteBtn.trigger("click");
        expect(wrapper.emitted().onConfirmCleanupSelectedItems).toBeTruthy();
        expect(wrapper.emitted().onConfirmCleanupSelectedItems.length).toBe(1);
    });

    function findByText(wrap, selector, text) {
        return wrap
            .findAll(selector)
            .filter((n) => n.text().match(text))
            .at(0);
    }
});
