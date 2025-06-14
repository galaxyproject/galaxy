import { inject, onScopeDispose, provide, type Ref, ref, unref } from "vue";

import { useUndoRedoStore } from "@/stores/undoRedoStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowCommentStore } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowEditorToolbarStore } from "@/stores/workflowEditorToolbarStore";
import { useWorkflowSearchStore } from "@/stores/workflowSearchStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

import { useTimeoutStoreDispose } from "./timeoutStoreDispose";

/**
 * Creates stores scoped to a specific workflowId, and manages their lifetime.
 * In child components, use `useWorkflowStores` instead.
 *
 * Provides `workflowId` to all child components.
 *
 * @param workflowId the workflow to scope to
 * @returns workflow Stores
 */
export function provideScopedWorkflowStores(workflowId: Ref<string> | string) {
    if (typeof workflowId === "string") {
        workflowId = ref(workflowId);
    }

    provide("workflowId", workflowId);

    const connectionStore = useConnectionStore(workflowId.value);
    const stateStore = useWorkflowStateStore(workflowId.value);
    const stepStore = useWorkflowStepStore(workflowId.value);
    const commentStore = useWorkflowCommentStore(workflowId.value);
    const toolbarStore = useWorkflowEditorToolbarStore(workflowId.value);
    const undoRedoStore = useUndoRedoStore(workflowId.value);
    const searchStore = useWorkflowSearchStore(workflowId.value);

    const disposeConnectionStore = useTimeoutStoreDispose(connectionStore);
    const disposeStateStore = useTimeoutStoreDispose(stateStore);
    const disposeStepStore = useTimeoutStoreDispose(stepStore);
    const disposeCommentStore = useTimeoutStoreDispose(commentStore);
    const disposeToolbarStore = useTimeoutStoreDispose(toolbarStore);
    const disposeUndoRedoStore = useTimeoutStoreDispose(undoRedoStore);
    const disposeSearchStore = useTimeoutStoreDispose(searchStore);

    onScopeDispose(() => {
        disposeConnectionStore();
        disposeStateStore();
        disposeStepStore();
        disposeCommentStore();
        disposeToolbarStore();
        disposeUndoRedoStore();
        disposeSearchStore();
    });

    return {
        connectionStore,
        stateStore,
        stepStore,
        commentStore,
        toolbarStore,
        undoRedoStore,
        searchStore,
    };
}

/**
 * Uses all workflow related stores scoped to the workflow defined by a parent component.
 * Does not manage lifetime.
 *
 * `provideScopedWorkflowStores` needs to be called by a parent component,
 * or this composable will throw an error.
 *
 * @returns workflow stores
 */
export function useWorkflowStores(workflowId?: Ref<string> | string) {
    workflowId = workflowId ?? (inject("workflowId") as Ref<string> | string);
    const id = unref(workflowId);

    if (typeof id !== "string") {
        throw new Error(
            "Workflow ID not provided by parent component. Use `provideScopedWorkflowStores` on a parent component."
        );
    }

    const connectionStore = useConnectionStore(id);
    const stateStore = useWorkflowStateStore(id);
    const stepStore = useWorkflowStepStore(id);
    const commentStore = useWorkflowCommentStore(id);
    const toolbarStore = useWorkflowEditorToolbarStore(id);
    const undoRedoStore = useUndoRedoStore(id);
    const searchStore = useWorkflowSearchStore(id);

    return {
        workflowId: id,
        connectionStore,
        stateStore,
        stepStore,
        commentStore,
        toolbarStore,
        undoRedoStore,
        searchStore,
    };
}
