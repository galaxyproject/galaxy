import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";

import { getStorageOperationRunItemsWithTotal } from "@/api/histories";

import StorageOperationRunView from "./StorageOperationRunView.vue";

const TOTAL_FAILED = 120;

vi.mock("@/api/histories", async (importOriginal) => ({
    ...(await importOriginal<Record<string, unknown>>()),
    getStorageOperationRunItemsWithTotal: vi.fn(),
}));

vi.mock("@/composables/useStorageRunWatcher", () => ({
    useStorageRunWatcher: () => {
        const runStatus = ref({
            run: {
                run_id: "run-1",
                state: "completed",
                mode: "copy",
                target_object_store_id: "store-1",
                total_count: TOTAL_FAILED,
                succeeded_count: 0,
                failed_count: TOTAL_FAILED,
                skipped_count: 0,
                total_bytes_processed: 0,
                create_time: "2026-01-01T00:00:00",
                update_time: "2026-01-01T00:01:00",
            },
        });
        return { runStatus, isTerminal: computed(() => true), startPolling: vi.fn(), stopPolling: vi.fn() };
    },
}));

vi.mock("@/stores/objectStoreStore", () => ({
    useObjectStoreStore: () => ({ getObjectStoreNameById: () => null }),
}));

vi.mock("@/stores/storageOperationsStore", () => ({
    useStorageOperationsStore: () => ({ startRun: vi.fn() }),
}));

const SELECTORS = {
    PAGE_BUTTON: "nav[aria-label='Pagination'] button[data-page]",
    CURRENT_PAGE: "nav[aria-label='Pagination'] button[aria-current='page']",
};

async function mountRunView() {
    const localVue = getLocalVue();
    const wrapper = mount(StorageOperationRunView as object, {
        props: { historyId: "history-1", runId: "run-1" },
        global: {
            ...localVue,
            stubs: {
                ...localVue.stubs,
                BreadcrumbHeading: true,
                DatasetPopoverLink: true,
                FilterMenu: true,
                StorageOperationOutcomeProgress: true,
                StorageOperationRunStateBadge: true,
            },
        },
    });
    await flushPromises();
    return wrapper;
}

function requestedOffsets() {
    return vi.mocked(getStorageOperationRunItemsWithTotal).mock.calls.map(([, , options]) => options?.offset);
}

describe("StorageOperationRunView", () => {
    beforeEach(() => {
        vi.mocked(getStorageOperationRunItemsWithTotal).mockReset();
        vi.mocked(getStorageOperationRunItemsWithTotal).mockResolvedValue({ data: [], totalMatches: TOTAL_FAILED });
    });

    it("loads the page picked in the pager", async () => {
        const wrapper = await mountRunView();

        expect(wrapper.findAll(SELECTORS.PAGE_BUTTON).map((button) => button.text())).toEqual(["1", "2", "3"]);
        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("1");
        expect(requestedOffsets()).toEqual([0]);

        await wrapper.find(`${SELECTORS.PAGE_BUTTON}[data-page='3']`).trigger("click");
        await flushPromises();

        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("3");
        expect(requestedOffsets()).toEqual([0, 100]);
    });
});
