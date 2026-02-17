import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { refactor, type RefactorResponse } from "@/api/workflows";

import RefactorConfirmationModal from "./RefactorConfirmationModal.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/api/workflows", () => ({
    refactor: vi.fn(),
}));

const mockConfirm = vi.fn();
vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({
        confirm: mockConfirm,
    }),
}));

const localVue = getLocalVue();
const TEST_WORKFLOW_ID = "test123";
const TEST_ACTION_TYPE = "upgrade_subworkflow";

describe("RefactorConfirmationModal.vue", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        vi.clearAllMocks();
        mockConfirm.mockReset();
        wrapper = shallowMount(RefactorConfirmationModal as object, {
            propsData: {
                refactorActions: [],
                workflowId: TEST_WORKFLOW_ID,
                versions: [],
            },
            localVue,
        });
    });

    it("should not attempt a dry run refactor is there are no actions", async () => {
        await wrapper.setProps({
            refactorActions: [],
        });
        expect(vi.mocked(refactor).mock.calls.length).toBe(0);
    });

    it("should call refactor on dryRun on update and pass along errors", async () => {
        vi.mocked(refactor).mockReturnValue(
            new Promise((then, error) => {
                error("foo");
            }),
        );
        await wrapper.setProps({
            refactorActions: [{ action_type: TEST_ACTION_TYPE }],
        });
        await flushPromises();
        expect(wrapper.emitted().onWorkflowError!.length).toBe(1);
        expect(vi.mocked(refactor).mock.calls[0]![0]).toEqual(TEST_WORKFLOW_ID);
        expect(vi.mocked(refactor).mock.calls[0]![3]).toBeTruthy(); // dry run argument

        // onRefactor never emitted because there was a failure
        expect(wrapper.emitted().onRefactor).toBeFalsy();
    });

    it("should call refactor on dryRun and run without dryRun if all fine", async () => {
        vi.mocked(refactor).mockReturnValue(
            new Promise((then) => {
                then({
                    action_executions: [],
                } as unknown as RefactorResponse);
            }),
        );
        await wrapper.setProps({
            refactorActions: [{ action_type: TEST_ACTION_TYPE }],
        });
        await flushPromises();
        expect(wrapper.emitted().onWorkflowError).toBeFalsy();
        // called with dry run as true...
        expect(vi.mocked(refactor).mock.calls[0]![0]).toEqual(TEST_WORKFLOW_ID);
        expect(vi.mocked(refactor).mock.calls[0]![3]).toBeTruthy();
        // ... and then as false
        expect(vi.mocked(refactor).mock.calls[1]![0]).toEqual(TEST_WORKFLOW_ID);
        expect(vi.mocked(refactor).mock.calls[1]![3]).toBeFalsy();
        // second time onRefactor emitted with the final response
        expect(wrapper.emitted().onRefactor!.length).toBe(1);
    });

    it("should show confirmation dialog if there are messages from the server", async () => {
        vi.mocked(refactor).mockReturnValue(
            new Promise((then) => {
                then({
                    action_executions: [
                        {
                            action_type: TEST_ACTION_TYPE,
                            messages: [
                                {
                                    message_type: "connection_drop_forced",
                                    message: "hey, a connection was dropped - better respond",
                                },
                            ],
                        },
                    ],
                } as unknown as RefactorResponse);
            }),
        );

        // Start with the modal hidden
        expect(wrapper.findComponent(GModal).props().show).toBeFalsy();

        await wrapper.setProps({
            refactorActions: [{ action_type: TEST_ACTION_TYPE }],
        });
        await flushPromises();
        expect(wrapper.emitted().onWorkflowError).toBeFalsy();

        // called with dry run...
        expect(vi.mocked(refactor).mock.calls[0]![0]).toEqual(TEST_WORKFLOW_ID);
        expect(vi.mocked(refactor).mock.calls[0]![3]).toBeTruthy();
        // but didn't follow up with executing the action because we need to confirm
        expect(vi.mocked(refactor).mock.calls.length).toBe(1);

        expect(wrapper.findComponent(GModal).props().show).toBeTruthy();
    });

    it("should show confirm dialog when refactoring a non-latest version", async () => {
        mockConfirm.mockResolvedValue(true);
        vi.mocked(refactor).mockResolvedValue({
            action_executions: [],
        } as unknown as RefactorResponse);

        const versions = [
            { version: 0, update_time: "2024-01-01", steps: 5 },
            { version: 1, update_time: "2024-01-02", steps: 6 },
        ];

        await wrapper.setProps({
            versions,
            version: 0, // Not the latest (latest is version 1)
            refactorActions: [{ action_type: TEST_ACTION_TYPE }],
        });
        await flushPromises();

        // Confirm dialog should have been called because we're on an older version
        expect(mockConfirm).toHaveBeenCalledTimes(1);
        expect(mockConfirm).toHaveBeenCalledWith(
            expect.stringContaining("not the latest version"),
            expect.objectContaining({
                title: "Confirm Refactor on Older Version",
            }),
        );

        // After confirming, refactor should proceed
        expect(vi.mocked(refactor)).toHaveBeenCalled();
    });

    it("should not call refactor if user cancels the non-latest version confirm dialog", async () => {
        mockConfirm.mockResolvedValue(false);

        const versions = [
            { version: 0, update_time: "2024-01-01", steps: 5 },
            { version: 1, update_time: "2024-01-02", steps: 6 },
        ];

        await wrapper.setProps({
            versions,
            version: 0, // Not the latest
            refactorActions: [{ action_type: TEST_ACTION_TYPE }],
        });
        await flushPromises();

        // Confirm dialog should have been called
        expect(mockConfirm).toHaveBeenCalledTimes(1);

        // Refactor should NOT have been called because user cancelled
        expect(vi.mocked(refactor)).not.toHaveBeenCalled();
    });

    it("should not show confirm dialog when refactoring the latest version", async () => {
        vi.mocked(refactor).mockResolvedValue({
            action_executions: [],
        } as unknown as RefactorResponse);

        const versions = [
            { version: 0, update_time: "2024-01-01", steps: 5 },
            { version: 1, update_time: "2024-01-02", steps: 6 },
        ];

        await wrapper.setProps({
            versions,
            version: 1, // This is the latest version
            refactorActions: [{ action_type: TEST_ACTION_TYPE }],
        });
        await flushPromises();

        // Confirm dialog should NOT have been called for latest version
        expect(mockConfirm).not.toHaveBeenCalled();

        // Refactor should proceed directly
        expect(vi.mocked(refactor)).toHaveBeenCalled();
    });
});
