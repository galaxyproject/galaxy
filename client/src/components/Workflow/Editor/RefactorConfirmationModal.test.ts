import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { refactor, type RefactorRequestAction, type RefactorResponse, type WorkflowVersion } from "@/api/workflows";

import RefactorConfirmationModal from "./RefactorConfirmationModal.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/api/workflows", () => ({ refactor: vi.fn() }));

const { mockConfirm } = vi.hoisted(() => ({ mockConfirm: vi.fn() }));
vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: mockConfirm }),
}));

const WORKFLOW_ID = "test123";
const ACTIONS: RefactorRequestAction[] = [{ action_type: "upgrade_subworkflow", step: { order_index: 0 } }];
const VERSIONS: WorkflowVersion[] = [
    { version: 0, update_time: "2024-01-01", steps: 5 },
    { version: 1, update_time: "2024-01-02", steps: 6 },
];

function refactorResponse(
    dryRun: boolean,
    actionExecutions: RefactorResponse["action_executions"] = [],
): RefactorResponse {
    return { action_executions: actionExecutions, changed: true, dry_run: dryRun, workflow: {} };
}

function mountConfirmation() {
    return mount(RefactorConfirmationModal, {
        props: { refactorActions: [], workflowId: WORKFLOW_ID, versions: [] },
        global: getLocalVue(),
    });
}

enableAutoUnmount(afterEach);

beforeEach(() => {
    vi.mocked(refactor).mockReset();
    mockConfirm.mockReset();
});

describe("RefactorConfirmationModal", () => {
    it("does not request a dry run when the action list stays empty", async () => {
        const wrapper = mountConfirmation();
        await wrapper.setProps({ refactorActions: [] });
        expect(refactor).not.toHaveBeenCalled();
    });

    it("emits the dry-run failure without executing the refactor", async () => {
        vi.mocked(refactor).mockRejectedValue("foo");
        const wrapper = mountConfirmation();
        await wrapper.setProps({ refactorActions: ACTIONS });
        await flushPromises();
        expect(refactor).toHaveBeenCalledExactlyOnceWith(WORKFLOW_ID, ACTIONS, "editor", true, undefined);
        expect(wrapper.emitted("onWorkflowError")).toEqual([["Reworking workflow failed...", "foo"]]);
        expect(wrapper.emitted("onRefactor")).toBeUndefined();
    });

    it("executes after a message-free dry run and emits the execution response", async () => {
        const executionResponse = refactorResponse(false);
        vi.mocked(refactor).mockResolvedValueOnce(refactorResponse(true)).mockResolvedValueOnce(executionResponse);
        const wrapper = mountConfirmation();
        await wrapper.setProps({ refactorActions: ACTIONS });
        await flushPromises();
        expect(refactor).toHaveBeenCalledTimes(2);
        expect(refactor).toHaveBeenNthCalledWith(1, WORKFLOW_ID, ACTIONS, "editor", true, undefined);
        expect(refactor).toHaveBeenNthCalledWith(2, WORKFLOW_ID, ACTIONS, "editor", false, undefined);
        expect(wrapper.emitted("onWorkflowError")).toBeUndefined();
        expect(wrapper.emitted("onRefactor")).toEqual([[executionResponse]]);
    });

    it("shows server messages and waits for Proceed before executing", async () => {
        const message = "hey, a connection was dropped - better respond";
        vi.mocked(refactor)
            .mockResolvedValueOnce(
                refactorResponse(true, [
                    {
                        action: ACTIONS[0]!,
                        messages: [{ message_type: "connection_drop_forced", message }],
                    },
                ]),
            )
            .mockResolvedValueOnce(refactorResponse(false));
        const wrapper = mountConfirmation();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        await wrapper.setProps({ refactorActions: ACTIONS });
        await flushPromises();
        expect(refactor).toHaveBeenCalledExactlyOnceWith(WORKFLOW_ID, ACTIONS, "editor", true, undefined);
        expect(wrapper.emitted("onWorkflowError")).toBeUndefined();
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        expect(wrapper.find(".workflow-refactor-modal").text()).toContain(message);
        const proceedButton = wrapper
            .findComponent(GModal)
            .findAll("button")
            .find((button) => button.text() === "Proceed");
        expect(proceedButton).toBeDefined();
        await proceedButton!.trigger("click");
        await flushPromises();
        expect(refactor).toHaveBeenNthCalledWith(2, WORKFLOW_ID, ACTIONS, "editor", false, undefined);
    });

    it("asks before refactoring an older version and proceeds when confirmed", async () => {
        mockConfirm.mockResolvedValue(true);
        vi.mocked(refactor).mockResolvedValue(refactorResponse(false));
        const wrapper = mountConfirmation();
        await wrapper.setProps({ versions: VERSIONS, version: 0, refactorActions: ACTIONS });
        await flushPromises();
        expect(mockConfirm).toHaveBeenCalledTimes(1);
        expect(mockConfirm).toHaveBeenCalledWith(
            expect.stringContaining("not the latest version"),
            expect.objectContaining({ title: "Confirm Refactor on Older Version" }),
        );
        expect(refactor).toHaveBeenNthCalledWith(1, WORKFLOW_ID, ACTIONS, "editor", true, 0);
        expect(refactor).toHaveBeenNthCalledWith(2, WORKFLOW_ID, ACTIONS, "editor", false, 0);
    });

    it("does not refactor an older version when its confirmation is cancelled", async () => {
        mockConfirm.mockResolvedValue(false);
        const wrapper = mountConfirmation();
        await wrapper.setProps({ versions: VERSIONS, version: 0, refactorActions: ACTIONS });
        await flushPromises();
        expect(mockConfirm).toHaveBeenCalledTimes(1);
        expect(refactor).not.toHaveBeenCalled();
    });

    it("refactors the latest version without asking for version confirmation", async () => {
        vi.mocked(refactor).mockResolvedValue(refactorResponse(false));
        const wrapper = mountConfirmation();
        await wrapper.setProps({ versions: VERSIONS, version: 1, refactorActions: ACTIONS });
        await flushPromises();
        expect(mockConfirm).not.toHaveBeenCalled();
        expect(refactor).toHaveBeenNthCalledWith(1, WORKFLOW_ID, ACTIONS, "editor", true, 1);
        expect(refactor).toHaveBeenNthCalledWith(2, WORKFLOW_ID, ACTIONS, "editor", false, 1);
    });
});
