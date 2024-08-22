import { faMagic, faSave, faWrench } from "@fortawesome/free-solid-svg-icons";

import type { Activity } from "@/stores/activityStore";

export const workflowEditorActivities = [
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
        title: "Best Practices",
        id: "workflow-best-practices",
        description: "Show and test for the best practices in this workflow.",
        tooltip: "Test workflow for best practices",
        icon: faMagic,
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
