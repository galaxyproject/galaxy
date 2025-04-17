import { faSave as farSave } from "@fortawesome/free-regular-svg-icons";
import {
    faDownload,
    faEdit,
    faHistory,
    faMagic,
    faPencilAlt,
    faPlay,
    faPlus,
    faRecycle,
    faSave,
    faSignOutAlt,
    faSitemap,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { watchImmediate } from "@vueuse/core";
import { faDiagramNext } from "font-awesome-6";
import { computed, type Ref } from "vue";

import { useActivityStore } from "@/stores/activityStore";
import type { Activity } from "@/stores/activityStoreTypes";

export const workflowEditorActivities = [
    {
        title: "Attributes",
        id: "workflow-editor-attributes",
        tooltip: "Edit workflow attributes",
        description: "View and edit the attributes of this workflow.",
        panel: true,
        icon: faPencilAlt,
        visible: true,
    },
    {
        title: "Inputs",
        id: "workflow-editor-inputs",
        tooltip: "Add input steps to your workflow",
        description: "Add input steps to your workflow.",
        icon: faDiagramNext,
        panel: true,
        visible: true,
    },
    {
        title: "Tools",
        id: "workflow-editor-tools",
        description: "Displays the tool panel to search and place all available tools.",
        icon: faWrench,
        panel: true,
        tooltip: "Search tools to use in your workflow",
        visible: true,
    },
    {
        title: "Workflows",
        id: "workflow-editor-workflows",
        description: "Browse other workflows and add them as sub-workflows.",
        tooltip: "Search workflows to use in your workflow",
        icon: faSitemap,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "Report",
        id: "workflow-editor-report",
        description: "Edit the report for this workflow.",
        tooltip: "Edit workflow report",
        icon: faEdit,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "Best Practices",
        id: "workflow-best-practices",
        description: "Show and test for the best practices in this workflow.",
        tooltip: "Test workflow for best practices",
        icon: faMagic,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "Changes",
        id: "workflow-undo-redo",
        description: "View, undo, and redo your latest changes.",
        tooltip: "Show and manage latest changes",
        icon: faHistory,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "Run",
        id: "workflow-run",
        description: "Run this workflow with specific parameters.",
        tooltip: "Run workflow",
        icon: faPlay,
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "Save this workflow.",
        icon: faSave,
        id: "save-workflow",
        title: "Save",
        tooltip: "Save current changes",
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "Save this workflow with a different name and annotation.",
        icon: farSave,
        id: "save-workflow-as",
        title: "Save as",
        tooltip: "Save a copy of this workflow",
        visible: true,
        click: true,
        optional: true,
    },
    {
        title: "Upgrade",
        id: "workflow-upgrade",
        description: "Update all tools used in this workflow.",
        tooltip: "Update all tools",
        icon: faRecycle,
        visible: true,
        click: true,
        optional: true,
    },
    {
        title: "Download",
        id: "workflow-download",
        description: "Download this workflow in '.ga' format.",
        tooltip: "Download workflow",
        icon: faDownload,
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "Save this workflow and create a new workflow.",
        icon: faPlus,
        title: "Create new",
        id: "workflow-create",
        tooltip: "Save this workflow and create a new one",
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "Exit the workflow editor and return to the start screen.",
        icon: faSignOutAlt,
        id: "exit",
        title: "Exit",
        tooltip: "Exit workflow editor",
        visible: false,
        click: true,
        optional: true,
    },
] as const satisfies Readonly<Activity[]>;

interface ActivityLogicOptions {
    activityBarId: string;
    isNewTempWorkflow: boolean;
}

export function useActivityLogic(options: Ref<ActivityLogicOptions>) {
    const store = useActivityStore(options.value.activityBarId);

    watchImmediate(
        () => options.value.isNewTempWorkflow,
        (value) => {
            store.setMeta("workflow-run", "disabled", value);
        }
    );
}

interface SpecialActivityOptions {
    hasInvalidConnections: boolean;
}

export function useSpecialWorkflowActivities(options: Ref<SpecialActivityOptions>) {
    const saveHover = computed(() => {
        if (options.value.hasInvalidConnections) {
            return "Workflow has invalid connections, review and remove invalid connections";
        } else {
            return "Save this workflow, then exit the workflow editor";
        }
    });

    const specialWorkflowActivities = computed<Activity[]>(() => [
        {
            description: "",
            icon: faSave,
            id: "save-and-exit",
            title: "Save + Exit",
            tooltip: saveHover.value,
            visible: false,
            click: true,
            mutable: false,
        },
    ]);

    return {
        specialWorkflowActivities,
    };
}
