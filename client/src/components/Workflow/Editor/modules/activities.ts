import {
    faEdit,
    faHistory,
    faMagic,
    faPencilAlt,
    faSave,
    faSitemap,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";

import type { Activity } from "@/stores/activityStore";

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
] as const satisfies Readonly<Activity[]>;

export const specialWorkflowActivities = [
    {
        description: "Save this workflow, then exit the workflow editor.",
        icon: faSave,
        id: "save-and-exit",
        title: "Save + Exit",
        to: null,
        tooltip: "Save and Exit",
        mutable: false,
        optional: false,
        panel: false,
        visible: true,
        click: true,
    },
] as const satisfies Readonly<Activity[]>;
