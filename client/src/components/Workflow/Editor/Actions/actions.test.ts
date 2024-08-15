import { createPinia, setActivePinia } from "pinia";

import { LazyUndoRedoAction, type UndoRedoAction, useUndoRedoStore } from "@/stores/undoRedoStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowCommentStore } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

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
    jest.useFakeTimers();

    const pinia = createPinia();
    setActivePinia(pinia);

    let workflow = mockWorkflow();
    let stores = resetStores();

    beforeEach(async () => {
        workflow = mockWorkflow();
        stores = resetStores();

        await fromSimple(workflowId, workflow);
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

    const { commentStore, undoRedoStore, stepStore, stateStore, connectionStore } = stores;

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
        it("AddCommentAction", () => {
            expect(commentStore.comments.length).toBe(0);

            const comment = mockComment(0);
            const insertAction = new AddCommentAction(commentStore, comment);

            testUndoRedo(insertAction, () => commentStore.addComments([comment]));
        });

        it("DeleteCommentAction", () => {
            const comment = addComment();
            const action = new DeleteCommentAction(commentStore, comment);
            testUndoRedo(action);
        });

        it("ChangeColorAction", () => {
            const comment = addComment();
            const action = new ChangeColorAction(commentStore, comment, "pink");
            testUndoRedo(action);
        });

        it("LazyChangeDataAction", () => {
            const comment = addComment();
            const action = new LazyChangeDataAction(commentStore, comment, { text: "abc", size: 1 });
            testUndoRedo(action);
        });

        it("LazyChangePositionAction", () => {
            const comment = addComment();
            const action = new LazyChangePositionAction(commentStore, comment, [20, 80]);
            testUndoRedo(action);
        });

        it("LazyChangeSizeAction", () => {
            const comment = addComment();
            const action = new LazyChangeSizeAction(commentStore, comment, [1000, 1000]);
            testUndoRedo(action);
        });

        it("ToggleCommentSelectedAction", () => {
            const comment = addComment();
            const action = new ToggleCommentSelectedAction(commentStore, comment);
            testUndoRedo(action);
        });

        it("RemoveAllFreehandCommentsAction", () => {
            addFreehandComment();
            addFreehandComment();
            addFreehandComment();

            const action = new RemoveAllFreehandCommentsAction(commentStore);
            testUndoRedo(action);
        });
    });

    describe("Workflow Actions", () => {
        it("LazySetValueAction", () => {
            const setValueCallback = (tags: string[]) => {
                workflow.tags = tags;
            };

            const showCanvasCallback = jest.fn();

            const action = new LazySetValueAction([], ["hello", "world"], setValueCallback, showCanvasCallback);
            testUndoRedo(action);

            expect(showCanvasCallback).toBeCalledTimes(2);
        });

        it("CopyIntoWorkflowAction", () => {
            const other = mockWorkflow();
            const action = new CopyIntoWorkflowAction(workflowId, other, { left: 10, top: 20 });
            testUndoRedo(action);
        });

        it("LazyMoveMultipleAction", () => {
            addComment();
            const action = new LazyMoveMultipleAction(
                commentStore,
                stores.stepStore,
                commentStore.comments,
                Object.values(stores.stepStore.steps) as any,
                { x: 0, y: 0 },
                { x: 500, y: 500 }
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

        it("ClearSelectionAction", () => {
            setupSelected();
            const action = new ClearSelectionAction(commentStore, stateStore);
            testUndoRedo(action);
        });

        it("AddToSelectionAction", () => {
            setupSelected();
            const action = new AddToSelectionAction(commentStore, stateStore, { comments: [1], steps: [0] });
            testUndoRedo(action);
        });

        it("RemoveFromSelectionAction", () => {
            setupSelected();
            const action = new RemoveFromSelectionAction(commentStore, stateStore, { comments: [0], steps: [2] });
            testUndoRedo(action);
        });

        it("DuplicateSelectionAction", () => {
            setupSelected();
            const action = new DuplicateSelectionAction(workflowId);
            testUndoRedo(action);
        });

        it("DeleteSelectionAction", () => {
            setupSelected();
            const action = new DeleteSelectionAction(workflowId);
            testUndoRedo(action);
        });
    });

    describe("Step Actions", () => {
        it("LazyMutateStepAction", () => {
            const step = addStep();
            const action = new LazyMutateStepAction(stepStore, step.id, "annotation", "", "hello world");
            testUndoRedo(action);
        });

        it("UpdateStepAction", () => {
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
                }
            );
            testUndoRedo(action);
        });

        it("InsertStepAction", () => {
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

        it("RemoveStepAction", () => {
            const step = addStep();
            const showAttributesCallback = jest.fn();
            const action = new RemoveStepAction(stepStore, stateStore, connectionStore, showAttributesCallback, step);
            testUndoRedo(action);

            expect(showAttributesCallback).toBeCalledTimes(2);
        });

        it("CopyStepAction", () => {
            const step = addStep();
            const action = new CopyStepAction(stepStore, stateStore, step);
            testUndoRedo(action);
        });

        it("LazySetLabelAction", () => {
            const step = addStep();
            const action = new LazySetLabelAction(stepStore, stateStore, step.id, step.label, "custom_label");
            testUndoRedo(action);
        });

        it("LazySetOutputLabelAction", () => {
            const step = addStep();
            const action = new LazySetOutputLabelAction(stepStore, stateStore, step.id, null, "abc", [
                {
                    label: "abc",
                    output_name: "out_file1",
                },
            ]);

            testUndoRedo(action);
        });

        it("ToggleStepSelectedAction", () => {
            const step = addStep();
            const action = new ToggleStepSelectedAction(stateStore, stepStore, step.id);
            testUndoRedo(action);
        });
    });
});

function resetStores(id = workflowId) {
    const stepStore = useWorkflowStepStore(id);
    const stateStore = useWorkflowStateStore(id);
    const connectionStore = useConnectionStore(id);
    const commentStore = useWorkflowCommentStore(id);
    const undoRedoStore = useUndoRedoStore(id);

    stepStore.$reset();
    stateStore.$reset();
    connectionStore.$reset();
    commentStore.$reset();
    undoRedoStore.$reset();

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
        extracted[key] = object[key];
    });

    return extracted;
}

function getWorkflowSnapshot(workflow: Workflow, id = workflowId): object {
    const stepStore = useWorkflowStepStore(id);
    const stateStore = useWorkflowStateStore(id);
    const connectionStore = useConnectionStore(id);
    const commentStore = useWorkflowCommentStore(id);

    const state = structuredClone({
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
    });

    return state;
}
