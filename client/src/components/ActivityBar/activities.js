/**
 * List of built-in activities
 */

export const Activities = [
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
        description: "Displays a panel to search and access available workflows.",
        icon: "sitemap",
        id: "workflows",
        mutable: false,
        optional: true,
        title: "Workflow",
        to: null,
        tooltip: "Display an advanced search field for workflows.",
        visible: true,
    },
    {
        description: "Displays a panel to search and access available workflows.",
        icon: "sitemap",
        id: "workflow",
        mutable: false,
        optional: true,
        title: "Workflows",
        to: "/workflows/list/",
        tooltip: "Display an advanced search field for workflows.",
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
    {
        description: "Displays all workflow invocations.",
        icon: "fa-list",
        id: "invocation",
        mutable: false,
        optional: true,
        title: "Invocations",
        tooltip: "Show all invocations",
        to: "/workflows/invocations",
        visible: false,
    },
];

export function convertDropData(data) {
    if (data.history_content_type === "dataset") {
        return {
            description: data.name,
            icon: "fa-folder",
            id: `dataset-${data.id}`,
            mutable: true,
            optional: true,
            title: data.name,
            tooltip: "A dataset from your history",
            to: "/datasets/list",
            visible: true,
        };
    }
    if (data.history_content_type === "dataset_collection") {
        return {
            description: data.name,
            icon: "fa-folder",
            id: `collection-${data.id}`,
            mutable: true,
            optional: true,
            title: data.name,
            tooltip: "A collection from your history",
            to: "/datasets/list",
            visible: true,
        };
    }
    if (data.model_class === "StoredWorkflow") {
        return {
            description: data.description,
            icon: "fa-play",
            id: `workflow-${data.id}`,
            mutable: true,
            optional: true,
            title: data.name,
            tooltip: data.name,
            to: `/workflows/run?id=${data.id}`,
            visible: true,
        };
    }
}

export default Activities;
