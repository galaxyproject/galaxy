import { faSave, faWrench } from "@fortawesome/free-solid-svg-icons";

import type { Activity } from "@/stores/activityStore";

export const workflowEditorActivities = [
    {
        anonymous: true,
        description: "Displays the tool panel to search and place all available tools.",
        icon: faWrench,
        id: "workflow-editor-tools",
        panel: true,
        title: "Tools",
        to: null,
        tooltip: "Search tools to use in your workflow",
        visible: true,
    },
] as const satisfies Readonly<Activity[]>;

export const specialWorkflowActivities = [
    {
        anonymous: true,
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
