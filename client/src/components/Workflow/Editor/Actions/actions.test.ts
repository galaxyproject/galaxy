import { createPinia, setActivePinia } from "pinia";

import { UndoRedoAction, useUndoRedoStore } from "@/stores/undoRedoStore";
import { LazyUndoRedoAction } from "@/stores/undoRedoStore/undoRedoAction";
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
    LazyMoveMultipleAction,
} from "./commentActions";
import { mockComment, mockWorkflow } from "./mockData";

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

    describe("Single Actions", () => {
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

        const { commentStore, undoRedoStore } = stores;

        describe("Comment Actions", () => {
            function addComment() {
                const comment = mockComment(commentStore.highestCommentId + 1);
                commentStore.addComments([comment]);
                return comment;
            }

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
            "activeNodeId",
            "stepPosition",
            "stepLoadingState",
        ]),
        connectionStoreState: extractKeys(connectionStore, [
            "connections",
            "invalidConnections",
            "inputTerminalToOutputTerminals",
            "terminalToConnection",
            "stepToConnections",
        ]),
        commentStoreState: extractKeys(commentStore, ["commentsRecord"]),
        workflowState: workflow,
    });

    return state;
}
