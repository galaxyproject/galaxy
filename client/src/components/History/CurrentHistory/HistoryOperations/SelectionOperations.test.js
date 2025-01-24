import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue, suppressDebugConsole } from "tests/jest/helpers";
import { setupMockConfig } from "tests/jest/mockConfig";

import { useServerMock } from "@/api/client/__mocks__";

import SelectionOperations from "./SelectionOperations.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const FAKE_HISTORY_ID = "fake_history_id";
const FAKE_HISTORY = { id: FAKE_HISTORY_ID, update_time: new Date() };
const BULK_SUCCESS_RESPONSE = { success_count: 1, errors: [] };

const NO_TASKS_CONFIG = {
    enable_celery_tasks: false,
};
const TASKS_CONFIG = {
    enable_celery_tasks: true,
};

const getMenuSelectorFor = (option) => `[data-description="${option} option"]`;

const getPurgedSelection = () => new Map([["FAKE_ID", { purged: true }]]);
const getNonPurgedSelection = () => new Map([["FAKE_ID", { purged: false }]]);
const getVisibleSelection = () => new Map([["FAKE_ID", { visible: true }]]);
const getHiddenSelection = () => new Map([["FAKE_ID", { visible: false }]]);
const getDeletedSelection = () => new Map([["FAKE_ID", { deleted: true }]]);
const getActiveSelection = () => new Map([["FAKE_ID", { deleted: false }]]);

async function mountSelectionOperationsWrapper(config) {
    setupMockConfig(config);

    const pinia = createPinia();
    const wrapper = shallowMount(SelectionOperations, {
        propsData: {
            history: FAKE_HISTORY,
            filterText: "",
            contentSelection: new Map(),
            selectionSize: 1,
            isQuerySelection: false,
            totalItemsInQuery: 5,
            isMultiViewItem: false,
        },
        localVue,
        pinia,
    });
    await flushPromises();
    return wrapper;
}

