import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setupTestPinia } from "@/stores/testUtils";
import { LazyUndoRedoAction, type UndoRedoAction, useUndoRedoStore } from "@/stores/undoRedoStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowCommentStore } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";
import { cloneRaw, toRawDeep } from "@/utils/toRawDeep";

import { fromSimple, type Workflow } from "../modules/model";
import {
    AddCommentAction,
    ChangeColorAction,
    DeleteCommentAction,
    LazyChangeDataAction,
    LazyChangePositionAction,
    LazyChangeSizeAction,
    RemoveAllFreehandCommentsAction,
    ToggleCommentSelectedAction,
} from "./commentActions";
import { mockComment, mockFreehandComment, mockToolStep, mockWorkflow } from "./mockData";
import {
    CopyStepAction,
    InsertStepAction,
    LazyMutateStepAction,
    LazySetLabelAction,
    LazySetOutputLabelAction,
    RemoveStepAction,
    ToggleStepSelectedAction,
    UpdateStepAction,
} from "./stepActions";
import {
    AddToSelectionAction,
    ClearSelectionAction,
    CopyIntoWorkflowAction,
    DeleteSelectionAction,
    DuplicateSelectionAction,
    LazyMoveMultipleAction,
    LazySetValueAction,
    RemoveFromSelectionAction,
} from "./workflowActions";

const workflowId = "mock-workflow";

describe("Workflow Undo Redo Actions", () => {
    let workflow: Workflow;
    let stores: ReturnType<typeof createStores>;
    let commentStore: ReturnType<typeof useWorkflowCommentStore>;
    let undoRedoStore: ReturnType<typeof useUndoRedoStore>;
    let stepStore: ReturnType<typeof useWorkflowStepStore>;
    let stateStore: ReturnType<typeof useWorkflowStateStore>;
    let connectionStore: ReturnType<typeof useConnectionStore>;

    beforeEach(async () => {
        vi.useFakeTimers();
        setupTestPinia();
        workflow = mockWorkflow();
        stores = createStores();
        ({ commentStore, undoRedoStore, stepStore, stateStore, connectionStore } = stores);

        await fromSimple(workflowId, workflow);
    });

    afterEach(() => {
        undoRedoStore.clearLazyAction();
        Object.values(stores).forEach((store) => store.$dispose());
        vi.clearAllTimers();
        vi.useRealTimers();
    });

    function testUndoRedo(action: UndoRedoAction | LazyUndoRedoAction, afterApplyCallback?: () => void) {
        const beforeApplyAction = getWorkflowSnapshot(workflow);

        if (action instanceof LazyUndoRedoAction) {
            undoRedoStore.applyLazyAction(action);
            undoRedoStore.flushLazyAction();
        } else {
            undoRedoStore.applyAction(action);
        }

        afterApplyCallback?.();

        const afterApplyActionSnapshot = getWorkflowSnapshot(workflow);
        expect(afterApplyActionSnapshot).not.toEqual(beforeApplyAction);

        stores.undoRedoStore.undo();

        const undoSnapshot = getWorkflowSnapshot(workflow);
        expect(undoSnapshot).toEqual(beforeApplyAction);

        stores.undoRedoStore.redo();

        const redoSnapshot = getWorkflowSnapshot(workflow);
        expect(redoSnapshot).toEqual(afterApplyActionSnapshot);
    }

    function addComment() {
        const comment = mockComment(commentStore.highestCommentId + 1);
        commentStore.addComments([comment]);
        return comment;
    }

    function addFreehandComment() {
        const comment = mockFreehandComment(commentStore.highestCommentId + 1);
        commentStore.addComments([comment]);
        return comment;
    }

    function addStep() {
        const step = mockToolStep(stepStore.getStepIndex + 1);
        stepStore.addStep(step);
        return step;
    }

    describe("Comment Actions", () => {
        it("adds a comment", () => {
            expect(commentStore.comments.length).toBe(0);

            const comment = mockComment(0);
            const insertAction = new AddCommentAction(commentStore, comment);

            testUndoRedo(insertAction, () => commentStore.addComments([comment]));
        });

        it("deletes a comment", () => {
            const comment = addComment();
            const action = new DeleteCommentAction(commentStore, comment);
            testUndoRedo(action);
        });

        it("changes a comment color", () => {
            const comment = addComment();
            const action = new ChangeColorAction(commentStore, comment, "pink");
            testUndoRedo(action);
        });

        it("changes comment data", () => {
            const comment = addComment();
            const action = new LazyChangeDataAction(commentStore, comment, { text: "abc", size: 1 });
            testUndoRedo(action);
        });

        it("moves a comment", () => {
            const comment = addComment();
            const action = new LazyChangePositionAction(commentStore, comment, [20, 80]);
            testUndoRedo(action);
        });

        it("resizes a comment", () => {
            const comment = addComment();
            const action = new LazyChangeSizeAction(commentStore, comment, [1000, 1000]);
            testUndoRedo(action);
        });

        it("toggles comment selection", () => {
            const comment = addComment();
            const action = new ToggleCommentSelectedAction(commentStore, comment);
            testUndoRedo(action);
        });

        it("removes all freehand comments", () => {
            addFreehandComment();
            addFreehandComment();
            addFreehandComment();

            const action = new RemoveAllFreehandCommentsAction(commentStore);
            testUndoRedo(action);
        });
    });

    describe("Workflow Actions", () => {
        it("changes workflow tags", () => {
            const setValueCallback = (tags: string[]) => {
                workflow.tags = tags;
            };

            const showCanvasCallback = vi.fn();

            const action = new LazySetValueAction([], ["hello", "world"], setValueCallback, showCanvasCallback);
            testUndoRedo(action);

            expect(showCanvasCallback).toBeCalledTimes(2);
        });

        it("copies another workflow", () => {
            const other = mockWorkflow();
            const action = new CopyIntoWorkflowAction(workflowId, other, { left: 10, top: 20 });
            testUndoRedo(action);
        });

        it("moves steps and comments together", () => {
            addComment();
            const action = new LazyMoveMultipleAction(
                commentStore,
                stepStore,
                commentStore.comments,
                Object.values(stepStore.steps).map((step) => ({
                    ...step,
                    position: ensureDefined(step.position),
                })),
                { x: 0, y: 0 },
                { x: 500, y: 500 },
            );
            testUndoRedo(action);
        });

        function setupSelected() {
            addComment();
            addComment();
            addStep();
            addStep();
            commentStore.setCommentMultiSelected(0, true);
            stateStore.setStepMultiSelected(2, true);
        }

        it("clears selection", () => {
            setupSelected();
            const action = new ClearSelectionAction(commentStore, stateStore);
            testUndoRedo(action);
        });

        it("adds steps and comments to selection", () => {
            setupSelected();
            const action = new AddToSelectionAction(commentStore, stateStore, { comments: [1], steps: [0] });
            testUndoRedo(action);
        });

        it("removes steps and comments from selection", () => {
            setupSelected();
            const action = new RemoveFromSelectionAction(commentStore, stateStore, { comments: [0], steps: [2] });
            testUndoRedo(action);
        });

        it("duplicates selected steps and comments", () => {
            setupSelected();
            const action = new DuplicateSelectionAction(workflowId);
            testUndoRedo(action);
        });

        it("deletes selected steps and comments", () => {
            setupSelected();
            const action = new DeleteSelectionAction(workflowId);
            testUndoRedo(action);
        });
    });

    describe("Step Actions", () => {
        it("changes a step annotation", () => {
            const step = addStep();
            const action = new LazyMutateStepAction(stepStore, step.id, "annotation", "", "hello world");
            testUndoRedo(action);
        });

        it("updates step outputs", () => {
            const step = addStep();
            const action = new UpdateStepAction(
                stepStore,
                stateStore,
                step.id,
                {
                    outputs: step.outputs,
                },
                {
                    outputs: [{ name: "output", extensions: ["input"], type: "data", optional: true }],
                },
            );
            testUndoRedo(action);
        });

        it("inserts a step", () => {
            const step = mockToolStep(1);
            const action = new InsertStepAction(stepStore, stateStore, {
                contentId: "mock",
                name: "step",
                type: "tool",
                position: { left: 0, top: 0 },
            });
            action.updateStepData = step;
            testUndoRedo(action);
        });

        it("removes a step", () => {
            const step = addStep();
            const action = new RemoveStepAction(stepStore, stateStore, connectionStore, step);
            testUndoRedo(action);
        });

        it("copies a step", () => {
            const step = addStep();
            const action = new CopyStepAction(stepStore, stateStore, step);
            testUndoRedo(action);
        });

        it("changes a step label", () => {
            const step = addStep();
            const action = new LazySetLabelAction(stepStore, stateStore, step.id, step.label, "custom_label");
            testUndoRedo(action);
        });

        it("changes an output label", () => {
            const step = addStep();
            const action = new LazySetOutputLabelAction(stepStore, stateStore, step.id, null, "abc", [
                {
                    label: "abc",
                    output_name: "out_file1",
                },
            ]);

            testUndoRedo(action);
        });

        it("toggles step selection", () => {
            const step = addStep();
            const action = new ToggleStepSelectedAction(stateStore, stepStore, step.id);
            testUndoRedo(action);
        });
    });
});

