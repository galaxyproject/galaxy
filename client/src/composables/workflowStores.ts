import { inject, onScopeDispose, provide } from "vue";

import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

/**
 * Creates stores scoped to a specific workflowId, and manages their lifetime.
 * In child components, use `useWorkflowStores` instead.
 *
 * Provides `workflowId` to all child components.
 *
 * @param workflowId the workflow to scope to
 * @returns workflow Stores
 */
export function provideScopedWorkflowStores(workflowId: string) {
    provide("workflowId", workflowId);

    const connectionStore = useConnectionStore(workflowId);
    const stateStore = useWorkflowStateStore(workflowId);
    const stepStore = useWorkflowStepStore(workflowId);

    onScopeDispose(() => {
        connectionStore.$dispose();
        stateStore.$dispose();
        stepStore.$dispose();
    });

    return {
        connectionStore,
        stateStore,
        stepStore,
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
export function useWorkflowStores() {
    const workflowId = inject("workflowId");

    if (typeof workflowId !== "string") {
        throw new Error(
            "Workflow ID not provided by parent component. Use `setupWorkflowStores` on a parent component."
        );
    }

    const connectionStore = useConnectionStore(workflowId);
    const stateStore = useWorkflowStateStore(workflowId);
    const stepStore = useWorkflowStepStore(workflowId);

    return {
        connectionStore,
        stateStore,
        stepStore,
    };
}
