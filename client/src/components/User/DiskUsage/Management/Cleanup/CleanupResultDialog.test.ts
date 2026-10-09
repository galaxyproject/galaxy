import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { CleanupResult } from "./model";
import { getFakeCleanableItem } from "./test-utils";

import CleanupResultDialog from "./CleanupResultDialog.vue";

enableAutoUnmount(afterEach);

const LOADING_SPINNER = '[data-test-id="loading-spinner"]';
const ERROR_ALERT = '[data-test-id="error-alert"]';
const SUCCESS_INFO = '[data-test-id="success-info"]';
const PARTIAL_SUCCESS_INFO = '[data-test-id="partial-success-info"]';
const ERRORS_TABLE = '[data-test-id="errors-table"]';

const items = [
    getFakeCleanableItem({ id: "1", name: "Dataset X" }),
    getFakeCleanableItem({ id: "2", name: "Dataset Y" }),
    getFakeCleanableItem({ id: "3", name: "Dataset Z" }),
];

function successfulCleanupResult() {
    return new CleanupResult(
        { total_item_count: 3, success_item_count: 3, total_free_bytes: 512 * 3, errors: [] },
        items,
    );
}

function mountCleanupResultDialog(result?: CleanupResult) {
    return shallowMount(CleanupResultDialog, {
        props: { result },
        global: {
            ...getLocalVue(),
            // Render table rows so assertions cover the displayed item names and reasons.
            stubs: { GTable: false },
        },
    });
}

describe("CleanupResultDialog.vue", () => {
    it("shows a loading indicator until a cleanup result arrives", async () => {
        const wrapper = mountCleanupResultDialog();

        expect(wrapper.find(LOADING_SPINNER).exists()).toBe(true);

        await wrapper.setProps({ result: successfulCleanupResult() });
        expect(wrapper.find(LOADING_SPINNER).exists()).toBe(false);
    });

    it("shows the operation error when cleanup fails completely", () => {
        const wrapper = mountCleanupResultDialog(new CleanupResult(undefined, [], "The operation failed"));

        const errorAlert = wrapper.find(ERROR_ALERT);
        expect(errorAlert.exists()).toBe(true);
        expect(errorAlert.text()).toContain("The operation failed");
        expect(wrapper.find(SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(PARTIAL_SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(ERRORS_TABLE).exists()).toBe(false);
    });

    it("shows freed space and each item error when cleanup partially succeeds", () => {
        const result = new CleanupResult(
            {
                total_item_count: 3,
                success_item_count: 1,
                total_free_bytes: 512,
                errors: [
                    { item_id: "1", error: "Failed because of X" },
                    { item_id: "2", error: "Failed because of Y" },
                ],
            },
            items,
        );
        const wrapper = mountCleanupResultDialog(result);

        expect(wrapper.find(ERROR_ALERT).exists()).toBe(false);
        expect(wrapper.find(SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(PARTIAL_SUCCESS_INFO).exists()).toBe(true);
        expect(wrapper.find(PARTIAL_SUCCESS_INFO).text()).toContain("512 b");
        expect(wrapper.find(ERRORS_TABLE).exists()).toBe(true);
        const errorRows = wrapper.findAll("tbody > tr");
        expect(errorRows).toHaveLength(result.errors.length);
        expect(errorRows.map((row) => row.findAll("td").map((cell) => cell.text()))).toEqual([
            ["Dataset X", "Failed because of X"],
            ["Dataset Y", "Failed because of Y"],
        ]);
    });

    it("shows the freed space when every item is cleaned successfully", () => {
        const wrapper = mountCleanupResultDialog(successfulCleanupResult());

        expect(wrapper.find(SUCCESS_INFO).exists()).toBe(true);
        expect(wrapper.find(SUCCESS_INFO).text()).toContain("1.5 KB");
        expect(wrapper.find(ERROR_ALERT).exists()).toBe(false);
        expect(wrapper.find(PARTIAL_SUCCESS_INFO).exists()).toBe(false);
        expect(wrapper.find(ERRORS_TABLE).exists()).toBe(false);
    });
});