function createStores(id = workflowId) {
    const stepStore = useWorkflowStepStore(id);
    const stateStore = useWorkflowStateStore(id);
    const connectionStore = useConnectionStore(id);
    const commentStore = useWorkflowCommentStore(id);
    const undoRedoStore = useUndoRedoStore(id);

    return {
        stepStore,
        stateStore,
        commentStore,
        connectionStore,
        undoRedoStore,
    };
}

function extractKeys<O extends object>(object: O, keys: (keyof O)[]): Partial<O> {
    const extracted: Partial<O> = {};

    keys.forEach((key) => {
        extracted[key] = toRawDeep(object[key]);
    });

    return extracted;
}

function getWorkflowSnapshot(workflow: Workflow, id = workflowId): object {
    const stepStore = useWorkflowStepStore(id);
    const stateStore = useWorkflowStateStore(id);
    const connectionStore = useConnectionStore(id);
    const commentStore = useWorkflowCommentStore(id);

    const state = {
        stepStoreState: extractKeys(stepStore, ["steps", "stepExtraInputs", "stepInputMapOver", "stepMapOver"]),
        stateStoreState: extractKeys(stateStore, [
            "inputTerminals",
            "outputTerminals",
            "stepPosition",
            "stepLoadingState",
            "report",
            "multiSelectedStepIds",
        ]),
        connectionStoreState: extractKeys(connectionStore, [
            "connections",
            "invalidConnections",
            "inputTerminalToOutputTerminals",
            "terminalToConnection",
            "stepToConnections",
        ]),
        commentStoreState: extractKeys(commentStore, ["commentsRecord", "multiSelectedCommentIds"]),
        workflowState: workflow,
    };

    return cloneRaw(state);
}
