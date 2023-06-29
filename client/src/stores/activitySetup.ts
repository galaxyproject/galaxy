/**
 * List of built-in activities
 */
import { type Activity } from "@/stores/activityStore";
import { type EventData } from "@/stores/eventStore";

export const Activities = [
    {
        description: "Displays currently active interactive tools (ITs), if these are enabled by the administrator.",
        icon: "fa-laptop",
        id: "interactivetools",
        mutable: false,
        optional: true,
        title: "Interactive Tools",
        tooltip: "Show active interactive tools",
        to: "/interactivetool_entry_points/list",
        visible: true,
    },
    {
        description: "Opens a data dialog, allowing uploads from URL, pasted content or disk.",
        icon: "upload",
        id: "upload",
        mutable: false,
        optional: false,
        title: "Upload",
        to: null,
        tooltip: "Download from URL or upload files from disk",
        visible: true,
    },
    {
        description: "Displays the tool panel to search and access all available tools.",
        icon: "wrench",
        id: "tools",
        mutable: false,
        optional: false,
        title: "Tools",
        to: null,
        tooltip: "Search and run tools",
        visible: true,
    },
    {
        description: "Displays a panel to search and access workflows.",
        icon: "sitemap",
        id: "workflows",
        mutable: false,
        optional: true,
        title: "Workflows",
        to: "/workflows/list",
        tooltip: "Search and run workflows",
        visible: true,
    },
    {
        description: "Displays all workflow runs.",
        icon: "fa-list",
        id: "invocation",
        mutable: false,
        optional: true,
        title: "Workflow Invocations",
        tooltip: "Show all workflow runs",
        to: "/workflows/invocations",
        visible: true,
    },
    {
        description: "Displays the list of available visualizations.",
        icon: "chart-bar",
        id: "visualizations",
        mutable: false,
        optional: true,
        title: "Visualize",
        to: "/visualizations",
        tooltip: "Visualize datasets",
        visible: true,
    },
    {
        description: "Displays the list of all histories.",
        icon: "fa-hdd",
        id: "histories",
        mutable: false,
        optional: true,
        title: "Histories",
        tooltip: "Show all histories",
        to: "/histories/list",
        visible: true,
    },
    {
        description: "Displays all of your datasets across all histories.",
        icon: "fa-folder",
        id: "datasets",
        mutable: false,
        optional: true,
        title: "Datasets",
        tooltip: "Show all datasets",
        to: "/datasets/list",
        visible: false,
    },
];

export function convertDropData(data: EventData): Activity | null {
    if (data.history_content_type === "dataset") {
        return {
            description: "Displays this dataset.",
            icon: "fa-file",
            id: `dataset-${data.id}`,
            mutable: true,
            optional: true,
            title: data.name as string,
            tooltip: "View your dataset",
            to: `/datasets/${data.id}/preview`,
            visible: true,
        };
    }
    if (data.model_class === "StoredWorkflow") {
        return {
            description: data.description as string,
            icon: "fa-play",
            id: `workflow-${data.id}`,
            mutable: true,
            optional: true,
            title: data.name as string,
            tooltip: data.name as string,
            to: `/workflows/run?id=${data.id}`,
            visible: true,
        };
    }
    return null;
}
