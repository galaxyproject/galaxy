import { composeStories } from "@storybook/vue3-vite";
import { emittedArg, nth, suppressDebugConsole } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useConfigStore } from "@/stores/configurationStore";

import * as SelectionOperationsStories from "./SelectionOperations.stories";
import { HISTORY, selectionOf, VISIBLE_DATASET, visibleDatasets } from "./test_fixtures";

import SelectionOperations from "./SelectionOperations.vue";
import StorageOperationWizardModal from "./StorageOperationWizardModal.vue";

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({
        confirm: vi.fn().mockResolvedValue(true),
    }),
}));

const stories = composeStories(SelectionOperationsStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

const BULK_SUCCESS_RESPONSE = { success_count: 1, errors: [] };
/** Galaxy refuses to change the items of an archived history. */
const IMMUTABLE_HISTORY_ERROR = { err_msg: "History is immutable", err_code: 403003 };
const ARCHIVED_HISTORY = { ...HISTORY, archived: true };

const getMenuSelectorFor = (option) => `[data-description="${option} option"]`;

/** Mounts a story, with `props` on top of its args, once the configuration has loaded. */
async function mountOperations(story, props = {}) {
    const wrapper = mountStory(story, { props });
    await vi.waitFor(() => expect(useConfigStore().isLoaded).toBe(true));
    await flushPromises();
    return wrapper.getComponent(SelectionOperations);
}

/** Whether the menu of `story`, with `props` on top of its args, has an item matching `selector`. */
async function offers(story, selector, props = {}) {
    const operations = await mountOperations(story, props);
    // The menu itself is there, so a missing item is really missing.
    expect(operations.find('[data-description="selected count"]').exists()).toBe(true);
    return operations.find(selector).exists();
}

/** Answers the bulk operation the menu runs on the selected items. */
function bulkOperationAnswers(status, body) {
    server.use(
        http.put("/api/histories/{history_id}/contents/bulk", ({ response }) =>
            response.untyped(HttpResponse.json(body, { status })),
        ),
    );
}

describe("History Selection Operations", () => {
    describe("With Celery Enabled", () => {
        describe("Dropdown Menu", () => {
            it("should not render if there is nothing selected", async () => {
                const operations = await mountOperations(stories.DatasetSelected, {
                    selectionSize: 0,
                    contentSelection: selectionOf(),
                });
                // root is `<section v-if="...">`; when false, VTU2 renders it as
                // a comment node rather than empty markup.
                expect(operations.find("section").exists()).toBe(false);
            });

            it("should display the total number of items to apply the operation", async () => {
                const operations = await mountOperations(stories.DatasetSelected, {
                    selectionSize: 10,
                    contentSelection: selectionOf(...visibleDatasets(10)),
                });
                expect(operations.get('[data-description="selected count"]').text()).toBe("With 10 selected...");
            });

            it("should display 'hide' option on visible items", async () => {
                const option = getMenuSelectorFor("hide");
                expect(await offers(stories.DatasetSelected, option)).toBe(true);
                expect(await offers(stories.DatasetSelected, option, { filterText: "visible:true" })).toBe(true);
            });

            it("should not display 'hide' option when only hidden items are selected", async () => {
                const option = getMenuSelectorFor("hide");
                expect(await offers(stories.DatasetSelected, option)).toBe(true);
                expect(await offers(stories.HiddenSelected, option, { filterText: "visible:any" })).toBe(false);
                expect(await offers(stories.HiddenSelected, option)).toBe(false);
            });

            it("should not display 'unhide' option when only visible items are selected", async () => {
                const option = getMenuSelectorFor("unhide");
                expect(await offers(stories.DatasetSelected, option, { filterText: "visible:any" })).toBe(false);
            });

            it("should display 'delete' option on non-deleted items", async () => {
                const option = getMenuSelectorFor("delete");
                expect(await offers(stories.DatasetSelected, option)).toBe(true);
                expect(await offers(stories.DatasetSelected, option, { filterText: "deleted:false" })).toBe(true);
            });

            it("should display 'delete' option on non-deleted items", async () => {
                const option = getMenuSelectorFor("delete");
                expect(await offers(stories.DatasetSelected, option)).toBe(true);
                expect(await offers(stories.DatasetSelected, option, { filterText: "deleted:false" })).toBe(true);
            });

            it("should not display 'delete' option when only deleted items are selected", async () => {
                const option = getMenuSelectorFor("delete");
                expect(await offers(stories.DatasetSelected, option)).toBe(true);
                expect(await offers(stories.DeletedSelected, option, { filterText: "deleted:any" })).toBe(false);
            });

            it("should display 'permanently delete' option unless all selected items are purged", async () => {
                const option = getMenuSelectorFor("purge");
                expect(await offers(stories.DatasetSelected, option)).toBe(true);
                expect(await offers(stories.DatasetSelected, option, { filterText: "deleted:any visible:any" })).toBe(
                    true,
                );
            });

            it("should not display 'undelete' when only purged items are selected", async () => {
                const option = getMenuSelectorFor("undelete");
                expect(await offers(stories.PurgedSelected, option, { filterText: "" })).toBe(false);
                expect(await offers(stories.PurgedSelected, option)).toBe(false);
            });

            it("should display 'undelete' option when is query selection mode and filtering by deleted", async () => {
                const option = getMenuSelectorFor("undelete");
                // In query selection mode we don't know if some items may not be purged, so we allow to undelete
                expect(await offers(stories.PurgedSelected, option, { isQuerySelection: true })).toBe(true);
            });

            it("should display 'undelete' option when is query selection mode and filtering by any deleted state", async () => {
                const option = getMenuSelectorFor("undelete");
                // In query selection mode we don't know if some items may not be purged, so we allow to undelete
                expect(
                    await offers(stories.DatasetSelected, option, {
                        filterText: "deleted:any",
                        isQuerySelection: true,
                    }),
                ).toBe(true);
            });

            it("should display collection building options only on active (non-deleted) items", async () => {
                const buildListOption = '[data-description="auto build list"]';
                const story = stories.DatasetSelected;
                expect(await offers(story, buildListOption, { filterText: "visible:true deleted:false" })).toBe(true);
                expect(await offers(story, buildListOption, { filterText: "deleted:true" })).toBe(false);
                expect(await offers(story, buildListOption, { filterText: "visible:any deleted:false" })).toBe(true);
                expect(await offers(story, buildListOption, { filterText: "deleted:any" })).toBe(false);
            });
        });

        describe("Operation Run", () => {
            it("should emit event to disable selection", async () => {
                const operations = await mountOperations(stories.DatasetSelected);
                bulkOperationAnswers(200, BULK_SUCCESS_RESPONSE);

                expect(operations.emitted()).not.toHaveProperty("update:show-selection");
                operations.vm.hideSelected();
                await flushPromises();
                expect(operations.emitted()).toHaveProperty("update:show-selection");
                expect(emittedArg(operations, "update:show-selection")).toBe(false);
            });

            it("should update operation-running state when running any operation that succeeds", async () => {
                const operations = await mountOperations(stories.DatasetSelected);
                bulkOperationAnswers(200, BULK_SUCCESS_RESPONSE);

                expect(operations.emitted()).not.toHaveProperty("update:operation-running");
                operations.vm.hideSelected();
                await flushPromises();
                expect(operations.emitted()).toHaveProperty("update:operation-running");

                const operationRunningEvents = operations.emitted("update:operation-running");
                expect(operationRunningEvents).toHaveLength(1);
                // The event sets the current History update time for waiting until the next history update
                expect(nth(operationRunningEvents, 0)).toEqual([HISTORY.update_time]);
            });

            it("should update operation-running state to null when the operation fails", async () => {
                suppressDebugConsole(); // expected error messages since we're testing errors.
                const operations = await mountOperations(stories.DatasetSelected, { history: ARCHIVED_HISTORY });
                bulkOperationAnswers(403, IMMUTABLE_HISTORY_ERROR);

                expect(operations.emitted()).not.toHaveProperty("update:operation-running");
                operations.vm.hideSelected();
                await flushPromises();
                expect(operations.emitted()).toHaveProperty("update:show-selection");

                const operationRunningEvents = operations.emitted("update:operation-running");
                // We expect 2 events, one before running the operation and another one after completion
                expect(operationRunningEvents).toHaveLength(2);
                // The first event sets the current History update time for waiting until the next history update
                expect(nth(operationRunningEvents, 0)).toEqual([HISTORY.update_time]);
                // The second is null to signal that we shouldn't wait for a history change anymore since the operation has failed
                expect(nth(operationRunningEvents, 1)).toEqual([null]);
            });

            it("should emit operation error event when the operation fails", async () => {
                suppressDebugConsole(); // expected error messages since we're testing errors.
                const operations = await mountOperations(stories.DatasetSelected, { history: ARCHIVED_HISTORY });
                bulkOperationAnswers(403, IMMUTABLE_HISTORY_ERROR);

                expect(operations.emitted()).not.toHaveProperty("operation-error");
                operations.vm.hideSelected();
                await flushPromises();
                expect(operations.emitted()).toHaveProperty("operation-error");
            });

            it("should emit operation error event with the result when any item fail", async () => {
                const BULK_ERROR_RESPONSE = {
                    success_count: 0,
                    errors: [
                        {
                            error: "Error reason",
                            item: { history_content_type: "dataset", id: VISIBLE_DATASET.id },
                        },
                    ],
                };
                const operations = await mountOperations(stories.DatasetSelected);
                bulkOperationAnswers(200, BULK_ERROR_RESPONSE);

                expect(operations.emitted()).not.toHaveProperty("operation-error");
                operations.vm.hideSelected();
                await flushPromises();
                expect(operations.emitted()).toHaveProperty("operation-error");

                const operationErrorEvents = operations.emitted("operation-error");
                expect(operationErrorEvents).toHaveLength(1);
                const errorEvent = emittedArg(operations, "operation-error");
                expect(errorEvent).toHaveProperty("result");
                expect(errorEvent.result).toEqual(BULK_ERROR_RESPONSE);
            });

            it("should hide the selection when a storage operation completes", async () => {
                const operations = await mountOperations(stories.DatasetSelected);
                const wizardModal = operations.getComponent(StorageOperationWizardModal);

                expect(operations.emitted("update:show-selection")).toBeFalsy();

                wizardModal.vm.$emit("completed");
                await flushPromises();

                expect(operations.emitted("update:show-selection")).toBeTruthy();
                expect(nth(operations.emitted("update:show-selection"), -1)).toEqual([false]);
            });
        });
    });

    describe("With Celery Disabled", () => {
        describe("Dropdown Menu", () => {
            it("should hide `Manage Storage Location` option", async () => {
                const option = '[data-description="storage operation"]';
                // With Celery the same menu has it, once the storage locations have loaded.
                const withCelery = await mountOperations(stories.DatasetSelected);
                await vi.waitFor(() => expect(withCelery.find(option).exists()).toBe(true));
                expect(await offers(stories.WithoutCelery, option)).toBe(false);
            });
        });
    });
});
