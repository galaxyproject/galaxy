import {
    faCopy,
    faDownload,
    faEdit,
    faFileExport,
    faLink,
    faPlay,
    faPlusSquare,
    faShareAlt,
    faTrash,
    faTrashRestore,
    faUpload,
} from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { computed, type Ref } from "vue";

import { undeleteWorkflow } from "@/api/workflows";
import { type WorkflowSummary } from "@/api/workflows";
import { type CardAttributes } from "@/components/Common/GCard.types";
import {
    copyWorkflow as copyWorkflowService,
    deleteWorkflow as deleteWorkflowService,
    updateWorkflow as updateWorkflowService,
} from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { copy } from "@/utils/clipboard";
import { withPrefix } from "@/utils/redirect";
import { getFullAppUrl } from "@/utils/utils";

export function useWorkflowCardActions(
    workflow: Ref<WorkflowSummary>,
    current: boolean,
    editorView: boolean,
    refreshCallback: () => void,
    insertSteps: () => void,
    insert: () => void
) {
    const userStore = useUserStore();
    const { isAnonymous } = storeToRefs(userStore);

    const { confirm } = useConfirmDialog();
    const toast = useToast();

    const shared = computed(() => {
        return !userStore.matchesCurrentUsername(workflow.value.owner);
    });
    const relativeLink = computed(() => {
        return `/published/workflow?id=${workflow.value.id}`;
    });
    const fullLink = computed(() => {
        return getFullAppUrl(relativeLink.value.substring(1));
    });
    const downloadUrl = computed(() => {
        return withPrefix(`/api/workflows/${workflow.value.id}/download?format=json-download`);
    });
    const editButtonTitle = computed(() => {
        if (isAnonymous.value) {
            return "Log in to edit Workflow";
        } else {
            if (workflow.value.deleted) {
                return "You cannot edit a deleted workflow. Restore it first.";
            } else {
                return "Edit Workflow";
            }
        }
    });
    const importedButtonTitle = computed(() => {
        if (isAnonymous.value) {
            return "Log in to import workflow";
        } else {
            return "Import this workflow to edit";
        }
    });
    const runButtonTitle = computed(() => {
        if (isAnonymous.value) {
            return "Log in to run workflow";
        } else {
            if (workflow.value.deleted) {
                return "You cannot run a deleted workflow. Restore it first.";
            } else {
                return "Run workflow";
            }
        }
    });

    const toggleBookmark = async (checked: boolean) => {
        try {
            await updateWorkflowService(workflow.value.id, {
                show_in_tool_panel: checked,
            });

            toast.info(`Workflow ${checked ? "added to" : "removed from"} bookmarks`);
        } catch (error) {
            toast.error("Failed to update workflow bookmark status");
        } finally {
            refreshCallback();
        }
    };

    async function deleteWorkflow() {
        const confirmed = await confirm("Are you sure you want to delete this workflow?", {
            title: "Delete workflow",
            okTitle: "Delete",
            okVariant: "danger",
        });

        if (confirmed) {
            await deleteWorkflowService(workflow.value.id);
            refreshCallback();
            toast.info("Workflow deleted");
        }
    }

    async function onRestore() {
        const confirmed = await confirm("Are you sure you want to restore this workflow?", "Restore workflow");

        if (confirmed) {
            await undeleteWorkflow(workflow.value.id);
            // emit("refreshList", true);
            refreshCallback();
            toast.info("Workflow restored");
        }
    }

    function copyPublicLink() {
        copy(fullLink.value);
        toast.success("Link to workflow copied");
    }

    async function copyWorkflow() {
        const confirmed = await confirm("Are you sure you want to make a copy of this workflow?", "Copy workflow");

        if (confirmed) {
            await copyWorkflowService(workflow.value.id, workflow.value.owner);
            refreshCallback();
            toast.success("Workflow copied");
        }
    }

    async function importWorkflow() {
        await copyWorkflowService(workflow.value.id, workflow.value.owner);
        toast.success("Workflow imported successfully");
    }

    const _workflowRunAction: CardAttributes = {
        id: "workflow-run",
        label: editorView ? "Run" : "",
        icon: faPlay,
        title: runButtonTitle.value,
        disabled: isAnonymous.value || workflow.value.deleted,
        to: `/workflows/run?id=${workflow.value.id}`,
        visible: true,
    };

    const _workflowCommonActions: CardAttributes[] = [
        {
            id: "workflow-link",
            label: "Link to Workflow",
            icon: faLink,
            title: "Copy link to workflow",
            handler: copyPublicLink,
            visible: !workflow.value.deleted && workflow.value.published,
        },
        {
            id: "workflow-copy",
            label: "Copy",
            icon: faCopy,
            title: "Copy workflow",
            handler: copyWorkflow,
            visible: !workflow.value.deleted && !isAnonymous.value && !shared.value,
        },
        {
            id: "workflow-download",
            label: "Download",
            icon: faDownload,
            title: "Download workflow in .ga format",
            href: downloadUrl.value,
            visible: !workflow.value.deleted,
        },
        {
            id: "workflow-share",
            label: "Share",
            icon: faShareAlt,
            title: "Share",
            to: `/workflows/sharing?id=${workflow.value.id}`,
            visible: !workflow.value.deleted && !isAnonymous.value && !shared.value,
        },
    ];

    const workflowCardExtraActions: CardAttributes[] = [
        {
            id: "workflow-delete",
            label: "Delete",
            icon: faTrash,
            title: "Delete workflow",
            handler: deleteWorkflow,
            visible: !isAnonymous.value && !shared.value && !workflow.value.deleted && !current,
        },
        {
            id: "workflow-export",
            label: "Export",
            icon: faFileExport,
            title: "Export workflow",
            to: `/workflows/export?id=${workflow.value.id}`,
            visible: !workflow.value.deleted,
        },
    ];

    const workflowCardSecondaryActions: CardAttributes[] = [
        {
            id: "workflow-restore",
            label: "Restore",
            icon: faTrashRestore,
            title: "Restore",
            handler: onRestore,
            visible: workflow.value.deleted,
        },
        {
            id: "workflow-copy-steps",
            label: "",
            icon: faCopy,
            title: "Copy steps into workflow",
            variant: "outline-primary",
            handler: insertSteps,
            visible: editorView && !workflow.value.deleted,
        },
        {
            id: "workflow-insert",
            label: "Insert",
            icon: faPlusSquare,
            title: "Insert as sub-workflow",
            variant: "primary",
            handler: insert,
            visible: editorView && !workflow.value.deleted && !current,
        },
    ];

    const workflowCardPrimaryActions: CardAttributes[] = [
        {
            id: "workflow-edit",
            label: "Edit",
            icon: faEdit,
            title: editButtonTitle.value,
            disabled: workflow.value.deleted,
            variant: "outline-primary",
            visible: !isAnonymous.value && !current && !shared.value,
            to: `/workflows/edit?id=${workflow.value.id}`,
        },
        {
            id: "workflow-import",
            label: "Import",
            icon: faUpload,
            title: importedButtonTitle.value,
            disabled: isAnonymous.value,
            variant: "outline-primary",
            handler: importWorkflow,
            visible: (isAnonymous.value || shared.value) && !current,
        },
    ];

    if (editorView) {
        workflowCardExtraActions.unshift(..._workflowCommonActions);
    } else {
        workflowCardSecondaryActions.unshift(..._workflowCommonActions);
    }

    if (!editorView) {
        workflowCardPrimaryActions.push(_workflowRunAction);
    } else {
        workflowCardExtraActions.unshift(_workflowRunAction);
    }

    return {
        workflowCardExtraActions,
        workflowCardSecondaryActions,
        workflowCardPrimaryActions,
        toggleBookmark,
    };
}
