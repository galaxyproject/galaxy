import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import StorageOperationRunsTable from "./StorageOperationRunsTable.vue";

vi.mock("@/stores/objectStoreStore", () => ({
    useObjectStoreStore: () => ({ getObjectStoreNameById: () => null }),
}));

const SELECTORS = {
    PAGER: "nav[aria-label='Pagination']",
    PAGE_BUTTON: "nav[aria-label='Pagination'] button[data-page]",
    CURRENT_PAGE: "nav[aria-label='Pagination'] button[aria-current='page']",
};

function makeRows(count: number) {
    return Array.from({ length: count }, (_, index) => ({
        run_id: `run-${index + 1}`,
        historyId: "history-1",
        runUrl: `/histories/history-1/storage/runs/run-${index + 1}`,
        state: "completed",
        mode: "copy",
        target_object_store_id: "store-1",
        total_count: 1,
        succeeded_count: 1,
        failed_count: 0,
        skipped_count: 0,
        total_bytes_processed: 10,
        create_time: "2026-01-01T00:00:00",
        update_time: "2026-01-01T00:01:00",
        progressPercent: 100,
    }));
}

function mountTable(rowCount: number, currentPage = 1) {
    const localVue = getLocalVue();
    return mount(StorageOperationRunsTable as object, {
        props: {
            title: "Finished",
            rows: makeRows(rowCount),
            currentPage,
            perPage: 2,
            sortBy: "create_time",
            sortDesc: true,
            emptyMessage: "No runs",
        },
        global: {
            ...localVue,
            stubs: {
                ...localVue.stubs,
                StorageOperationOutcomeProgress: true,
                StorageOperationRunStateBadge: true,
                UtcDate: true,
            },
        },
    });
}

describe("StorageOperationRunsTable", () => {
    it("shows the page the parent passes in", () => {
        const wrapper = mountTable(5, 2);

        expect(wrapper.findAll(SELECTORS.PAGE_BUTTON).map((button) => button.text())).toEqual(["1", "2", "3"]);
        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("2");
    });

    it("emits page-change with the clicked page", async () => {
        const wrapper = mountTable(5);

        await wrapper.find(`${SELECTORS.PAGE_BUTTON}[data-page='3']`).trigger("click");

        expect(emittedArg(wrapper, "page-change")).toBe(3);
    });

    it("shows no pager when every row fits on one page", () => {
        const wrapper = mountTable(2);

        expect(wrapper.find(SELECTORS.PAGER).exists()).toBe(false);
    });
});
