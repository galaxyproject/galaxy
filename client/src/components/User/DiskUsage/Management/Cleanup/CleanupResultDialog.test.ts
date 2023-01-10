import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";
import CleanupResultDialog from "./CleanupResultDialog.vue";
import { CleanupResult } from "./model";

const localVue = getLocalVue();

const LOADING_SPINNER = '[data-test-id="loading-spinner"]';
const ERROR_ALERT = '[data-test-id="error-alert"]';
const SUCCESS_INFO = '[data-test-id="success-info"]';
const PARTIAL_SUCCESS_INFO = '[data-test-id="partial-success-info"]';
const ERRORS_TABLE = '[data-test-id="errors-table"]';

const NO_RESULT_YET = undefined;
const FAILED_RESULT = () => {
    return new CleanupResult({
        errorMessage: "The operation failed",
        totalFreeBytes: 0,
        totalItemCount: 0,
        errors: [],
    });
};
const PARTIAL_SUCCESS_RESULT = () => {
    return new CleanupResult({
        totalItemCount: 3,
        totalFreeBytes: 1,
        errors: [
            { name: "Dataset X", reason: "Failed because of X" },
            { name: "Dataset Y", reason: "Failed because of Y" },
        ],
    });
};
const SUCCESS_RESULT = () => {
    return new CleanupResult({ totalItemCount: 2, totalFreeBytes: 2, errors: [] });
};
async function mountCleanupResultDialogWith(result?: CleanupResult) {
    const wrapper = mount(CleanupResultDialog, { propsData: { result, show: true }, localVue });
    await flushPromises();
    return wrapper;
}

describe("CleanupResultDialog.vue", () => {
    it("should display a loading indicator when there is no result yet", async () => {
        const wrapper = await mountCleanupResultDialogWith(NO_RESULT_YET);

        expect(wrapper.find(LOADING_SPINNER).exists()).toBe(true);

        await wrapper.setProps({ result: SUCCESS_RESULT() });
        expect(wrapper.find(LOADING_SPINNER).exists()).toBe(false);
    });

    it("should display an error message when the operation completely failed", async () => {
        const failedResult = FAILED_RESULT();
        const wrapper = await mountCleanupResultDialogWith(failedResult);

        const errorAlert = wrapper.find(ERROR_ALERT);
        expect(errorAlert.exists()).toBe(true);
        expect(errorAlert.html()).toContain(failedResult.errorMessage);
        expect(wrapper.find(SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(PARTIAL_SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(ERRORS_TABLE).exists()).toBe(false);
    });

    it("should display the amount freed and a table with errors for each errored item when partial success", async () => {
        const partialSuccessResult = PARTIAL_SUCCESS_RESULT();
        const wrapper = await mountCleanupResultDialogWith(partialSuccessResult);

        expect(wrapper.find(ERROR_ALERT).exists()).toBe(false);
        expect(wrapper.find(SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(PARTIAL_SUCCESS_INFO).exists()).toBe(true);
        expect(wrapper.find(ERRORS_TABLE).exists()).toBe(true);
        expect(wrapper.findAll("tbody > tr").wrappers.length).toBe(partialSuccessResult.errors.length);
    });

    it("should display a success message when everything went OK", async () => {
        const wrapper = await mountCleanupResultDialogWith(SUCCESS_RESULT());

        expect(wrapper.find(SUCCESS_INFO).exists()).toBe(true);
        expect(wrapper.find(ERROR_ALERT).exists()).toBe(false);
        expect(wrapper.find(PARTIAL_SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(ERRORS_TABLE).exists()).toBe(false);
    });
});
