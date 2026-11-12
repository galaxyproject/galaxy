import { faEye, faHdd, faLink, faRedo, faSitemap, faStopCircle } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { ref } from "vue";
import { useRouter } from "vue-router";

import { userOwnsHistory } from "@/api";
import type { WorkflowInvocation } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { getFullAppUrl } from "@/app/utils";
import type { TableAction } from "@/components/Common/GTable.types";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useInvocationStore } from "@/stores/invocationStore";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { copy } from "@/utils/clipboard";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { INVOCATION_STATE_GROUPS } from "./invocationFilters";

interface Options {
    /** Opens an invocation, as the list does (e.g. in a new tab for a batch run) */
    viewInvocation: (invocation: WorkflowInvocation) => void;
    /** Reloads the list, e.g. to show a cancelled invocation's new state */
    refreshList: () => Promise<void>;
}

/**
 * The options at the end of each `InvocationList` row, grouped by what they act on, with Cancel apart.
 * They only read workflows and histories the list has already loaded.
 */
export function useInvocationListItemActions({ viewInvocation, refreshList }: Options) {
    const router = useRouter();
    const workflowStore = useWorkflowStore();
    const historyStore = useHistoryStore();
    const userStore = useUserStore();
    const { currentUser } = storeToRefs(userStore);

    /** The workflow version the invocation ran, once the list has loaded it */
    function storedWorkflow(invocation: WorkflowInvocation) {
        return workflowStore.getStoredWorkflowByInstanceId(invocation.workflow_id) as
            | StoredWorkflowDetailed
            | undefined;
    }

    /**
     * Why the invocation can't be rerun, if it can't: rerunning switches to its history, then runs its workflow,
     * so both must be usable. A workflow the user can't access never loads.
     */
    function rerunBlockedReason(invocation: WorkflowInvocation) {
        const workflow = storedWorkflow(invocation);
        const history = historyStore.getHistoryById(invocation.history_id, false);
        if (!workflow) {
            return "This workflow isn't available to you, so it can't be run again";
        } else if (workflow.deleted) {
            return "This workflow has been deleted, so it can't be run again";
        } else if (!history || !currentUser.value || !userOwnsHistory(currentUser.value, history)) {
            return "Rerunning switches to this invocation's history, which isn't yours";
        } else if (history.purged || history.archived) {
            return `Rerunning switches to this invocation's history, which is ${history.purged ? "purged" : "archived"}`;
        }
        return undefined;
    }

    function ownsHistory(invocation: WorkflowInvocation) {
        const history = historyStore.getHistoryById(invocation.history_id, false);
        return !!history && !!currentUser.value && userOwnsHistory(currentUser.value, history);
    }

    /** The workflow version to preview in the list's modal, as the workflow list's cards do */
    const workflowPreview = ref<{ id: string; version?: number } | null>(null);

    /** Previews the exact workflow version the invocation ran, read-only */
    function viewWorkflow(invocation: WorkflowInvocation) {
        const workflow = storedWorkflow(invocation)!;
        workflowPreview.value = { id: workflow.id, version: workflow.version ?? undefined };
    }

    /** Cancels an invocation that is still active, then reloads the list to show its new state */
    async function cancelInvocation(invocation: WorkflowInvocation) {
        try {
            await useInvocationStore().cancelWorkflowScheduling(invocation.id);
            Toast.success("Cancelling the invocation.");
        } catch (e) {
            Toast.error(errorMessageAsString(e), localize("Failed to cancel the invocation"));
        }
        await refreshList();
    }

    const invocationListItemActions: TableAction[] = [
        {
            id: "rerun-invocation",
            groupId: "invocation",
            label: "Rerun",
            title: (invocation: WorkflowInvocation) =>
                rerunBlockedReason(invocation) ?? "Rerun this workflow with the same inputs",
            icon: faRedo,
            disabled: (invocation: WorkflowInvocation) => !!rerunBlockedReason(invocation),
            handler: (invocation: WorkflowInvocation) => router.push(`/workflows/rerun?invocation_id=${invocation.id}`),
        },
        {
            id: "view-invocation",
            groupId: "invocation",
            label: "View invocation",
            title: "View this invocation",
            icon: faEye,
            handler: viewInvocation,
        },
        {
            id: "copy-invocation-link",
            groupId: "invocation",
            label: "Copy link",
            title: "Copy a link to this invocation",
            icon: faLink,
            handler: (invocation: WorkflowInvocation) =>
                copy(getFullAppUrl(`workflows/invocations/${invocation.id}`), "Link to invocation copied"),
        },
        {
            id: "view-workflow",
            groupId: "workflow",
            label: "View workflow",
            title: "View the workflow version this invocation ran",
            icon: faSitemap,
            visible: (invocation: WorkflowInvocation) => !!storedWorkflow(invocation),
            handler: viewWorkflow,
        },
        {
            id: "view-history",
            groupId: "history",
            label: "View history",
            title: "View this invocation's history without switching to it",
            icon: faHdd,
            visible: ownsHistory,
            handler: (invocation: WorkflowInvocation) => router.push(`/histories/view?id=${invocation.history_id}`),
        },
        {
            id: "cancel-invocation",
            groupId: "stop",
            label: "Cancel",
            title: "Cancel this invocation",
            icon: faStopCircle,
            visible: (invocation: WorkflowInvocation) =>
                (INVOCATION_STATE_GROUPS.active as readonly string[]).includes(invocation.state),
            handler: cancelInvocation,
        },
    ];

    return { invocationListItemActions, storedWorkflow, workflowPreview };
}
