import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { refactor } from "./modules/services";

import RefactorConfirmationModal from "./RefactorConfirmationModal.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("./modules/services", () => ({
    refactor: vi.fn(),
}));

const localVue = getLocalVue();
const TEST_WORKFLOW_ID = "test123";
const TEST_ACTION_TYPE = "upgrade_subworkflow";

describe("RefactorConfirmationModal.vue", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        vi.clearAllMocks();
        wrapper = shallowMount(RefactorConfirmationModal as object, {
            propsData: {
                refactorActions: [],
                workflowId: TEST_WORKFLOW_ID,
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
        expect(vi.mocked(refactor).mock.calls[0]![2]).toBeTruthy(); // dry run argument

        // onRefactor never emitted because there was a failure
        expect(wrapper.emitted().onRefactor).toBeFalsy();
    });

    it("should call refactor on dryRun and run without dryRun if all fine", async () => {
        vi.mocked(refactor).mockReturnValue(
            new Promise((then) => {
                then({
                    action_executions: [],
                });
            }),
        );
        await wrapper.setProps({
            refactorActions: [{ action_type: TEST_ACTION_TYPE }],
        });
        await flushPromises();
        expect(wrapper.emitted().onWorkflowError).toBeFalsy();
        // called with dry run as true...
        expect(vi.mocked(refactor).mock.calls[0]![0]).toEqual(TEST_WORKFLOW_ID);
        expect(vi.mocked(refactor).mock.calls[0]![2]).toBeTruthy();
        // ... and then as false
        expect(vi.mocked(refactor).mock.calls[1]![0]).toEqual(TEST_WORKFLOW_ID);
        expect(vi.mocked(refactor).mock.calls[1]![2]).toBeFalsy();
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
                });
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
        expect(vi.mocked(refactor).mock.calls[0]![2]).toBeTruthy();
        // but didn't follow up with executing the action because we need to confirm
        expect(vi.mocked(refactor).mock.calls.length).toBe(1);

        expect(wrapper.findComponent(GModal).props().show).toBeTruthy();
    });
});
