import type { Activity } from "@/stores/activityStore";

export const workflowEditorActivities = [
    {
        anonymous: true,
        description: "Displays the tool panel to search and access all available tools.",
        icon: "wrench",
        id: "workflow-editor-tools",
        mutable: false,
        optional: false,
        panel: true,
        title: "Tools",
        to: null,
        tooltip: "Search and run tools",
        visible: true,
    },
] as const satisfies Readonly<Activity[]>;

export const specialWorkflowActivities = [
    {
        anonymous: true,
        description: "Displays the tool panel to search and access all available tools.",
        icon: "wrench",
        id: "tools",
        mutable: false,
        optional: false,
        panel: true,
        title: "Tools",
        to: null,
        tooltip: "Search and run tools",
        visible: true,
    },
] as const satisfies Readonly<Activity[]>;