describe("History Selection Operations", () => {
    let wrapper;

    describe("With Celery Enabled", () => {
        beforeEach(async () => {
            wrapper = await mountSelectionOperationsWrapper(TASKS_CONFIG);
            await flushPromises();
        });

        describe("Dropdown Menu", () => {
            it("should not render if there is nothing selected", async () => {
                await wrapper.setProps({ selectionSize: 0 });
                expect(wrapper.html()).toBe("");
            });

            it("should display the total number of items to apply the operation", async () => {
                await wrapper.setProps({ selectionSize: 10 });
                expect(wrapper.find('[data-description="selected count"]').text()).toContain("10");
            });

            it("should display 'hide' option on visible items", async () => {
                const option = getMenuSelectorFor("hide");
                expect(wrapper.find(option).exists()).toBe(true);
                await wrapper.setProps({ filterText: "visible:true" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display 'hide' option when visible and hidden items are mixed", async () => {
                const option = getMenuSelectorFor("hide");
                expect(wrapper.find(option).exists()).toBe(true);
                await wrapper.setProps({ filterText: "visible:any" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should not display 'hide' option when only hidden items are selected", async () => {
                const option = getMenuSelectorFor("hide");
                expect(wrapper.find(option).exists()).toBe(true);
                await wrapper.setProps({ filterText: "visible:any", contentSelection: getHiddenSelection() });
                expect(wrapper.find(option).exists()).toBe(false);
                await wrapper.setProps({ filterText: "visible:false" });
                expect(wrapper.find(option).exists()).toBe(false);
            });

            it("should display 'unhide' option on hidden items", async () => {
                const option = getMenuSelectorFor("unhide");
                await wrapper.setProps({ filterText: "visible:false" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display 'unhide' option when hidden and visible items are mixed", async () => {
                const option = getMenuSelectorFor("unhide");
                await wrapper.setProps({ filterText: "visible:any" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should not display 'unhide' option when only visible items are selected", async () => {
                const option = getMenuSelectorFor("unhide");
                await wrapper.setProps({
                    filterText: "visible:any",
                    contentSelection: getVisibleSelection(),
                });
                expect(wrapper.find(option).exists()).toBe(false);
            });

            it("should display 'delete' option on non-deleted items", async () => {
                const option = getMenuSelectorFor("delete");
                expect(wrapper.find(option).exists()).toBe(true);
                await wrapper.setProps({ filterText: "deleted:false" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display 'delete' option on non-deleted items", async () => {
                const option = getMenuSelectorFor("delete");
                expect(wrapper.find(option).exists()).toBe(true);
                await wrapper.setProps({ filterText: "deleted:false" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display 'delete' option when non-deleted and deleted items are mixed", async () => {
                const option = getMenuSelectorFor("delete");
                await wrapper.setProps({ filterText: "deleted:any" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should not display 'delete' option when only deleted items are selected", async () => {
                const option = getMenuSelectorFor("delete");
                expect(wrapper.find(option).exists()).toBe(true);
                await wrapper.setProps({ filterText: "deleted:any", contentSelection: getDeletedSelection() });
                expect(wrapper.find(option).exists()).toBe(false);
            });

            it("should display 'permanently delete' option always", async () => {
                const option = getMenuSelectorFor("purge");
                expect(wrapper.find(option).exists()).toBe(true);
                await wrapper.setProps({ filterText: "deleted:any visible:any" });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display 'undelete' option on deleted and non-purged items", async () => {
                const option = getMenuSelectorFor("undelete");
                expect(wrapper.find(option).exists()).toBe(false);
                await wrapper.setProps({
                    filterText: "deleted:true",
                    contentSelection: getNonPurgedSelection(),
                });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display 'undelete' option when non-purged items (deleted or not) are mixed", async () => {
                const option = getMenuSelectorFor("undelete");
                await wrapper.setProps({
                    filterText: "deleted:any",
                    contentSelection: getNonPurgedSelection(),
                });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should not display 'undelete' when only non-deleted items are selected", async () => {
                const option = getMenuSelectorFor("undelete");
                await wrapper.setProps({
                    filterText: "deleted:any",
                    contentSelection: getActiveSelection(),
                });
                expect(wrapper.find(option).exists()).toBe(false);
            });

            it("should not display 'undelete' when only purged items are selected", async () => {
                const option = getMenuSelectorFor("undelete");
                await wrapper.setProps({
                    contentSelection: getPurgedSelection(),
                    isQuerySelection: false,
                });
                expect(wrapper.find(option).exists()).toBe(false);
            });

            it("should display 'undelete' option when is query selection mode and filtering by deleted", async () => {
                const option = getMenuSelectorFor("undelete");
                // In query selection mode we don't know if some items may not be purged, so we allow to undelete
                await wrapper.setProps({
                    filterText: "deleted:true",
                    contentSelection: getPurgedSelection(),
                    isQuerySelection: true,
                });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display 'undelete' option when is query selection mode and filtering by any deleted state", async () => {
                const option = getMenuSelectorFor("undelete");
                // In query selection mode we don't know if some items may not be purged, so we allow to undelete
                await wrapper.setProps({ filterText: "deleted:any", isQuerySelection: true });
                expect(wrapper.find(option).exists()).toBe(true);
            });

            it("should display collection building options only on active (non-deleted) items", async () => {
                const buildListOption = '[data-description="build list"]';
                const buildListOfPairsOption = '[data-description="build list of pairs"]';
                await wrapper.setProps({ filterText: "visible:true deleted:false" });
                expect(wrapper.find(buildListOption).exists()).toBe(true);
                expect(wrapper.find(buildListOfPairsOption).exists()).toBe(true);
                await wrapper.setProps({ filterText: "deleted:true" });
                expect(wrapper.find(buildListOption).exists()).toBe(false);
                expect(wrapper.find(buildListOfPairsOption).exists()).toBe(false);
                await wrapper.setProps({ filterText: "visible:any deleted:false" });
                expect(wrapper.find(buildListOption).exists()).toBe(true);
                expect(wrapper.find(buildListOfPairsOption).exists()).toBe(true);
                await wrapper.setProps({ filterText: "deleted:any" });
                expect(wrapper.find(buildListOption).exists()).toBe(false);
                expect(wrapper.find(buildListOfPairsOption).exists()).toBe(false);
            });

            it("should display list building option when all are selected", async () => {
                const buildListOption = '[data-description="build list all"]';
                await wrapper.setProps({ selectionSize: 105 });
                await wrapper.setProps({ totalItemsInQuery: 105 });
                await wrapper.setProps({ isQuerySelection: true });
                expect(wrapper.find(buildListOption).exists()).toBe(true);
            });
        });

        describe("Operation Run", () => {
            it("should emit event to disable selection", async () => {
                server.use(
                    http.put("/api/histories/{history_id}/contents/bulk", ({ response }) => {
                        return response(200).json(BULK_SUCCESS_RESPONSE);
                    })
                );

                expect(wrapper.emitted()).not.toHaveProperty("update:show-selection");
                wrapper.vm.hideSelected();
                await flushPromises();
                expect(wrapper.emitted()).toHaveProperty("update:show-selection");
                expect(wrapper.emitted()["update:show-selection"][0][0]).toBe(false);
            });

            it("should update operation-running state when running any operation that succeeds", async () => {
                server.use(
                    http.put("/api/histories/{history_id}/contents/bulk", ({ response }) => {
                        return response(200).json(BULK_SUCCESS_RESPONSE);
                    })
                );

                expect(wrapper.emitted()).not.toHaveProperty("update:operation-running");
                wrapper.vm.hideSelected();
                await flushPromises();
                expect(wrapper.emitted()).toHaveProperty("update:operation-running");

                const operationRunningEvents = wrapper.emitted("update:operation-running");
                expect(operationRunningEvents).toHaveLength(1);
                // The event sets the current History update time for waiting until the next history update
                expect(operationRunningEvents[0]).toEqual([FAKE_HISTORY.update_time]);
            });

            it("should update operation-running state to null when the operation fails", async () => {
                suppressDebugConsole(); // expected error messages since we're testing errors.
                server.use(
                    http.put("/api/histories/{history_id}/contents/bulk", ({ response }) => {
                        return response("4XX").json({ err_msg: "Error", err_code: 400 }, { status: 400 });
                    })
                );

                expect(wrapper.emitted()).not.toHaveProperty("update:operation-running");
                wrapper.vm.hideSelected();
                await flushPromises();
                expect(wrapper.emitted()).toHaveProperty("update:show-selection");

                const operationRunningEvents = wrapper.emitted("update:operation-running");
                // We expect 2 events, one before running the operation and another one after completion
                expect(operationRunningEvents).toHaveLength(2);
                // The first event sets the current History update time for waiting until the next history update
                expect(operationRunningEvents[0]).toEqual([FAKE_HISTORY.update_time]);
                // The second is null to signal that we shouldn't wait for a history change anymore since the operation has failed
                expect(operationRunningEvents[1]).toEqual([null]);
            });

            it("should emit operation error event when the operation fails", async () => {
                suppressDebugConsole(); // expected error messages since we're testing errors.

                server.use(
                    http.put("/api/histories/{history_id}/contents/bulk", ({ response }) => {
                        return response("4XX").json({ err_msg: "Error", err_code: 400 }, { status: 400 });
                    })
                );

                expect(wrapper.emitted()).not.toHaveProperty("operation-error");
                wrapper.vm.hideSelected();
                await flushPromises();
                expect(wrapper.emitted()).toHaveProperty("operation-error");
            });

            it("should emit operation error event with the result when any item fail", async () => {
                const BULK_ERROR_RESPONSE = {
                    success_count: 0,
                    errors: [{ error: "Error reason", item: { history_content_type: "dataset", id: "dataset_id" } }],
                };
                server.use(
                    http.put("/api/histories/{history_id}/contents/bulk", ({ response }) => {
                        return response(200).json(BULK_ERROR_RESPONSE);
                    })
                );

                expect(wrapper.emitted()).not.toHaveProperty("operation-error");
                wrapper.vm.hideSelected();
                await flushPromises();
                expect(wrapper.emitted()).toHaveProperty("operation-error");

                const operationErrorEvents = wrapper.emitted("operation-error");
                expect(operationErrorEvents).toHaveLength(1);
                const errorEvent = operationErrorEvents[0][0];
                expect(errorEvent).toHaveProperty("result");
                expect(errorEvent.result).toEqual(BULK_ERROR_RESPONSE);
            });
        });
    });

    describe("With Celery Disabled", () => {
        beforeEach(async () => {
            wrapper = await mountSelectionOperationsWrapper(NO_TASKS_CONFIG);
            await flushPromises();
        });

        describe("Dropdown Menu", () => {
            it("should hide `Change data type` option", async () => {
                const option = '[data-description="change data type"]';
                expect(wrapper.find(option).exists()).toBe(false);
            });
        });
    });
});
